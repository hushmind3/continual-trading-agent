"""The deployed FastAPI serves only the current frontend build, without caching."""
from types import SimpleNamespace
import unittest
from fastapi.testclient import TestClient
from stockrl.platform.api import make_app
from stockrl.paths import PROJECT_ROOT


class ReactAssetChecks(unittest.TestCase):
    def test_built_entrypoint_and_asset_delivery(self):
        with TestClient(make_app(SimpleNamespace())) as client:
            response=client.get('/')
            self.assertEqual(response.status_code,200)
            self.assertIn('id="root"',response.text)
            self.assertEqual(response.headers['cache-control'],'no-store')
            import re
            names=re.findall(r'/assets/([^"\s]+)',response.text)
            self.assertTrue(names)
            for name in names:
                asset=client.get('/assets/'+name)
                self.assertEqual(asset.status_code,200)
                self.assertTrue(asset.content)
                self.assertEqual(asset.headers['cache-control'],'no-store')

    def test_traversal_and_project_identity(self):
        with TestClient(make_app(SimpleNamespace())) as client:
            for path in ['missing.js','%2e%2e/config.py','C:/Windows/win.ini']:
                self.assertEqual(client.get('/assets/'+path).status_code,404)
            health=client.get('/api/health').json()
            self.assertEqual(health['architecture'],'finrlx-moe-ppo-v1')
            self.assertEqual(health['project'],str(PROJECT_ROOT))
