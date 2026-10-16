import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from runtime_layout import migrate,rewrite


class RuntimeLayoutTests(unittest.TestCase):
    def test_menus_share_no_legacy_container_and_files_remain_intact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            files={'runtime/official/server.json':'{}','runtime/official/policies/a/weights.bin':'unchanged',
                'runtime/operations/paper-account.json':'{"cash":123}',
                'runtime/operations/library-job.json':'{}','runtime/operations/policies.json':'{}',
                'runtime/experts/status.json':'{}','runtime/experts/engines/llama.cpp/program.bin':'engine',
                'runtime/rea/inputs/input.txt':'source','backend/rea/project_explorer/saved_projects/a/project.json':json.dumps({'folder':str(root/'backend/rea/project_explorer/saved_projects/a')})}
            for name,value in files.items():
                file=root/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(value,encoding='utf8')
            migrate(root)
            self.assertEqual((root/'runtime/finance/policy_learning/policies/a/weights.bin').read_text(),'unchanged')
            self.assertEqual(json.loads((root/'runtime/finance/virtual_account_orders/paper-account.json').read_text())['cash'],123)
            self.assertTrue((root/'runtime/finance/moe/library-job.json').is_file())
            self.assertTrue((root/'runtime/finance/moe/status.json').is_file())
            self.assertTrue((root/'runtime/shared/engines/llama.cpp/program.bin').is_file())
            self.assertTrue((root/'runtime/platform/server.json').is_file())
            self.assertTrue((root/'runtime/rea/program_analysis/inputs/input.txt').is_file())
            record=json.loads((root/'runtime/rea/project_explorer/projects/a/project.json').read_text())
            self.assertEqual(Path(record['folder']),root/'runtime/rea/project_explorer/projects/a')
            self.assertFalse((root/'runtime/official').exists())
            self.assertEqual(migrate(root)['moved'],0)

    def test_collision_is_rejected_before_moving_any_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for name in ('runtime/official/server.json','runtime/platform/server.json'):
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}')
            with self.assertRaisesRegex(ValueError,'collision'):migrate(root)
            self.assertTrue((root/'runtime/official/server.json').exists())

    def test_rewrite_only_path_values_not_arbitrary_text(self):
        root=Path.cwd()
        self.assertEqual(rewrite({'checkpoint':'runtime/official/policies/a.zip','text':'look at runtime/official'},root),
            {'checkpoint':'runtime/finance/policy_learning/policies/a.zip','text':'look at runtime/official'})


if __name__=='__main__':unittest.main()
