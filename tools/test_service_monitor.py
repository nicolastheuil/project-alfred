"""Failure-path checks; run on Linux, no service changes or model calls."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

source = Path(__file__).resolve().parents[1] / 'deploy/runtime/service-monitor.py'
spec = importlib.util.spec_from_file_location('service_monitor', source)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class RecoveryChecks(unittest.TestCase):
    def test_monitor_report_timestamp_field_and_stale_detection(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'health.json'
            path.write_text('{"at":"1970-01-01T00:16:40+00:00"}')
            probe = {'kind': 'heartbeat', 'path': str(path), 'timestamp_field': 'at', 'max_age': 180}
            with patch.object(monitor.time, 'time', return_value=1100):
                monitor.probe(probe)
            with patch.object(monitor.time, 'time', return_value=1200):
                with self.assertRaises(ValueError):
                    monitor.probe(probe)

    def test_delivery_failure_preserves_one_episode_across_ticks(self):
        config = {'services': [{'unit': 'fake.service', 'auto_restart': False}],
                  'failure_threshold': 3, 'restart_limit_per_hour': 2}
        state = {'fake.service': {'strikes': 2, 'restarts': []}}
        with patch.object(monitor, 'health', return_value=(False, 'service_inactive', {})), \
             patch.object(monitor, 'write_json'), \
             patch.object(monitor, 'run', side_effect=OSError('not stored')):
            monitor.tick(config, state)
            first = state['fake.service']['episode']
            monitor.tick(config, state)
        self.assertEqual(state['fake.service']['episode'], first)
        self.assertEqual(state['fake.service']['queue_error'], 'incident_delivery_failed')

    def test_exhausted_restart_budget_cannot_execute_command(self):
        history = {'restarts': [950, 980]}
        with patch.object(monitor, 'run') as command:
            self.assertFalse(monitor.bounded_restart('fake.service', history, 2, 1000))
            command.assert_not_called()

    def test_old_attempt_expires_and_failed_restart_consumes_budget(self):
        history = {'restarts': [1, 990]}
        with patch.object(monitor, 'run') as command:
            command.return_value.returncode = 1
            self.assertFalse(monitor.bounded_restart('fake.service', history, 2, 4000))
        self.assertEqual(history['restarts'], [990, 4000])

    def test_privileged_write_refuses_symlink_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'actual').mkdir()
            (root / 'redirect').symlink_to(root / 'actual', target_is_directory=True)
            with self.assertRaises(OSError):
                monitor.write_json(root / 'redirect/incident.json', {'test': True})
            self.assertFalse((root / 'actual/incident.json').exists())

    def test_three_strikes_and_exhausted_restarts_open_incident(self):
        config = {'services': [{'unit': 'fake.service'}], 'failure_threshold': 3, 'restart_limit_per_hour': 2}
        state = {'fake.service': {'strikes': 2, 'restarts': [650, 700]}}
        with patch.object(monitor.time, 'time', return_value=1000), \
             patch.object(monitor, 'health', return_value=(False, 'service_inactive', {})), \
             patch.object(monitor, 'write_json'), patch.object(monitor, 'queue_incident') as incident:
            monitor.tick(config, state)
            incident.assert_called_once()

    def test_healthy_tick_uses_no_model_or_restart(self):
        config = {'services': [{'unit': 'fake.service'}], 'failure_threshold': 3, 'restart_limit_per_hour': 2}
        with patch.object(monitor, 'health', return_value=(True, 'healthy', {})), \
             patch.object(monitor, 'write_json'), patch.object(monitor, 'run') as command:
            monitor.tick(config, {})
            command.assert_not_called()


if __name__ == '__main__':
    unittest.main()
