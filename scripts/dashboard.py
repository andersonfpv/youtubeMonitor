"""Dashboard local e somente leitura do histórico de espectadores."""
import argparse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import secrets
from urllib.parse import urlparse,parse_qs
import webbrowser
from dashboard_data import dashboard


def build_server(folder, script_folder, port=8766, service=None):
    token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def respond(self,code,value,kind='application/json; charset=utf-8'):
            content=(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False)).encode('utf-8')
            self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(content)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Frame-Options','SAMEORIGIN')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'self'")
            self.end_headers();self.wfile.write(content)
        def do_GET(self):
            if self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}':return self.respond(403,{'error':'Endereço inválido.'})
            parsed=urlparse(self.path)
            try:
                if parsed.path=='/':
                    html=Path(__file__).with_name('dashboard.html').read_text(encoding='utf-8')
                    return self.respond(200,html.replace('__TOKEN__',token),'text/html; charset=utf-8')
                if service and parsed.path=='/agenda':
                    html=Path(__file__).with_name('agenda.html').read_text(encoding='utf-8').replace("fetch('/api'","fetch('/api/agenda'").replace('X-Agenda-Token','X-Dashboard-Token')
                    return self.respond(200,html.replace('__TOKEN__',token),'text/html; charset=utf-8')
                if service and parsed.path in ('/api/settings','/api/control','/api/agenda') and self.headers.get('X-Dashboard-Token')==token:
                    result={'/api/settings':service.settings,'/api/control':service.status,'/api/agenda':service.agenda.snapshot}[parsed.path]()
                    return self.respond(200,result)
                if parsed.path=='/api' and self.headers.get('X-Dashboard-Token')==token:
                    query=parse_qs(parsed.query)
                    filters={key:value[-1] for key,value in query.items() if key!='url'}
                    filters['urls']=query.get('url',[])
                    return self.respond(200,dashboard(folder,script_folder,filters))
                self.respond(404,{'error':'Página não encontrada.'})
            except Exception as exc:self.respond(400,{'error':str(exc)})
        def do_POST(self):
            if not service or self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}' or self.headers.get('X-Dashboard-Token')!=token:
                return self.respond(403,{'error':'Reabra o painel para continuar.'})
            try:
                if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                    raise ValueError('Formato inválido.')
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=100000: raise ValueError('Conteúdo inválido.')
                payload=json.loads(self.rfile.read(length))
                if self.path=='/api/settings': result=service.save(payload)
                elif self.path=='/api/agenda': result=service.agenda.save(payload)
                elif self.path=='/api/control':
                    if payload.get('action') not in ('start','stop','exit'): raise ValueError('Ação inválida.')
                    result=service.start() if payload['action']=='start' else service.request_stop()
                    if payload['action']=='exit':
                        import threading
                        threading.Thread(target=self.server.shutdown,daemon=True).start()
                else: return self.respond(404,{'error':'Página não encontrada.'})
                self.respond(200,result)
            except Exception as exc: self.respond(400,{'error':str(exc)})
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)


def main():
    parser=argparse.ArgumentParser(description='Painel de espectadores simultâneos')
    parser.add_argument('--logs',default=r'C:\logs')
    parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    import os
    os.environ['MONITOR_HOME']=str(Path(__file__).parent)
    from app_service import AppService
    service=AppService(Path(__file__).parent,Path(args.logs).resolve())
    with build_server(Path(args.logs).resolve(),Path(__file__).parent,args.port,service) as server:
        url=f'http://127.0.0.1:{server.server_port}/'
        print(f'Dashboard: {url}\nCtrl+C encerra o painel e solicita a parada do monitor.',flush=True)
        if not args.no_browser:webbrowser.open(url)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:
            service.request_stop()
            if service.child: service.child.wait()

if __name__=='__main__':
    try:main()
    except Exception as exc:raise SystemExit(f'Não foi possível abrir o painel: {exc}')
