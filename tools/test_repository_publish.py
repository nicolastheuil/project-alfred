"""Publication boundary checks; run on Linux without GitHub or credentials."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

source = Path(__file__).resolve().parents[1] / 'deploy/runtime/repository-publish.py'
spec = importlib.util.spec_from_file_location('publisher', source)
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)

class PublicationBoundaries(unittest.TestCase):
    def test_personal_memory_never_enters_public_scope(self):
        with self.assertRaises(ValueError):
            publisher.validate_relative('platform', 'profiles/alfred/USER.md')
        with self.assertRaises(ValueError):
            publisher.validate_relative('platform', 'profiles/alfred/PROFESSIONAL.md')
        self.assertEqual(str(publisher.validate_relative('instance', 'profiles/alfred/USER.md')), 'profiles/alfred/USER.md')

    def test_escape_and_operational_data_are_rejected(self):
        for name in ['../README.md', '/etc/shadow', 'docs/.env', 'profiles/alfred/sessions/history.md', 'docs/data.db']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                publisher.validate_relative('instance', name)

    def test_symlink_file_cannot_read_outside_workspace(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            workspace = root / 'workspace'
            workspace.mkdir()
            (root / 'private').write_text('never-copy')
            (workspace / 'README.md').symlink_to(root / 'private')
            with self.assertRaises(OSError):
                publisher.source_bytes(workspace, Path('README.md'))

    def test_symlink_parent_cannot_read_outside_workspace(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            workspace = root / 'workspace'
            workspace.mkdir()
            private = root / 'private'
            private.mkdir()
            (private / 'file.md').write_text('never-copy')
            (workspace / 'docs').symlink_to(private, target_is_directory=True)
            with self.assertRaises(OSError):
                publisher.source_bytes(workspace, Path('docs/file.md'))

    def test_source_size_is_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'file.md').write_bytes(b'x' * 1_000_001)
            with self.assertRaises(ValueError):
                publisher.source_bytes(root, Path('file.md'))

if __name__ == '__main__':
    unittest.main()
