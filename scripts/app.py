"""Entry point shared by the packaged UI and its isolated worker."""
import os
import sys
from pathlib import Path

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--home',default=str(Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'YouTubeMonitor'/'data'))
    parser.add_argument('--logs')
    parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--no-browser',action='store_true')
    if '--worker' in sys.argv:
        sys.argv.remove('--worker')
        if sys.stdout is None:
            logdir=Path(os.environ['MONITOR_HOME'])/'logs'
            logdir.mkdir(parents=True,exist_ok=True)
            sys.stdout=sys.stderr=(logdir/'worker.log').open('a',encoding='utf-8',buffering=1)
        from monitor_runtime import main as worker
        return worker()
    args=parser.parse_args()
    home=Path(args.home).resolve();logs=Path(args.logs).resolve() if args.logs else home/'logs'
    os.environ['MONITOR_HOME']=str(home)
    home.mkdir(parents=True,exist_ok=True);logs.mkdir(parents=True,exist_ok=True)
    from app_service import AppService
    from dashboard import build_server
    from monitor_runtime import lock
    import webbrowser
    service=AppService(home,logs)
    try:
        with lock(home/'app.lock',wait=0):
            with build_server(logs,home,args.port,service) as server:
                if not args.no_browser: webbrowser.open(f'http://127.0.0.1:{server.server_port}/')
                try: server.serve_forever()
                except KeyboardInterrupt: pass
                finally:
                    service.request_stop()
                    if service.child: service.child.wait()
    except Exception as exc:
        if 'Outra execução mantém o bloqueio: app.lock' in str(exc):
            if not args.no_browser: webbrowser.open(f'http://127.0.0.1:{args.port}/')
            return 0
        with (logs/'app-error.log').open('a',encoding='utf-8') as stream: stream.write(str(exc)+'\n')
        if getattr(sys,'frozen',False):
            import ctypes
            ctypes.windll.user32.MessageBoxW(0,str(exc),'Monitor YouTube',0)
        else: raise
        return 1
    return 0

if __name__=='__main__':
    raise SystemExit(main())
