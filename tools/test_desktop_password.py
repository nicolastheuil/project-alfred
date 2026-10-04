"""Verify recovery failures preserve a usable password and restore vault consistency."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

source = Path(__file__).resolve().parents[1] / 'deploy/runtime/desktop-password.py'
spec = importlib.util.spec_from_file_location('desktop_password', source)
password = importlib.util.module_from_spec(spec)
spec.loader.exec_module(password)


class RecoveryChecks(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name)
        self.login, self.env = root / 'login.json', root / 'auth.env'
        self.old_login = json.dumps({'username': 'operator', 'password': 'original-example', 'signing_secret': 'original-signature'})
        self.old_env = 'HERMES_DASHBOARD_BASIC_AUTH_USERNAME=operator\nHERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH=old\nHERMES_DASHBOARD_BASIC_AUTH_SECRET=old\nHERMES_DASHBOARD_PUBLIC_URL=https://example.org:28443\n'
        for p, value in [(self.login, self.old_login), (self.env, self.old_env)]:
            p.write_text(value); p.chmod(0o600)
        self.patches = [patch.object(password, 'LOGIN', self.login), patch.object(password, 'ENV', self.env)]
        for p in self.patches:
            p.start(); self.addCleanup(p.stop)

    def test_vault_failure_does_not_change_the_working_account(self):
        item = {'fields': [{'id': 'username', 'value': 'operator'}, {'id': 'password', 'value': 'original-example'}]}
        with patch.object(password, 'vault_get', return_value=(item, {}, {})), \
             patch.object(password, 'vault_put', side_effect=RuntimeError('vault unavailable')), \
             patch.object(password, 'restart') as restart:
            with self.assertRaises(RuntimeError): password.rotate()
            restart.assert_not_called()
        self.assertEqual(self.login.read_text(), self.old_login)
        self.assertEqual(self.env.read_text(), self.old_env)

    def test_restart_failure_restores_vm_and_vault(self):
        item = {'fields': [{'id': 'username', 'value': 'operator'}, {'id': 'password', 'value': 'original-example'}]}
        with patch.object(password, 'vault_get', return_value=(item, {}, {})), \
             patch.object(password, 'vault_put') as write, \
             patch.object(password, 'restart', side_effect=[RuntimeError('restart failed'), None]):
            with self.assertRaises(RuntimeError): password.rotate()
            self.assertEqual(write.call_count, 2)
            self.assertEqual(write.call_args.args[0], item)
        self.assertEqual(self.login.read_text(), self.old_login)
        self.assertEqual(self.env.read_text(), self.old_env)

    def test_local_rotation_changes_password_and_signing_key(self):
        with patch.object(password, 'restart'):
            result = password.rotate(local_only=True)
        self.assertNotEqual(json.loads(self.login.read_text())['password'], 'original-example')
        self.assertNotEqual(json.loads(self.login.read_text())['signing_secret'], 'original-signature')
        self.assertIn('HERMES_DASHBOARD_PUBLIC_URL=https://example.org:28443', self.env.read_text())
        self.assertTrue(result['sessions_invalidated'])


if __name__ == '__main__': unittest.main()
