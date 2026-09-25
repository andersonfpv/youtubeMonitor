"""Agenda local de relatórios. A tela e o monitor compartilham este formato."""
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

ZONE = ZoneInfo('America/Sao_Paulo')
DEFAULT_PATH = Path(os.environ.get('MONITOR_HOME', Path(__file__).parent)) / 'report_schedule.json'


def parse_slot(date_text, time_text):
    try:
        result = datetime.strptime(f'{date_text.strip()} {time_text.strip()}', '%d/%m/%Y %H:%M')
    except ValueError as exc:
        raise ValueError('Informe uma data válida (DD/MM/AAAA) e hora (HH:MM).') from exc
    return result.replace(tzinfo=ZONE)


def validate(value):
    if not isinstance(value, dict) or value.get('version') != 1:
        raise ValueError('Formato de agenda inválido.')
    if value.get('mode') not in ('daily', 'dates'):
        raise ValueError('Modo de agenda inválido.')
    slots = value.get('dates')
    if not isinstance(slots, list):
        raise ValueError('Lista de datas inválida.')
    parsed = []
    for raw in slots:
        if not isinstance(raw, str):
            raise ValueError('Data inválida na agenda.')
        try:
            slot = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError('Data inválida na agenda.') from exc
        if slot.tzinfo is None or slot.second or slot.microsecond:
            raise ValueError('Cada data deve incluir fuso e precisão de minutos.')
        parsed.append(slot.astimezone(ZONE).isoformat())
    if len(set(parsed)) != len(parsed):
        raise ValueError('A agenda contém datas e horários repetidos.')
    return dict(version=1, mode=value['mode'], dates=sorted(parsed))


def read_schedule(path=None):
    path = Path(path or DEFAULT_PATH)
    if not path.exists():
        return dict(version=1, mode='daily', dates=[])
    return validate(json.loads(path.read_text(encoding='utf-8-sig')))


def save_schedule(value, path=DEFAULT_PATH):
    value = validate(value)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def due_dates(schedule, now, tolerance):
    return [slot for raw in schedule['dates']
            if 0 <= (now - (slot := datetime.fromisoformat(raw))).total_seconds() <= tolerance * 60]


def slot_status(slot, now, tolerance, journal, legacy):
    state = journal.get(slot.isoformat(), {}).get('status')
    if state:
        return {'done': 'Enviado', 'accepted': 'Enviado; limpeza pendente',
                'prepared': 'Relatório preparado', 'sending': 'Conferir entrega',
                'uncertain': 'Conferir entrega'}.get(state, 'Conferir estado')
    if legacy.get(slot.strftime('%Y-%m-%d'), {}).get(slot.strftime('%H:%M')):
        return 'Enviado'
    if now < slot:
        return 'Agendado'
    if (now - slot).total_seconds() <= tolerance * 60:
        return 'Aguardando execução'
    return 'Prazo vencido'
