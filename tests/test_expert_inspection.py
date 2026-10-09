import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from stockrl.platform.expert_inspection import inspect_all
from stockrl.platform.expert_discovery import discover_repositories,FINANCE_QUERIES
from stockrl.platform.expert_search_metadata import annotate


class InspectionTests(unittest.TestCase):
    def test_batch_continues_on_failures_preserves_selection_and_checks_quality(self):
        def expert(key,source=None):
            return dict(id=key,name=key,role='market',input={'supported':True},feature_size=4,
                package={'sha256':key},conversion={'source_id':source,'validation':{'max_relative_rmse':.01}} if source else None)
        items={key:expert(key,source) for key,source in [('a',None),('broken',None),('a_int4','a'),('last',None)]}
        catalog={'experts':items,'active':['a']}
        measured=[]
        def measure(*args):
            key=args[4];measured.append(key)
            if key=='broken':raise ValueError('missing input')
            return dict(id=key,warm_median_seconds=.1,metrics={},packet={'native_output':[1]})
        with tempfile.TemporaryDirectory() as directory:
            with (patch('stockrl.platform.expert_inspection.capture_input',return_value={'input':{},'snapshot':{'as_of':'now'}}),
                  patch('stockrl.platform.expert_inspection.measure',side_effect=measure),
                  patch('stockrl.platform.expert_inspection.comparison_result',return_value={'relative_rmse':.2,'action_agreement':None,'input_sha256':'same'})):
                report=inspect_all(SimpleNamespace(state_dir=Path(directory)),'config',catalog,{},lambda **kw:None)
        self.assertEqual(set(measured),set(items));self.assertEqual(catalog['active'],['a'])
        self.assertEqual((report['passed'],report['failed'],report['quality_warning']),(2,1,1))
        self.assertEqual(items['a_int4']['check']['status'],'quality_warning')
        self.assertFalse(items['a_int4']['conversion']['validation']['passed'])

    def test_finance_preset_deduplicates_and_fetches_popular_and_recent(self):
        class API:
            def __init__(self):self.calls=[]
            def list_models(self,**kw):
                self.calls.append(kw);return [SimpleNamespace(id='same/model')]
        api=API();title,keywords,repos,errors=discover_repositories(api,{},lambda **kw:None)
        self.assertEqual(keywords,list(FINANCE_QUERIES));self.assertEqual(len(repos),1);self.assertFalse(errors)
        self.assertEqual({kw['sort'] for kw in api.calls},{'downloads','lastModified'})
        self.assertIn('금융',title)

    def test_creation_is_never_fabricated_release_and_requirements_remain_unknown(self):
        info=SimpleNamespace(card_data={},created_at='2024-01-01',last_modified='2026-10-09',pipeline_tag='text-generation')
        row=dict(repository='finance/test',url='https://huggingface.co/finance/test',revision='abc',bytes=10)
        with patch('stockrl.platform.expert_search_metadata.requests.get',side_effect=__import__('requests').RequestException('offline')):
            result=annotate(row,info,{}, {'finance/test':[{'id':'local'}]},100)
        self.assertIsNone(result['release_date']);self.assertEqual(result['created'],'2024-01-01')
        self.assertFalse(result['requirements_verified']);self.assertTrue(result['installed_versions'])
        self.assertIn('미확인',result['api_requirement'])


if __name__=='__main__':unittest.main()
