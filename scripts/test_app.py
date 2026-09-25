import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from app_service import AppService

class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name);self.s=AppService(self.home,self.home/'logs')
    def test_first_install_empty_schedule_and_folders(self):
        self.assertTrue((self.home/'logs').exists())
        self.assertEqual(self.s.agenda.snapshot()['config']['mode'],'dates')
        self.assertFalse(self.s.status()['running'])
    def test_secret_not_returned_and_blank_preserves(self):
        cfg=self.s.settings();cfg['SMTP_PASS']='example-secret';cfg['urls']=['https://youtu.be/abc']
        self.s.save(cfg);result=self.s.settings()
        self.assertNotIn('SMTP_PASS',result);self.assertTrue(result['password_saved'])
        result['SMTP_PASS']='';self.s.save(result)
        self.assertIn('SMTP_PASS="example-secret"',(self.home/'.env').read_text())
    def test_reject_newlines_and_invalid_links(self):
        cfg=self.s.settings();cfg['SMTP_HOST']='host\nSMTP_PASS=bad'
        with self.assertRaises(ValueError):self.s.save(cfg)
        cfg=self.s.settings();cfg['urls']=['https://example.com']
        with self.assertRaises(ValueError):self.s.save(cfg)
    def test_control_owned_process_and_settings_guard(self):
        cfg=self.s.settings();cfg['urls']=['https://youtu.be/abc'];self.s.save(cfg)
        child=MagicMock();child.poll.return_value=None
        with patch('app_service.subprocess.Popen',return_value=child) as spawn:
            self.assertTrue(self.s.start()['running']);self.s.start();self.assertEqual(spawn.call_count,1)
            with self.assertRaises(ValueError):self.s.save(cfg)
            self.assertTrue(self.s.request_stop()['stopping']);child.terminate.assert_not_called()
            child.poll.return_value=0
            self.assertFalse(self.s.status()['running'])
    def test_start_requires_links(self):
        with self.assertRaises(ValueError):self.s.start()

if __name__=='__main__':unittest.main()
