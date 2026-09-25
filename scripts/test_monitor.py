import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime
from zoneinfo import ZoneInfo
import monitor_runtime as rt
import monitor_youtube_live_multi as core


class Tests(unittest.TestCase):
    def test_parser(self):
        for raw, expected in [('978',978), ('1.094',1094), ('1094',1094), ('12.345',12345), ('0',0)]:
            self.assertEqual(core.parse_ptbr_int_from_text(raw+' assistindo agora'), expected)
        for raw in ['1,2 mil assistindo agora', 'Canal 12 - 1.094 assistindo agora', '1.09 assistindo agora', '12 visualizações', '1 2 3 assistindo agora', '1094']:
            self.assertIsNone(core.parse_ptbr_int_from_text(raw))

    def test_schedule_midnight_multiple_and_invalid(self):
        now = datetime(2026,9,26,0,2,tzinfo=ZoneInfo('America/Sao_Paulo'))
        slots = rt.due_slots(now, ['23:59','00:01'], 6)
        self.assertEqual([s.strftime('%d %H:%M') for s in slots], ['25 23:59','26 00:01'])
        self.assertEqual(rt.due_slots(now,['00:03'],6), [])
        for raw in ['25:99','24:00','09:00;bad']:
            with self.assertRaises(ValueError): rt.daily_times({'DAILY_SEND_TIMES':raw})

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.csv = str(Path(self.tmp.name)/'data.csv')
        self.state = patch.object(core,'STATE_FILE',str(Path(self.tmp.name)/'legacy.json'))
        self.state.start()
        core.append_csv(self.csv,['old','url','title',100,'100 assistindo agora'])
        self.env = dict(DAILY_SEND_TIMES='09:00',SMTP_HOST='fake',SMTP_USER='fake',SMTP_PASS='fake',ALERT_TO='fake',CLEAR_CSV_AFTER_DAILY='1')
        self.now = datetime(2026,9,25,9,0,tzinfo=ZoneInfo('America/Sao_Paulo'))

    def tearDown(self):
        self.state.stop(); self.tmp.cleanup()

    def test_snapshot_new_rows_and_duplicate(self):
        def send(env, snapshot):
            self.assertIn('__daily_snapshot_2026-09-25_09-00_',snapshot)
            self.assertIn('old',Path(snapshot).read_text())
            core.append_csv(self.csv,['new','url','title',200,'200 assistindo agora'])
            return True
        with patch.object(core,'send_daily_report',side_effect=send) as smtp:
            rt.reports(self.env,self.csv,self.now)
            rt.reports(self.env,self.csv,self.now)
        self.assertEqual(smtp.call_count,1)
        self.assertNotIn('old',Path(self.csv).read_text())
        self.assertIn('new',Path(self.csv).read_text())

    def test_failure_preserves_data_and_stops_ambiguous_retry(self):
        original = Path(self.csv).read_bytes()
        with patch.object(core,'send_daily_report',return_value=False) as smtp:
            with self.assertRaises(RuntimeError): rt.reports(self.env,self.csv,self.now)
            rt.reports(self.env,self.csv,self.now)
        self.assertEqual(smtp.call_count,1)
        self.assertEqual(Path(self.csv).read_bytes(),original)

    def test_crash_after_accept_recovers_without_resend(self):
        with patch.object(core,'send_daily_report',return_value=True), patch.object(rt,'finish_cleanup',side_effect=OSError('busy')):
            with self.assertRaises(OSError): rt.reports(self.env,self.csv,self.now)
        with patch.object(core,'send_daily_report') as smtp:
            rt.reports(self.env,self.csv,self.now)
            smtp.assert_not_called()
        self.assertNotIn('old',Path(self.csv).read_text())

    def test_legacy_sent_is_respected(self):
        rt.write_json(core.STATE_FILE,{'2026-09-25':{'09:00':True}})
        with patch.object(core,'send_daily_report') as smtp:
            rt.reports(self.env,self.csv,self.now)
            smtp.assert_not_called()

    def test_corrupt_state_stops(self):
        Path(core.STATE_FILE).write_text('{broken')
        with self.assertRaises(ValueError): rt.reports(self.env,self.csv,self.now)

    def test_lock(self):
        path=Path(self.tmp.name)/'lock'
        with rt.lock(path):
            with self.assertRaises(RuntimeError):
                with rt.lock(path,wait=0): pass

    def test_wrong_video_and_not_live_are_rejected(self):
        driver=MagicMock()
        driver.current_url='https://www.youtube.com/watch?v=abc'
        driver.title='test'
        for details in [{'videoDetails':{'videoId':'other','isLive':True}}, {'videoDetails':{'videoId':'abc','isLive':False}}]:
            driver.execute_script.return_value=details
            with patch.object(core,'WebDriverWait'), patch.object(core.time,'sleep'):
                value,_,_=core.extract_viewers_for_url(driver,driver.current_url,1,0)
            self.assertIsNone(value)

    def test_aria_label_precedence(self):
        driver=MagicMock()
        driver.current_url='https://www.youtube.com/watch?v=abc'
        driver.execute_script.return_value={'videoDetails':{'videoId':'abc','isLive':True}}
        elem=MagicMock()
        elem.get_attribute.return_value='1.094 assistindo agora'
        elem.text='67677878 assistindo agora'
        driver.find_elements.return_value=[elem]
        with patch.object(core,'WebDriverWait'):
            value,raw,_=core.extract_viewers_for_url(driver,driver.current_url,1,0)
        self.assertEqual(value,1094)
        self.assertEqual(raw,'1.094 assistindo agora')

    def test_manual_does_not_clear_or_consume_slot(self):
        original=Path(self.csv).read_bytes()
        with patch.object(sys,'argv',['monitor','--test-daily-email','--csv',self.csv]), patch.object(core,'read_env',return_value=self.env), patch.object(core,'send_daily_report',return_value=True):
            self.assertEqual(rt.main(),0)
        self.assertEqual(Path(self.csv).read_bytes(),original)
        self.assertFalse(rt.paths_for(self.csv)[0].exists())

    def test_two_due_slots_have_distinct_snapshots(self):
        env=dict(self.env, DAILY_SEND_TIMES='08:57;09:00')
        with patch.object(core,'send_daily_report',return_value=True) as smtp:
            rt.reports(env,self.csv,self.now)
        self.assertEqual(smtp.call_count,2)
        self.assertNotEqual(smtp.call_args_list[0].args[1],smtp.call_args_list[1].args[1])

    def test_reporting_runs_even_if_collector_fails(self):
        child=MagicMock(); child.poll.return_value=1
        with patch.object(sys,'argv',['monitor','--csv',self.csv,'--url','https://www.youtube.com/watch?v=abc']), patch.object(core,'read_env',return_value=self.env), patch.object(rt,'reports') as reports, patch.object(rt.subprocess,'Popen',return_value=child):
            self.assertEqual(rt.main(),1)
            self.assertGreaterEqual(reports.call_count,2)

    def test_env_quotes_preserve_literal_password_characters(self):
        config=Path(self.tmp.name)/'example.env'
        config.write_text("A=\"quoted\"\nB=endswith'\nC='wrapped'\n",encoding='utf-8')
        self.assertEqual(core.read_env(str(config)),{'A':'quoted','B':"endswith'",'C':'wrapped'})

    def test_missing_snapshot_never_sends(self):
        with patch.object(core,'send_email_smtp') as smtp:
            self.assertFalse(core.send_daily_report(self.env,str(Path(self.tmp.name)/'missing.csv')))
            smtp.assert_not_called()


if __name__=='__main__': unittest.main()

