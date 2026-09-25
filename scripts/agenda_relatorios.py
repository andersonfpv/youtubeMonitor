"""Tela local no navegador: cadastro da agenda, sem coleta nem envio de e-mails."""
import argparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import webbrowser
import monitor_youtube_live_multi as core
import monitor_runtime as runtime
import report_schedule as agenda


class AgendaService:
    def __init__(self, env_path, csv_path, schedule_path=agenda.DEFAULT_PATH):
        self.env_path, self.csv_path, self.path = env_path, csv_path, Path(schedule_path)

    def snapshot(self):
        config = agenda.read_schedule(self.path)
        env = core.read_env(self.env_path)
        tolerance = int(core.getenv(env,'DAILY_SEND_TOLERANCE_MINUTES',core.getenv(env,'DAILY_SEND_WINDOW_MIN',10)))
        journal = runtime.read_json(runtime.paths_for(self.csv_path)[0])
        legacy = runtime.read_json(core.STATE_FILE)
        now = core.tz_now()
        return dict(config=config, now=now.isoformat(), tolerance=tolerance,
                    daily='; '.join(runtime.daily_times(env)),
                    statuses={raw:agenda.slot_status(datetime.fromisoformat(raw),now,tolerance,journal,legacy) for raw in config['dates']})

    def save(self, payload):
        proposed = agenda.validate(payload['config'])
        expected = agenda.validate(payload['previous'])
        with runtime.lock(str(self.path)+'.edit.lock',wait=2):
            current = agenda.read_schedule(self.path)
            if current != expected:
                raise ValueError('A agenda mudou em outra janela. Recarregue antes de salvar.')
            now = core.tz_now()
            changed = set(current['dates']).symmetric_difference(proposed['dates'])
            if any(datetime.fromisoformat(raw) <= now for raw in changed):
                raise ValueError('Cadastre ou altere apenas horários futuros. Datas passadas são mantidas como histórico.')
            journal = runtime.read_json(runtime.paths_for(self.csv_path)[0])
            if any(raw in journal for raw in changed):
                raise ValueError('Um dos relatórios já foi preparado. Atualize a tela antes de continuar.')
            agenda.save_schedule(proposed,self.path)
        return self.snapshot()


def build_server(service, port=8765):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, code, value, kind='application/json; charset=utf-8'):
            body=value.encode('utf-8') if isinstance(value,str) else json.dumps(value,ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Frame-Options','DENY')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def do_GET(self):
            if not self.valid_host():
                return self.respond(403,{'error':'Endereço local inválido.'})
            try:
                if self.path == '/':
                    html=Path(__file__).with_name('agenda.html').read_text(encoding='utf-8')
                    return self.respond(200,html.replace('__TOKEN__',token),'text/html; charset=utf-8')
                if self.path == '/api' and self.headers.get('X-Agenda-Token') == token:
                    return self.respond(200,service.snapshot())
                self.respond(404,{'error':'Página não encontrada.'})
            except Exception as exc:
                self.respond(400,{'error':str(exc)})

        def do_POST(self):
            if not self.valid_host() or self.path != '/api' or self.headers.get('X-Agenda-Token') != token:
                return self.respond(403,{'error':'Reabra a tela da agenda para continuar.'})
            if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                return self.respond(415,{'error':'Formato inválido.'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 100000:
                    raise ValueError('Agenda muito grande ou conteúdo vazio.')
                payload=json.loads(self.rfile.read(length))
                self.respond(200,service.save(payload))
            except Exception as exc:
                self.respond(400,{'error':str(exc)})

    return ThreadingHTTPServer(('127.0.0.1',port),Handler)


def main():
    parser=argparse.ArgumentParser(description='Cadastro local de datas e horários de relatórios')
    parser.add_argument('--env',default=str(Path(__file__).with_name('.env')))
    parser.add_argument('--csv',default=r'C:\logs\dados_live.csv')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    service=AgendaService(args.env,args.csv)
    service.snapshot()  # Report invalid configuration before opening the browser.
    with build_server(service,args.port) as server:
        url=f'http://127.0.0.1:{server.server_port}/'
        print(f'Agenda disponível em {url}\nMantenha esta janela aberta enquanto editar a agenda. Ctrl+C encerra.',flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        raise SystemExit(f'Não foi possível abrir a agenda: {exc}')
