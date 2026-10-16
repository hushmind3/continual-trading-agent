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

    def test_git_status_and_line_references_resolve_actual_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'AGENTS.md').write_text('actual project instructions', encoding='utf8')
            for reference in ('M AGENTS.md', '?? AGENTS.md', 'AGENTS.md:4:2', 'AGENTS.md#L4-L7'):
                self.assertEqual(preview(reference, root)['name'], 'AGENTS.md')
            (root/'M AGENTS.md').write_text('literal filename', encoding='utf8')
            self.assertEqual(preview('M AGENTS.md', root)['content'], 'literal filename')

    def test_missing_documents_are_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(FileNotFoundError):preview('missing.md',temporary)


class UploadTests(unittest.TestCase):
    def test_upload_preserves_bytes_and_cannot_escape_owned_folder(self):
        import base64
        from unittest.mock import patch
        from ai_agent.Hermes.artifacts import handlers
        with tempfile.TemporaryDirectory() as temporary,patch.object(handlers,'UPLOADS',Path(temporary)/'uploads'):
            result=handlers.upload({'name':'../../보고서.md','content':base64.b64encode('내용'.encode()).decode()})
            self.assertEqual(Path(result['path']).read_text(encoding='utf8'),'내용')
            self.assertEqual(handlers.uploaded_paths([result['path']]),[result['path']])
            self.assertTrue(Path(result['path']).is_relative_to(Path(temporary)/'uploads'))
            with self.assertRaises(ValueError):handlers.uploaded_paths([str(Path(temporary)/'secret.md')])
    def test_invalid_and_oversized_uploads_fail(self):
        from fastapi import HTTPException
        from ai_agent.Hermes.artifacts.handlers import upload,UPLOAD_LIMIT
        for value in ({'name':'test.txt','content':'%%%bad'},{'name':'a:b.txt','content':''},{'name':'large.txt','content':'A'*((UPLOAD_LIMIT+2)//3*4+4)}):
            with self.subTest(name=value['name']),self.assertRaises(HTTPException):upload(value)

if __name__=='__main__':unittest.main()
