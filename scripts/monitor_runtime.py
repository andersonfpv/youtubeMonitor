"""Runtime Windows: coleta isolada, exclusão mútua e diário de envio recuperável."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import timedelta
import msvcrt
import monitor_youtube_live_multi as core


@contextmanager
def lock(path, wait=10):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'0'); handle.flush()
        deadline = time.monotonic() + wait
        while True:
            try:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError(f'Outra execução mantém o bloqueio: {path.name}')
                time.sleep(.1)
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def atomic_bytes(path, content):
    path = Path(path)
    temp = path.with_name(path.name + '.tmp')
    with temp.open('wb') as stream:
        stream.write(content); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp, path)


def write_json(path, value):
    atomic_bytes(path, json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8'))


def read_json(path):
    if not Path(path).exists():
        return {}
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError(f'Estado inválido: {path}')
    return value


def daily_times(env):
    raw = str(core.getenv(env, 'DAILY_SEND_TIMES', '') or '').strip()
    if not raw:
        raw = f"{int(core.getenv(env, 'DAILY_SEND_HOUR', 0)):02}:{int(core.getenv(env, 'DAILY_SEND_MINUTE', 1)):02}"
    result = set()
    for part in raw.replace(',', ';').split(';'):
        part = part.strip()
        if not core.re.fullmatch(r'[0-2][0-9]:[0-5][0-9]', part) or int(part[:2]) > 23:
            raise ValueError(f'Horário inválido: {part!r}')
        result.add(part)
    return sorted(result)


def due_slots(now, times, tolerance):
    # Date-aware, including yesterday when the window crosses midnight.
    slots = []
    for days in range(int(tolerance // 1440) + 2):
        day = now - timedelta(days=days)
        for planned in times:
            hour, minute = map(int, planned.split(':'))
            slot = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if 0 <= (now - slot).total_seconds() <= tolerance * 60:
                slots.append(slot)
    return sorted(slots)


def paths_for(csv_path):
    path = Path(csv_path).resolve()
    return path.with_suffix('.send-journal.json'), path.with_suffix('.data.lock')


def finish_cleanup(csv_path, record):
    if not record['clear']:
        return
    snapshot = Path(record['snapshot']).read_bytes()
    active = Path(csv_path).read_bytes()
    if active.startswith(snapshot):
        # Preserve new rows appended while SMTP was working.
        header = snapshot.split(b'\n', 1)[0] + b'\n'
        atomic_bytes(csv_path, header + active[len(snapshot):])
    elif active == snapshot.split(b'\n', 1)[0] + b'\n' or not active.startswith(snapshot.split(b'\n', 1)[0] + b'\n'):
        if active != snapshot.split(b'\n', 1)[0] + b'\n':
            raise RuntimeError('CSV modificado externamente; limpeza suspensa')
    else:
        # Could be an already-completed cleanup followed by new samples.
        # Never guess and delete data after a crash.
        core.log('[recuperação] CSV preservado: prefixo não coincide com snapshot')


def reports(env, csv_path, now=None):
    now = now or core.tz_now()
    journal_path, data_lock = paths_for(csv_path)
    journal = read_json(journal_path)
    legacy = read_json(core.STATE_FILE)
    tolerance = int(core.getenv(env, 'DAILY_SEND_TOLERANCE_MINUTES', core.getenv(env, 'DAILY_SEND_WINDOW_MIN', 10)))
    if not 0 <= tolerance <= 10080:
        raise ValueError('Tolerância deve estar entre 0 e 10080 minutos')
    # Recover accepted sends without sending again.
    for record in journal.values():
        if record['status'] == 'accepted':
            with lock(data_lock):
                finish_cleanup(csv_path, record)
                record['status'] = 'done'
                write_json(journal_path, journal)
    slots = {slot.isoformat(): slot for slot in due_slots(now, daily_times(env), tolerance)}
    # Once prepared, a report survives an expired schedule window.
    for key, record in journal.items():
        if record['status'] == 'prepared':
            slots[key] = core.datetime.fromisoformat(key)
    for key, slot in sorted(slots.items()):
        if legacy.get(slot.strftime('%Y-%m-%d'), {}).get(slot.strftime('%H:%M')):
            continue
        record = journal.get(key)
        if record and record['status'] in ('done', 'sending', 'uncertain'):
            if record['status'] != 'done':
                core.log(f'[ATENÇÃO] envio {key} incerto; conferir SMTP antes de reenviar. Estado: {journal_path}')
            continue
        if record is None:
            with lock(data_lock):
                core.ensure_csv(csv_path)
                snapshot = Path(csv_path).with_name(f"__daily_snapshot_{slot.strftime('%Y-%m-%d_%H-%M')}_{Path(csv_path).name}")
                if snapshot.exists():
                    raise RuntimeError(f'Snapshot órfão preservado; revisar antes de continuar: {snapshot}')
                atomic_bytes(snapshot, Path(csv_path).read_bytes())
                record = dict(status='prepared', snapshot=str(snapshot), clear=str(core.getenv(env, 'CLEAR_CSV_AFTER_DAILY', '1')) == '1')
                journal[key] = record
                write_json(journal_path, journal)
        required = ['SMTP_HOST', 'SMTP_USER', 'SMTP_PASS', 'ALERT_TO']
        if not all(core.getenv(env, name, '') for name in required):
            raise ValueError('SMTP incompleto; snapshot preservado para nova tentativa')
        record['status'] = 'sending'
        write_json(journal_path, journal)
        core.log(f'[envio] previsto={key} atraso_segundos={(core.tz_now()-slot).total_seconds():.1f}')
        ok = core.send_daily_report(env, record['snapshot'])
        record['status'] = 'accepted' if ok else 'uncertain'
        write_json(journal_path, journal)
        if not ok:
            raise RuntimeError('SMTP sem confirmação; dados preservados, reenvio automático suspenso para evitar duplicidade')
        with lock(data_lock):
            finish_cleanup(csv_path, record)
            record['status'] = 'done'
            write_json(journal_path, journal)


def collect(env, args):
    _, data_lock = paths_for(args.csv)
    driver = core.setup_driver(
        block_media=str(core.getenv(env, 'BLOCK_MEDIA', '1')) == '1',
        block_exts=core.getenv(env, 'BLOCK_MEDIA_EXT', ''), mobile_ua=False)
    failed = False
    try:
        for url in args.url:
            value, raw, title = None, '', ''
            try:
                value, raw, title = core.extract_viewers_for_url(driver, url,
                    int(core.getenv(env, 'RETRY_READS', 3)), int(core.getenv(env, 'RETRY_SLEEP_MS', 1000)))
                maximum = int(core.getenv(env, 'OUTLIER_ABS_MAX', 5000000))
                if value is not None and value > maximum:
                    raw = f'rejeitado_acima_de_{maximum}: {raw}'
                    value = None
            except Exception as exc:
                raw = f'falha: {type(exc).__name__}'
                core.log(f'[coleta] {raw}')
            with lock(data_lock):
                core.append_csv(args.csv, [core.tz_now().isoformat(), url, title, '' if value is None else value, raw])
            failed |= value is None
            core.log(f'[coleta] video={url} espectadores={value} texto={raw}')
    finally:
        driver.quit()
    return 1 if failed else 0


def stop_child(child):
    # Only terminate this collector and its descendants, never all Chrome instances.
    subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True)
    child.wait(timeout=15)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', default=r'C:\logs\dados_live.csv')
    parser.add_argument('--env', default=r'C:\scripts\.env')
    parser.add_argument('--url', action='append', default=[])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--continuous', action='store_true')
    mode.add_argument('--collect-only', action='store_true')
    mode.add_argument('--report-only', action='store_true')
    mode.add_argument('--test-daily-email', action='store_true')
    mode.add_argument('--force-daily-email', action='store_true')
    args = parser.parse_args()
    args.csv = str(Path(args.csv).resolve())
    env = core.read_env(args.env)
    daily_times(env)
    core.tz_now()  # Fail early if tzdata is missing.
    if not args.url and not (args.report_only or args.test_daily_email or args.force_daily_email):
        parser.error('Informe ao menos uma --url')
    role = 'collector' if args.collect_only else 'supervisor'
    instance = Path(args.csv).with_suffix(f'.{role}.lock')
    try:
        with lock(instance, wait=0):
            if args.collect_only:
                return collect(env, args)
            if args.test_daily_email or args.force_daily_email:
                # Explicit manual send; never clears data or consumes a scheduled slot.
                _, data_lock = paths_for(args.csv)
                with lock(data_lock):
                    core.ensure_csv(args.csv)
                    snapshot = Path(args.csv).with_name('__manual_snapshot_' + core.tz_now().strftime('%Y-%m-%d_%H-%M-%S-%f') + '.csv')
                    atomic_bytes(snapshot, Path(args.csv).read_bytes())
                return 0 if core.send_daily_report(env, str(snapshot)) else 1
            if args.report_only:
                reports(env, args.csv)
                return 0
            interval = int(core.getenv(env, 'COLLECT_INTERVAL_SECONDS', 180))
            timeout = int(core.getenv(env, 'COLLECT_TIMEOUT_SECONDS', 150))
            if interval < 10 or timeout < 10:
                raise ValueError('Intervalo e timeout devem ser >= 10 segundos')
            child = None
            next_collect = 0
            next_report = 0
            started = 0
            result = 0
            core.log(f'[início] modo={"contínuo" if args.continuous else "único"} horários={daily_times(env)} fuso=America/Sao_Paulo')
            try:
                while True:
                    clock = time.monotonic()
                    if clock >= next_report:
                        try:
                            reports(env, args.csv)
                        except Exception as exc:
                            result = 1
                            core.log(f'[relatório] {exc}')
                        next_report = time.monotonic() + 5
                    if child is None and clock >= next_collect:
                        command = [sys.executable, str(Path(core.__file__).resolve()), '--collect-only', '--csv', args.csv, '--env', str(Path(args.env).resolve())]
                        for url in args.url:
                            command.extend(['--url', url])
                        child = subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW)
                        started = time.monotonic()
                        next_collect = started + interval
                    if child is not None:
                        code = child.poll()
                        if code is None and time.monotonic() - started > timeout:
                            stop_child(child)
                            core.log('[coleta] timeout; processo encerrado, próxima coleta será reiniciada')
                            code = 1
                        if code is not None:
                            result = max(result, int(code != 0))
                            child = None
                            if not args.continuous:
                                reports(env, args.csv)
                                return result
                    time.sleep(1)
            finally:
                if child is not None and child.poll() is None:
                    stop_child(child)
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        core.log(f'[FALHA] {exc}')
        return 1
