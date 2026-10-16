from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from ai_agent.Hermes.artifacts.handlers import preview,LIMIT


class ArtifactTests(unittest.TestCase):
    def test_markdown_is_returned_as_text_and_large_files_are_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);file=root/'report.md'
            file.write_text('# 오류 보고서\n<script>unsafe()</script>',encoding='utf8')
            result=preview('report.md',root)
            self.assertIn('오류 보고서',result['content']);self.assertEqual(result['format'],'.md')
            self.assertFalse(result['truncated'])
            file.write_bytes(b'a'*(LIMIT+20));result=preview('report.md',root)
            self.assertTrue(result['truncated']);self.assertEqual(len(result['content']),LIMIT)

    def test_sibling_paths_installation_credentials_and_binaries_are_denied(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'workspace';root.mkdir()
            for name in ('../secret.md','configs/local/secret.json','platform-settings.json','.venv/report.md','program.exe'):
                with self.subTest(path=name),self.assertRaises(ValueError):preview(name,root)

    def test_missing_documents_are_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(FileNotFoundError):preview('missing.md',temporary)


if __name__=='__main__':unittest.main()
