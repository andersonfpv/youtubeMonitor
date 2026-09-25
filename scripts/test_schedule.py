import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch
import report_schedule as agenda
import monitor_runtime as runtime
import monitor_youtube_live_multi as core
import agenda_relatorios as ui


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'agenda.json'
        self.csv=str(Path(self.temp.name)/'dados.csv')
        self.now=agenda.parse_slot('30/09/2026','10:26')
        self.env=dict(DAILY_SEND_TIMES='10:26',DAILY_SEND_TOLERANCE_MINUTES='6',
                      SMTP_HOST='fake',SMTP_USER='fake',SMTP_PASS='fake',ALERT_TO='fake',CLEAR_CSV_AFTER_DAILY='1')
        self.path_patch=patch.object(agenda,'DEFAULT_PATH',self.path)
        self.state_patch=patch.object(core,'STATE_FILE',str(Path(self.temp.name)/'legacy.json'))
        self.path_patch.start();self.state_patch.start()
        core.append_csv(self.csv,['sample','url','title',100,'100 assistindo agora'])

    def tearDown(self):
        self.path_patch.stop();self.state_patch.stop();self.temp.cleanup()

    def save(self,dates,mode='dates'):
        agenda.save_schedule(dict(version=1,mode=mode,dates=[s.isoformat() for s in dates]),self.path)

    def test_blank_daily_times_disable_legacy_fallback(self):
        self.assertEqual(runtime.daily_times(dict(DAILY_SEND_TIMES='',DAILY_SEND_HOUR='10')),[])
        self.assertEqual(runtime.daily_times({}),[])
        self.assertEqual(runtime.daily_times(dict(DAILY_SEND_HOUR='10',DAILY_SEND_MINUTE='26')),['10:26'])

    def test_specific_date_sends_without_daily_times(self):
        self.env['DAILY_SEND_TIMES']=''
        self.save([self.now])
        with patch.object(core,'send_daily_report',return_value=True) as smtp:
            runtime.reports(self.env,self.csv,self.now)
            runtime.reports(self.env,self.csv,self.now+timedelta(days=1))
            self.assertEqual(smtp.call_count,1)

    def test_daily_mode_blank_has_no_implicit_midnight_send(self):
        self.env['DAILY_SEND_TIMES']=''
        self.save([],mode='daily')
        with patch.object(core,'send_daily_report') as smtp:
            runtime.reports(self.env,self.csv,self.now.replace(hour=0,minute=1))
            smtp.assert_not_called()

    def test_calendar_validation_and_duplicate(self):
        for day,hour in [('31/02/2026','12:00'),('25/09/2026','24:00')]:
            with self.assertRaises(ValueError): agenda.parse_slot(day,hour)
        with self.assertRaises(ValueError): self.save([self.now,self.now])
        self.assertEqual(self.now.utcoffset(),timedelta(hours=-3))

    def test_future_does_not_send_and_date_is_not_daily(self):
        self.save([self.now+timedelta(days=1)])
        with patch.object(core,'send_daily_report') as smtp:
            runtime.reports(self.env,self.csv,self.now)
            smtp.assert_not_called()

    def test_specific_date_sends_once(self):
        self.save([self.now])
        with patch.object(core,'send_daily_report',return_value=True) as smtp:
            runtime.reports(self.env,self.csv,self.now)
            runtime.reports(self.env,self.csv,self.now+timedelta(minutes=1))
            runtime.reports(self.env,self.csv,self.now+timedelta(days=1))
            self.assertEqual(smtp.call_count,1)

    def test_missing_agenda_preserves_daily_schedule(self):
        with patch.object(core,'send_daily_report',return_value=True) as smtp:
            runtime.reports(self.env,self.csv,self.now)
            self.assertEqual(smtp.call_count,1)

    def test_empty_date_agenda_disables_daily(self):
        self.save([])
        with patch.object(core,'send_daily_report') as smtp:
            runtime.reports(self.env,self.csv,self.now)
            smtp.assert_not_called()

    def test_change_is_loaded_without_restart(self):
        self.save([])
        with patch.object(core,'send_daily_report',return_value=True) as smtp:
            runtime.reports(self.env,self.csv,self.now)
            self.save([self.now])
            runtime.reports(self.env,self.csv,self.now)
            self.assertEqual(smtp.call_count,1)

    def test_expired_slot_and_midnight(self):
        slot=agenda.parse_slot('29/09/2026','23:59')
        self.save([slot])
        schedule=agenda.read_schedule()
        self.assertEqual(agenda.due_dates(schedule,slot+timedelta(minutes=3),6),[slot])
        self.assertEqual(agenda.due_dates(schedule,slot+timedelta(minutes=7),6),[])

    def test_corrupt_agenda_never_falls_back_to_daily(self):
        self.path.write_text('{invalid',encoding='utf-8')
        with patch.object(core,'send_daily_report') as smtp:
            with self.assertRaises(ValueError): runtime.reports(self.env,self.csv,self.now)
            smtp.assert_not_called()

    def test_status_and_save_roundtrip(self):
        self.save([self.now])
        self.assertEqual(agenda.read_schedule()['dates'],[self.now.isoformat()])
        self.assertEqual(agenda.slot_status(self.now,self.now,6,{},{}),'Aguardando execução')
        self.assertEqual(agenda.slot_status(self.now,self.now,6,{self.now.isoformat():{'status':'done'}},{}),'Enviado')

    def test_screen_rejects_stale_save_and_past_dates(self):
        envfile=Path(self.temp.name)/'.env'
        envfile.write_text('DAILY_SEND_TOLERANCE_MINUTES=6',encoding='utf-8')
        service=ui.AgendaService(str(envfile),self.csv,self.path)
        current=agenda.read_schedule()
        with patch.object(core,'tz_now',return_value=self.now):
            with self.assertRaises(ValueError):
                service.save(dict(previous=current,config=dict(version=1,mode='dates',dates=[self.now.isoformat()])))
            future=self.now+timedelta(days=1)
            service.save(dict(previous=current,config=dict(version=1,mode='dates',dates=[future.isoformat()])))
            with self.assertRaises(ValueError):
                service.save(dict(previous=current,config=dict(version=1,mode='dates',dates=[])))


if __name__=='__main__':unittest.main()
