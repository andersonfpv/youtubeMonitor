"""Configuration and lifecycle of the local monitor application."""
import os
import re
import sys
import subprocess
import threading
from pathlib import Path
import monitor_runtime as runtime
import monitor_youtube_live_multi as core
from dashboard_data import canonical_url, configured_links
from agenda_relatorios import AgendaService

FIELDS = ('SMTP_HOST','SMTP_PORT','SMTP_USER','ALERT_FROM','ALERT_TO','ALERT_SUBJECT','DAILY_SEND_TIMES','DAILY_SEND_TOLERANCE_MINUTES','COLLECT_INTERVAL_SECONDS')
DEFAULTS = dict(SMTP_PORT='587', DAILY_SEND_TIMES='', DAILY_SEND_TOLERANCE_MINUTES='10', COLLECT_INTERVAL_SECONDS='180', ALERT_SUBJECT='[MONITOR YT] Relatório')

class AppService:
    def __init__(self, home, logs):
        self.home, self.logs = Path(home), Path(logs)
        self.home.mkdir(parents=True,exist_ok=True); self.logs.mkdir(parents=True,exist_ok=True)
        self.env = self.home / '.env'
        self.csv = self.logs / 'dados_live.csv'
        self.stop = self.home / 'stop.request'
        self.child = None
        self.guard = threading.RLock()
        self.agenda = AgendaService(str(self.env),str(self.csv),self.home/'report_schedule.json')
        if not self.env.exists():
            runtime.atomic_bytes(self.env, ''.join(f'{k}={v}\n' for k,v in DEFAULTS.items()).encode())
        if not (self.home/'report_schedule.json').exists():
            import report_schedule
            report_schedule.save_schedule(dict(version=1,mode='dates',dates=[]),self.home/'report_schedule.json')

    def settings(self):
        env=core.read_env(str(self.env))
        value={k:env.get(k,DEFAULTS.get(k,'')) for k in FIELDS}
        value['password_saved']=bool(env.get('SMTP_PASS'))
        cfg=runtime.read_json(self.home/'app_settings.json')
        value['urls']=cfg.get('urls',configured_links(self.home))
        return value

    def save(self,value):
        with self.guard:
            if self.status()['running']:
                raise ValueError('Pare a coleta antes de alterar a configuração. A agenda pode ser editada durante a execução.')
            updated={k:str(value.get(k,'')).strip() for k in FIELDS}
            password=str(value.get('SMTP_PASS',''))
            if any('\n' in v or '\r' in v or '\x00' in v for v in [*updated.values(),password]):
                raise ValueError('Os campos não podem conter quebras de linha.')
            for key,lo,hi in [('SMTP_PORT',1,65535),('COLLECT_INTERVAL_SECONDS',10,86400),('DAILY_SEND_TOLERANCE_MINUTES',1,1440)]:
                if not updated[key].isdigit() or not lo<=int(updated[key])<=hi: raise ValueError('Valor inválido: '+key)
            runtime.daily_times(updated)
            if updated['SMTP_HOST'] and not re.fullmatch(r'[a-zA-Z0-9.\-]+',updated['SMTP_HOST']): raise ValueError('Servidor SMTP inválido.')
            for key in ('ALERT_FROM','ALERT_TO'):
                if updated[key] and any(not re.fullmatch(r'[^\s@,;<>]+@[^\s@,;<>]+', x.strip()) for x in updated[key].split(',')):
                    raise ValueError('Informe e-mail válido; separe destinatários por vírgula.')
            urls=value.get('urls',[])
            if not isinstance(urls,list) or len(urls)>50: raise ValueError('Informe até 50 links.')
            urls=list(dict.fromkeys(canonical_url(str(x)) for x in urls if str(x).strip()))
            if any('/watch?v=' not in x for x in urls): raise ValueError('Informe links de vídeos, não canais.')
            with runtime.lock(self.home/'settings.edit.lock',wait=2):
                env=core.read_env(str(self.env));env.update(updated)
                if password: env['SMTP_PASS']=password
                runtime.atomic_bytes(self.env, ''.join(f'{k}="{v}"\n' for k,v in env.items()).encode('utf-8'))
                runtime.write_json(self.home/'app_settings.json',dict(urls=urls))
            return self.settings()

    def status(self):
        with self.guard:
            code=self.child.poll() if self.child else None
            running=self.child is not None and code is None
            return dict(running=running,stopping=running and self.stop.exists(),exit_code=code,
                        logs=str(self.logs),home=str(self.home))

    def start(self):
        with self.guard:
            if self.status()['running']: return self.status()
            urls=self.settings()['urls']
            if not urls: raise ValueError('Cadastre pelo menos um link nas configurações.')
            # Detect another monitor using the same data before launching.
            with runtime.lock(self.csv.with_suffix('.supervisor.lock'),wait=0): pass
            self.stop.unlink(missing_ok=True)
            cmd=([sys.executable,'--worker'] if getattr(sys,'frozen',False) else [sys.executable,str(Path(core.__file__).resolve())])
            cmd+=['--continuous','--env',str(self.env),'--csv',str(self.csv),'--stop-file',str(self.stop)]
            for url in urls: cmd+=['--url',url]
            env=os.environ.copy();env['MONITOR_HOME']=str(self.home)
            with (self.logs/'yt-monitor.log').open('ab') as stream:
                self.child=subprocess.Popen(cmd,stdout=stream,stderr=stream,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
            return self.status()

    def request_stop(self):
        with self.guard:
            if self.status()['running']: self.stop.write_text('stop',encoding='ascii')
            return self.status()
