import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from stockrl.finrl.price_data import operations
from stockrl.finrl.price_data.storage import PriceStore


class KiwoomHistoryTests(unittest.TestCase):
    def test_intraday_timestamps_and_origins_do_not_overwrite_each_other(self):
        import pandas as pd
        import sqlite3
        from contextlib import closing
        with tempfile.TemporaryDirectory() as directory:
            store=PriceStore(directory)
            frame=pd.DataFrame({'ticker':['A','A'],'date':pd.to_datetime(['2026-10-13 09:00:00.000000001+09:00','2026-10-13 09:01:00+09:00'],format='mixed'),
                'open':[100,101],'high':[100,101],'low':[100,101],'close':[100,101],'volume':[1,2]})
            frame.attrs.update(source='kiwoom',timeframe='1m')
            self.assertEqual(store.save_price_data(frame),2)
            original=store.get_price_data(['A'],'2026-10-13','2026-10-13',source='kiwoom',timeframe='1m')
            self.assertEqual(len(original),2)
            self.assertEqual(pd.to_datetime(original.datadate,utc=True,format='mixed').astype('int64').tolist(),[pd.Timestamp(value).value for value in frame.date])
            frame.attrs['timeframe']='5m';store.save_price_data(frame.iloc[:1])
            frame.attrs.update(source='another',timeframe='1m');store.save_price_data(frame.iloc[:1])
            self.assertEqual(len(store.get_price_data(['A'],'2026-10-13','2026-10-13')),4)
            with closing(sqlite3.connect(store.db_path)) as db:
                identity=db.execute("SELECT id,created_at FROM price_data WHERE source='kiwoom' AND timeframe='1m' ORDER BY date").fetchall()
            frame.attrs.update(source='kiwoom',timeframe='1m');frame.loc[0,'close']=99;store.save_price_data(frame.iloc[:1])
            self.assertEqual(len(store.get_price_data(['A'],'2026-10-13','2026-10-13')),4)
            self.assertEqual(store.get_price_data(['A'],'2026-10-13','2026-10-13',source='kiwoom',timeframe='1m').prccd.tolist(),[99,101])
            with closing(sqlite3.connect(store.db_path)) as db:
                self.assertEqual(db.execute("SELECT id,created_at FROM price_data WHERE source='kiwoom' AND timeframe='1m' ORDER BY date").fetchall(),identity)

    def test_legacy_schema_migration_preserves_rows_and_custom_index(self):
        import sqlite3
        from contextlib import closing
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'market_prices.sqlite3'
            with closing(sqlite3.connect(path)) as db,db:
                db.execute('''CREATE TABLE price_data (id INTEGER PRIMARY KEY AUTOINCREMENT,ticker TEXT NOT NULL,date TEXT NOT NULL,
                    open REAL,high REAL,low REAL,close REAL,adj_close REAL,volume REAL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,UNIQUE(ticker,date))''')
                db.execute("INSERT INTO price_data(ticker,date,close) VALUES('A','2026-10-13',100)")
                db.execute('CREATE INDEX prices_by_close ON price_data(close)')
                db.execute("UPDATE sqlite_sequence SET seq=42 WHERE name='price_data'")
                before=db.execute('SELECT id,ticker,date,close,created_at FROM price_data').fetchall()
            store=PriceStore(directory)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute('SELECT id,ticker,date,close,created_at FROM price_data').fetchall(),before)
                self.assertEqual(db.execute('SELECT source,timeframe FROM price_data').fetchone(),('unknown','unknown'))
                self.assertIn('prices_by_close',[index[1] for index in db.execute('PRAGMA index_list(price_data)')])
                self.assertEqual(db.execute("SELECT seq FROM sqlite_sequence WHERE name='price_data'").fetchone(),(42,))
            self.assertEqual(len(store.get_price_data(['A'],'2020','2030')),1)
            PriceStore(directory)

    def test_unsupported_legacy_columns_roll_back_migration(self):
        import sqlite3
        from contextlib import closing
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'market_prices.sqlite3'
            with closing(sqlite3.connect(path)) as db,db:
                db.execute('''CREATE TABLE price_data (id INTEGER PRIMARY KEY AUTOINCREMENT,ticker TEXT NOT NULL,date TEXT NOT NULL,
                    open REAL,high REAL,low REAL,close REAL,adj_close REAL,volume REAL,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_note TEXT,UNIQUE(ticker,date))''')
                db.execute("INSERT INTO price_data(ticker,date,user_note) VALUES('A','2026-10-13','keep')")
                before=db.execute('SELECT * FROM price_data').fetchall()
                columns=[row[1] for row in db.execute('PRAGMA table_info(price_data)')]
            with self.assertRaisesRegex(RuntimeError,'알 수 없는 열'):PriceStore(directory)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute('SELECT * FROM price_data').fetchall(),before)
                self.assertEqual([row[1] for row in db.execute('PRAGMA table_info(price_data)')],columns)

    def test_throttling_is_retried_but_other_api_errors_are_not(self):
        from stockrl.platform import kiwoom_data
        from unittest.mock import Mock
        class APIError(Exception):
            def __init__(self,status):self.status_code=status
        client=Mock();client.request.side_effect=[APIError(429),SimpleNamespace(body={'return_code':0})]
        with patch.object(kiwoom_data.time,'sleep') as sleep:
            self.assertEqual(kiwoom_data.request_daily_history(client,'005930.KS','20261013'),{'return_code':0})
        self.assertEqual(client.request.call_count,2);sleep.assert_called_once_with(1)
        client=Mock();client.request.side_effect=APIError(400)
        with patch.object(kiwoom_data.time,'sleep') as sleep:
            with self.assertRaises(APIError):kiwoom_data.request_daily_history(client,'005930.KS','20261013')
        self.assertEqual(client.request.call_count,1);sleep.assert_not_called()

    def result(self):
        return {'symbol':'005930.KS','base_date':'20261013','response':{
            'return_code':0,'stk_dt_pole_chart_qry':[
                {'dt':'20261013','open_pric':'-100','high_pric':'+110','low_pric':'90','cur_prc':'+105','trde_qty':'1,234'},
                {'dt':'20261012','open_pric':'90','high_pric':'100','low_pric':'85','cur_prc':'95','trde_qty':'900'}]}}

    def test_signed_prices_are_positive_and_dates_sorted(self):
        frame=operations.normalize_kiwoom_daily(self.result())
        self.assertEqual(frame.date.tolist(),['2026-10-12','2026-10-13'])
        self.assertEqual(frame.close.tolist(),[95,105])
        self.assertEqual(frame.volume.tolist(),[900,1234])
        self.assertEqual(frame.adj_close.tolist(),frame.close.tolist())

    def test_invalid_bar_or_future_session_rejects_entire_symbol(self):
        for field,value in [('dt','20261014'),('dt','invalid'),('cur_prc','nan'),('cur_prc','inf'),('low_pric','109'),('open_pric','0'),('trde_qty','-1')]:
            with self.subTest(field=field,value=value):
                result=self.result();result['response']['stk_dt_pole_chart_qry'][0][field]=value
                with self.assertRaises(ValueError):operations.normalize_kiwoom_daily(result)

    def test_response_for_other_symbol_or_missing_result_code_is_rejected(self):
        result=self.result();result['response']['stk_cd']='000660'
        with self.assertRaisesRegex(ValueError,'종목'):operations.normalize_kiwoom_daily(result)
        result=self.result();del result['response']['return_code']
        with self.assertRaises(ValueError):operations.normalize_kiwoom_daily(result)

    def test_conflicting_duplicate_dates_are_not_silently_overwritten(self):
        result=self.result();row=copy.deepcopy(result['response']['stk_dt_pole_chart_qry'][0]);row['cur_prc']='104';result['response']['stk_dt_pole_chart_qry'].append(row)
        with self.assertRaisesRegex(ValueError,'상충'):operations.normalize_kiwoom_daily(result)

    def test_partial_collection_saves_only_valid_registered_symbols(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'configs').mkdir();(root/'.venv/kiwoom/Scripts').mkdir(parents=True);(root/'.venv/kiwoom/Scripts/python.exe').touch()
            (root/'configs/instruments.json').write_text(json.dumps({'instruments':[
                {'symbol':'005930.KS','market':'KRX','asset_class':'equity'},
                {'symbol':'000660.KS','market':'KRX','asset_class':'equity'}]}))
            bad=self.result();bad['symbol']='000660.KS';bad['response']['return_code']=1;bad['response']['return_msg']='조회 실패'
            output=json.dumps({'kind':'history','value':[self.result(),bad]})
            store=PriceStore(root/'data')
            with patch.object(operations,'ROOT',root),patch.object(operations,'price_store',return_value=store), \
                    patch('stockrl.management.connection_settings.provider_credentials.read_settings',return_value={'provider':'kiwoom'}), \
                    patch('subprocess.run',return_value=SimpleNamespace(returncode=0,stdout=output)) as sdk:
                summary=operations.collect_kiwoom_prices(['005930.KS','000660.KS'])
            self.assertEqual(summary['rows'],2);self.assertEqual(summary['status'],'partial')
            self.assertEqual(summary['errors'][0]['symbol'],'000660.KS')
            self.assertEqual(len(store.get_price_data(['005930.KS'],'2020','2030')),2)
            self.assertEqual(len(store.get_price_data(['005930.KS'],'2020','2030',source='kiwoom',timeframe='1d')),2)
            self.assertTrue(store.get_price_data(['000660.KS'],'2020','2030').empty)
            self.assertEqual(json.loads(sdk.call_args.kwargs['input'])['operation'],'daily_history')

    def test_unknown_symbol_rejected_before_sdk_call(self):
        with patch('stockrl.management.connection_settings.provider_credentials.read_settings',return_value={'provider':'kiwoom'}), \
                patch('subprocess.run') as sdk:
            with self.assertRaises(ValueError):operations.collect_kiwoom_prices(['UNKNOWN.KS'])
        sdk.assert_not_called()
