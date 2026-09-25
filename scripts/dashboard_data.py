"""Consulta somente leitura de CSVs do monitor, com histórico e picos por link."""
import csv
import json
from datetime import datetime, date
from pathlib import Path
import re
from urllib.parse import urlparse, parse_qs
from zoneinfo import ZoneInfo

ZONE = ZoneInfo('America/Sao_Paulo')
HEADER = {'timestamp_iso', 'video_url', 'video_title', 'concurrent_viewers', 'raw_counter_text'}


def canonical_url(value):
    parsed = urlparse(value.strip())
    host = (parsed.hostname or '').lower()
    if host == 'youtu.be':
        vid = parsed.path.strip('/').split('/')[0]
    elif host in ('youtube.com','www.youtube.com','m.youtube.com'):
        vid = parse_qs(parsed.query).get('v',[''])[0]
        if not vid and parsed.path.startswith(('/live/','/shorts/')):
            vid = parsed.path.split('/')[2]
        if not vid:
            return 'https://www.youtube.com' + parsed.path.rstrip('/')
    else:
        raise ValueError('URL fora do YouTube')
    if not re.fullmatch(r'[A-Za-z0-9_-]+',vid):
        raise ValueError('ID de vídeo inválido')
    return 'https://www.youtube.com/watch?v=' + vid


def configured_links(folder):
    result = set()
    config = Path(folder)/'app_settings.json'
    if config.exists():
        for value in json.loads(config.read_text(encoding='utf-8')).get('urls',[]):
            result.add(canonical_url(value))
    for name in ('rodar_monitor.bat','iniciar_continuo.bat'):
        path = Path(folder)/name
        if path.exists():
            text = path.read_text(encoding='utf-8-sig')
            for match in re.finditer(r'--url\s+(?:"([^"]+)"|([^\s]+))',text):
                try:
                    result.add(canonical_url(match[1] or match[2]))
                except ValueError:
                    pass
    return sorted(result)


def sources(folder, include_tests):
    if not Path(folder).is_dir():
        raise ValueError('A pasta de dados não existe: ' + str(folder))
    return sorted(p for p in Path(folder).rglob('*.csv')
                  if include_tests or not re.search(r'(teste|test)[_-]',p.name,re.I))


def signature(paths):
    return [(str(p),p.stat().st_size,p.stat().st_mtime_ns) for p in paths]


def load_records(folder, include_tests=False):
    # Retry if the collector appends or rotates files during the read.
    for attempt in range(3):
        try:
            files = sources(folder,include_tests)
            before = signature(files)
            result = _load(files,Path(folder))
            after_files = sources(folder,include_tests)
            if before == signature(after_files):
                return result
        except FileNotFoundError:
            continue
    raise ValueError('Os arquivos mudaram durante a leitura. Clique em Atualizar novamente.')


def _load(files, folder):
    groups = {}
    warnings = []
    counts = dict(files=0,duplicates=0,malformed=0,conflicts=0,naive_timestamps=0)
    for path in files:
        source = path.relative_to(folder).as_posix()
        try:
            with path.open(encoding='utf-8-sig',newline='') as stream:
                reader = csv.DictReader(stream)
                if not HEADER.issubset(reader.fieldnames or []):
                    warnings.append(f'{source}: cabeçalho incompatível; arquivo não incluído.')
                    continue
                counts['files'] += 1
                for line,row in enumerate(reader,2):
                    try:
                        if None in row or any(row[k] is None for k in HEADER):
                            raise ValueError('linha incompleta')
                        stamp = datetime.fromisoformat(row['timestamp_iso'])
                        if stamp.tzinfo is None:
                            counts['naive_timestamps'] += 1
                            stamp = stamp.replace(tzinfo=ZONE)
                        stamp = stamp.astimezone(ZONE)
                        url = canonical_url(row['video_url'])
                        number = row['concurrent_viewers'].strip()
                        value = int(number) if re.fullmatch(r'[0-9]+',number) else None
                        reason = '' if value is not None else ('Sem contagem' if not number else 'Número inválido')
                        raw = re.sub(r'\s+',' ',row['raw_counter_text'].strip())
                        exact = re.fullmatch(r'([0-9]+|[1-9][0-9]{0,2}(?:\.[0-9]{3})+) assistindo agora(?: \(page_source\))?',raw,re.I)
                        if exact and value is not None and int(exact[1].replace('.','')) != value:
                            value,reason = None,'Divergência entre número e texto'
                        key = (stamp.isoformat(),url)
                        item = dict(timestamp=key[0],date=stamp.strftime('%Y-%m-%d'),hour=stamp.hour,
                                    url=url,title=row['video_title'].strip() or url,
                                    viewers=value,raw=raw,status=reason or 'Válida',sources=[source],line=line)
                        existing = groups.get(key)
                        if existing is None:
                            groups[key]=item
                        else:
                            counts['duplicates'] += 1
                            existing['sources']=sorted(set(existing['sources']+[source]))
                            if existing['status']=='Contagem conflitante':
                                continue
                            if existing['viewers'] != value:
                                existing['viewers']=None
                                existing['status']='Contagem conflitante'
                                counts['conflicts'] += 1
                    except (ValueError,TypeError,KeyError,OverflowError):
                        counts['malformed'] += 1
        except (OSError,UnicodeError,csv.Error) as exc:
            warnings.append(f'{source}: leitura incompleta ({type(exc).__name__}).')
    return sorted(groups.values(),key=lambda r:(r['timestamp'],r['url'])),counts,warnings


def summarize(records, start='', end='', urls=None, hour_start=0, hour_end=23, quality='all'):
    if start: date.fromisoformat(start)
    if end: date.fromisoformat(end)
    if start and end and start>end: raise ValueError('A data inicial deve ser anterior à final.')
    if not 0 <= hour_start <= hour_end <= 23: raise ValueError('Intervalo de horas inválido.')
    if quality not in ('all','valid','missing'): raise ValueError('Filtro de qualidade inválido.')
    filtered=[r for r in records if (not start or r['date']>=start) and (not end or r['date']<=end)
              and (not urls or r['url'] in urls) and hour_start<=r['hour']<=hour_end
              and (quality=='all' or (r['viewers'] is not None)==(quality=='valid'))]
    valid=[r for r in filtered if r['viewers'] is not None]
    daily,hourly,clock,links={},{},{},{}
    for r in filtered:
        for table,key in ((daily,(r['date'],r['url'])),(hourly,(r['date'],r['hour'],r['url'])),
                          (clock,(r['hour'],r['url'])),(links,(r['url'],))):
            group=table.setdefault(key,dict(date=r['date'],hour=r['hour'],url=r['url'],title=r['title'],peak=None,at=None,valid=0,missing=0))
            group['title']=r['title']
            if r['viewers'] is None:
                group['missing']+=1
            else:
                group['valid']+=1
                if group['peak'] is None or r['viewers']>group['peak']:
                    group['peak']=r['viewers'];group['at']=r['timestamp']
                    # Link-level cards must describe the row that produced
                    # the peak, even when the first row was another day/hour.
                    group['date']=r['date'];group['hour']=r['hour'];group['title']=r['title']
    peak=max(valid,key=lambda r:r['viewers']) if valid else None
    return dict(records=filtered,daily=[daily[k] for k in sorted(daily)],hourly=[hourly[k] for k in sorted(hourly)],
                clock=[clock[k] for k in sorted(clock)],links=sorted(links.values(),key=lambda x:-(x['peak'] if x['peak'] is not None else -1)),
                metrics=dict(total=len(filtered),valid=len(valid),missing=len(filtered)-len(valid),
                             links=len(links),days=len(set(r['date'] for r in filtered)),peak=peak))


def dashboard(folder, script_folder, filters):
    rows,counts,warnings=load_records(folder,filters.get('tests')=='1')
    catalog={u:dict(url=u,title=u,configured=True) for u in configured_links(script_folder)}
    for row in rows:
        old=catalog.get(row['url'],{})
        catalog[row['url']]=dict(url=row['url'],title=row['title'],configured=old.get('configured',False))
    result=summarize(rows,filters.get('start',''),filters.get('end',''),filters.get('urls',[]),
                     int(filters.get('hour_start',0)),int(filters.get('hour_end',23)),filters.get('quality','all'))
    result.update(catalog=list(catalog.values()),ingestion=counts,warnings=warnings,
                  available=dict(start=rows[0]['date'] if rows else None,end=rows[-1]['date'] if rows else None),
                  updated=datetime.now(ZONE).isoformat(),folder=str(folder))
    return result
