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
            self.assertTrue(store.get_price_data(['000660.KS'],'2020','2030').empty)
            self.assertEqual(json.loads(sdk.call_args.kwargs['input'])['operation'],'daily_history')

    def test_unknown_symbol_rejected_before_sdk_call(self):
        with patch('stockrl.management.connection_settings.provider_credentials.read_settings',return_value={'provider':'kiwoom'}), \
                patch('subprocess.run') as sdk:
            with self.assertRaises(ValueError):operations.collect_kiwoom_prices(['UNKNOWN.KS'])
        sdk.assert_not_called()
