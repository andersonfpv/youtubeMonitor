#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor YouTube Live (multi URLs) + envio diário em horários configuráveis.

✅ O que este arquivo garante (pontos que você pediu):
- Coleta do contador restaurada (mesma lógica "robusta" da versão OLD):
  * espera elementos carregarem (WebDriverWait)
  * tenta aria-label do #view-count (mais confiável)
  * fallback para texto visível
  * fallback extra: varredura no DOM / page_source (último recurso)
- DAILY_SEND_TIMES permite vários horários por dia (ex.: "00:01;12:00;18:30")
- Compatível com DAILY_SEND_HOUR/DAILY_SEND_MINUTE quando DAILY_SEND_TIMES estiver vazio
- Janela de tolerância configurável via DAILY_SEND_TOLERANCE_MINUTES ou DAILY_SEND_WINDOW_MIN
- Evita duplicidade usando daily_send_state.json
- --test-daily-email e --force-daily-email enviam o e-mail sem precisar passar --url
- Backup __daily_snapshot_YYYY-MM-DD_<nomearquivo>.csv e limpeza do CSV se CLEAR_CSV_AFTER_DAILY=1
"""

import os
import re
import csv
import sys
import ssl
import json
import time
import argparse
import traceback
from datetime import datetime

from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email import encoders
import smtplib

# ----------------- Selenium -----------------
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ----------------- Paths / estado -----------------
HERE = os.path.abspath(os.path.dirname(__file__))
STATE_FILE = os.path.join(HERE, "daily_send_state.json")


# ----------------- Tempo / logs -----------------
def tz_now():
    # horário local da máquina (Brasil)
    return datetime.now()

def log(msg: str):
    stamp = tz_now().strftime("%Y-%m-%dT%H:%M:%S")
    print(f"[{stamp}] {msg}")
    sys.stdout.flush()


# ----------------- .env -----------------
def read_env(path: str):
    env = {}
    if not path:
        return env
    if not os.path.isfile(path):
        log(f"AVISO: .env não encontrado em {path}")
        return env
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if "=" in s:
                k, v = s.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def getenv(env: dict, key: str, default=None, cast=None):
    val = env.get(key, os.environ.get(key, default))
    if cast and val is not None:
        try:
            return cast(val)
        except Exception:
            return default
    return val

def ensure_dir(path: str):
    if path and not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


# ----------------- CSV helpers -----------------
CSV_HEADER = ["timestamp_iso", "video_url", "video_title", "concurrent_viewers", "raw_counter_text"]

def ensure_csv(csv_path: str):
    ensure_dir(os.path.dirname(csv_path))
    if not os.path.isfile(csv_path):
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(CSV_HEADER)

def append_csv(csv_path: str, row):
    ensure_csv(csv_path)
    with open(csv_path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(row)

def backup_and_maybe_clear(csv_path: str, clear_after: bool = True):
    if not os.path.isfile(csv_path):
        return None
    base = os.path.basename(csv_path)
    day = tz_now().strftime("%Y-%m-%d")
    backup_name = f"__daily_snapshot_{day}_{base}"
    backup_path = os.path.join(os.path.dirname(csv_path), backup_name)

    with open(csv_path, "r", encoding="utf-8") as src, open(backup_path, "w", encoding="utf-8") as dst:
        dst.write(src.read())

    if clear_after:
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(CSV_HEADER)

    return backup_path


# ----------------- Estado de envios diários -----------------
def load_send_state():
    if os.path.isfile(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_send_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def parse_daily_times(env: dict):
    """
    DAILY_SEND_TIMES="00:01;12:00;18:30"
    Se vazio -> usa DAILY_SEND_HOUR/DAILY_SEND_MINUTE
    """
    times_str = str(getenv(env, "DAILY_SEND_TIMES", "") or "").strip()
    times = []

    if times_str:
        for chunk in re.split(r"[;,]", times_str):
            t = chunk.strip()
            if re.fullmatch(r"\d{2}:\d{2}", t or ""):
                times.append(t)

    if not times:
        hh = getenv(env, "DAILY_SEND_HOUR", "0")
        mm = getenv(env, "DAILY_SEND_MINUTE", "1")
        if re.fullmatch(r"\d{1,2}", str(hh)) and re.fullmatch(r"\d{1,2}", str(mm)):
            times = [f"{int(hh):02d}:{int(mm):02d}"]

    return sorted(set(times))

def should_send_now(now: datetime, planned_times, send_state, tolerance_minutes=10):
    """
    Permite disparar no horário planejado ou alguns minutos depois,
    evitando perda do envio quando o agendador não roda exatamente no minuto.
    """
    if not planned_times:
        return (False, None)

    today_key = now.strftime("%Y-%m-%d")
    now_minutes = now.hour * 60 + now.minute

    for planned in planned_times:
        try:
            hh, mm = planned.split(":", 1)
            planned_minutes = int(hh) * 60 + int(mm)
        except Exception:
            continue

        diff = now_minutes - planned_minutes

        if diff < 0:
            continue
        if diff > tolerance_minutes:
            continue

        minute_key = planned
        already = send_state.get(today_key, {}).get(minute_key, False)
        if already:
            continue

        return (True, minute_key)

    return (False, None)

def mark_sent(send_state, when: datetime, minute_key: str):
    today_key = when.strftime("%Y-%m-%d")
    send_state.setdefault(today_key, {})[minute_key] = True

    # mantém só ~10 dias
    keys = sorted(send_state.keys())
    if len(keys) > 10:
        for k in keys[:-10]:
            send_state.pop(k, None)


# ----------------- SMTP -----------------
def send_email_smtp(host, port, user, pwd, from_addr, to_addr, subject, html_body, attachments=None):
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    for path in attachments or []:
        if path and os.path.isfile(path):
            part = MIMEBase("application", "octet-stream")
            with open(path, "rb") as f:
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(path)}"')
            msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(user, pwd)
        server.send_message(msg)

def send_daily_report(env: dict, csv_path: str):
    smtp_host = getenv(env, "SMTP_HOST", "")
    smtp_port = int(getenv(env, "SMTP_PORT", "587"))
    smtp_user = getenv(env, "SMTP_USER", "")
    smtp_pass = getenv(env, "SMTP_PASS", "")
    from_addr = getenv(env, "ALERT_FROM", smtp_user or "")
    to_addr   = getenv(env, "ALERT_TO", "")
    subject   = getenv(env, "ALERT_SUBJECT", "[MONITOR YT] Relatório diário")

    if not (smtp_host and smtp_user and smtp_pass and to_addr):
        log("FALHA [daily-email]: Config SMTP incompleta.")
        return False

    html = """<html><body>
      <p>Segue relatório diário do monitor do YouTube.</p>
      <p>Arquivo CSV em anexo.</p>
    </body></html>"""

    attachments = [csv_path] if os.path.isfile(csv_path) else []
    try:
        send_email_smtp(smtp_host, smtp_port, smtp_user, smtp_pass, from_addr, to_addr, subject, html, attachments)
        log(f"[daily-email] Envio OK para {to_addr}")
        return True
    except Exception as e:
        log(f"FALHA [daily-email]: {e}")
        return False


# ----------------- Driver / bloqueios -----------------
def setup_driver(block_media=True, block_exts="", mobile_ua=False):
    """
    Nome 'setup_driver' mantido para compatibilidade.
    """
    chrome_opts = Options()
    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument("--window-size=1280,2200")
    chrome_opts.add_argument("--lang=pt-BR")
    chrome_opts.add_argument("--disable-notifications")
    chrome_opts.add_argument("--mute-audio")

    if mobile_ua:
        chrome_opts.add_argument("--user-agent=Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36")

    driver = webdriver.Chrome(options=chrome_opts)

    if block_media:
        driver.execute_cdp_cmd("Network.enable", {})
        exts = {e.strip().lower() for e in (block_exts or "").split(",") if e.strip()}
        # bloqueio simples por URL pattern
        urls = [f"*.{ext}" for ext in exts]
        if urls:
            driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": urls})

    return driver


# ----------------- Extração do contador (RESTORE OLD LOGIC) -----------------
VIEW_SELECTOR = "#view-count"

# Extrai número pt-BR tipo "1.094" / "12.345"
_PTBR_INT_RE = re.compile(r"(\d{1,3}(?:\.\d{3})*)")

def _normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def parse_ptbr_int_from_text(text: str):
    """
    Extrai inteiro de um texto pt-BR.
    Ex.: "1.094 assistindo agora" -> 1094
    """
    if not text:
        return None
    m = _PTBR_INT_RE.search(text)
    if not m:
        return None
    return int(m.group(1).replace(".", ""))

def extract_viewers_for_url(driver, youtube_live_url: str, retry_reads: int = 3, retry_sleep_ms: int = 1000):
    """
    Versão robusta (baseada na OLD):
    - espera carregamento (ytd-watch-flexy / metadata)
    - tenta aria-label de #view-count
    - tenta texto visível
    - fallback final: varredura no page_source procurando "assistindo agora"
    Retorna (viewers_int_or_None, raw_text, page_title)
    """
    # 1) abre página
    driver.get(youtube_live_url)

    # 2) pequeno scroll para "acordar" layout em headless
    try:
        driver.execute_script("window.scrollTo(0, 400);")
    except Exception:
        pass

    # 3) espera base da página
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-watch-flexy"))
        )
    except Exception:
        # não aborta; só continua com tentativas
        pass

    title_i = ""
    try:
        title_i = driver.title or ""
    except Exception:
        title_i = ""

    last_raw = ""
    for _ in range(max(1, retry_reads)):
        raw = ""

        # A) aria-label do #view-count
        try:
            elem = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, VIEW_SELECTOR))
            )
        except Exception:
            elem = None

        if elem is not None:
            try:
                raw = elem.get_attribute("aria-label") or ""
            except Exception:
                raw = ""

            # se aria-label vazio, tenta texto visível
            if not raw:
                try:
                    raw = elem.text or ""
                except Exception:
                    raw = ""

        raw = _normalize_spaces(raw)
        if raw:
            last_raw = raw

        # validação: preferir textos que contenham "assistindo agora"
        low = raw.lower()
        if "assistindo agora" in low:
            v = parse_ptbr_int_from_text(raw)
            if v is not None:
                return v, raw, title_i

        # B) fallback: procurar outros candidatos "assistindo agora" no DOM
        try:
            candidates = driver.find_elements(By.XPATH, "//*[contains(translate(text(),'ASSISTINDO AGORA','assistindo agora'),'assistindo agora')]")
        except Exception:
            candidates = []

        for c in candidates[:5]:
            try:
                t = _normalize_spaces(c.text or "")
            except Exception:
                t = ""
            if "assistindo agora" in (t.lower()):
                v = parse_ptbr_int_from_text(t)
                if v is not None:
                    return v, t, title_i

        # C) fallback final: page_source (último recurso)
        try:
            html = driver.page_source or ""
        except Exception:
            html = ""
        if html:
            # tenta achar "#### assistindo agora" dentro do HTML
            m = re.search(r'(\d{1,3}(?:\.\d{3})*)\s*assistindo agora', html, flags=re.IGNORECASE)
            if m:
                try:
                    v = int(m.group(1).replace(".", ""))
                    return v, f"{m.group(1)} assistindo agora (page_source)", title_i
                except Exception:
                    pass

        time.sleep(max(0, retry_sleep_ms) / 1000.0)

    return None, last_raw, title_i


# ----------------- main -----------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", help="Caminho do CSV", default=os.path.join("C:\\", "logs", "dados_live.csv"))
    parser.add_argument("--url", action="append", help="URL de live do YouTube (pode repetir)")
    parser.add_argument("--env", help="Caminho do .env", default=os.path.join("C:\\", "scripts", ".env"))
    parser.add_argument("--test-daily-email", action="store_true", help="Envia e-mail agora com o CSV (teste)")
    parser.add_argument("--force-daily-email", action="store_true", help="Força envio diário agora (sem esperar horário)")
    args = parser.parse_args()

    env = read_env(args.env)

    planned_times = parse_daily_times(env)
    clear_after   = str(getenv(env, "CLEAR_CSV_AFTER_DAILY", "1")) == "1"
    tolerance = int(getenv(env, "DAILY_SEND_TOLERANCE_MINUTES", getenv(env, "DAILY_SEND_WINDOW_MIN", "10")))

    block_media = str(getenv(env, "BLOCK_MEDIA", "1")) == "1"
    block_exts  = str(getenv(env, "BLOCK_MEDIA_EXT", "") or "")
    mobile_ua   = str(getenv(env, "MOBILE_UA", "0")) == "1"

    retry_reads = int(getenv(env, "RETRY_READS", "3"))
    retry_sleep = int(getenv(env, "RETRY_SLEEP_MS", "1000"))

    # Execuções especiais: teste/força envio (não exigem URL)
    if args.test_daily_email or args.force_daily_email:
        ensure_csv(args.csv)
        ok = send_daily_report(env, args.csv)
        if ok and clear_after:
            backup = backup_and_maybe_clear(args.csv, clear_after=True)
            if backup:
                log(f"[backup] Gerado: {backup}")
                log("[daily-email] CSV limpo após envio.")
        return

    urls = args.url or []
    if not urls:
        parser.error("Você precisa informar pelo menos uma --url (exceto com --test-daily-email / --force-daily-email).")

    ensure_csv(args.csv)

    send_state = load_send_state()

    # inicia navegador
    driver = setup_driver(block_media=block_media, block_exts=block_exts, mobile_ua=mobile_ua)

    try:
        now = tz_now()

        # coleta
        for url in urls:
            try:
                v, raw, title = extract_viewers_for_url(driver, url, retry_reads=retry_reads, retry_sleep_ms=retry_sleep)
                if v is None:
                    log(f"contador não encontrado | {title} | {url}")
                ts = now.isoformat()
                append_csv(args.csv, [ts, url, title or "", "" if v is None else int(v), raw or ""])
                log(f"{'None' if v is None else int(v)} espectadores | {title} | {url}")
            except Exception as e:
                log(f"FALHA: {e}\n{traceback.format_exc()}")

        # verifica disparo
        do_send, minute_key = should_send_now(now, planned_times, send_state, tolerance_minutes=tolerance)
        if do_send:
            ok = send_daily_report(env, args.csv)
            if ok:
                if clear_after:
                    backup = backup_and_maybe_clear(args.csv, clear_after=True)
                    if backup:
                        log(f"[backup] Gerado: {backup}")
                        log("[daily-email] CSV limpo após envio.")
                mark_sent(send_state, now, minute_key)
                save_send_state(send_state)

    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == "__main__":
    main()
