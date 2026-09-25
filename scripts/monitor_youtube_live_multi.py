#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Monitor de espectadores simultâneos; execução única ou contínua (--continuous)."""

import os
import re
import csv
import sys
import ssl
import time
from datetime import datetime
from zoneinfo import ZoneInfo

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
    # Fuso explícito; requer tzdata no Windows.
    return datetime.now(ZoneInfo("America/Sao_Paulo"))

def log(msg: str):
    stamp = tz_now().isoformat(timespec="seconds")
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
                value = v.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                env[k.strip()] = value
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
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(user, pwd)
        refused = server.send_message(msg)
        if refused:
            raise RuntimeError("SMTP recusou um ou mais destinatários")

def send_daily_report(env: dict, csv_path: str):
    smtp_host = getenv(env, "SMTP_HOST", "")
    smtp_port = int(getenv(env, "SMTP_PORT", "587"))
    smtp_user = getenv(env, "SMTP_USER", "")
    smtp_pass = getenv(env, "SMTP_PASS", "")
    from_addr = (getenv(env, "ALERT_FROM", "") or smtp_user)
    to_addr   = getenv(env, "ALERT_TO", "")
    subject   = getenv(env, "ALERT_SUBJECT", "[MONITOR YT] Relatório diário")

    if not (smtp_host and smtp_user and smtp_pass and to_addr):
        log("FALHA [daily-email]: Config SMTP incompleta.")
        return False

    html = """<html><body>
      <p>Segue relatório diário do monitor do YouTube.</p>
      <p>Arquivo CSV em anexo.</p>
    </body></html>"""

    if not os.path.isfile(csv_path):
        log("FALHA [daily-email]: snapshot ausente; envio cancelado.")
        return False
    attachments = [csv_path]
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

    chrome_opts.page_load_strategy = "eager"
    driver = webdriver.Chrome(options=chrome_opts)
    driver.set_page_load_timeout(40)
    driver.set_script_timeout(15)

    if block_media:
        driver.execute_cdp_cmd("Network.enable", {})
        exts = {e.strip().lower() for e in (block_exts or "").split(",") if e.strip()}
        # bloqueio simples por URL pattern
        urls = [f"*.{ext}" for ext in exts]
        if urls:
            driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": urls})

    return driver


# ----------------- Extração do contador (RESTORE OLD LOGIC) -----------------
VIEW_SELECTOR = "ytd-watch-flexy #primary #view-count"
_PTBR_INT_RE = re.compile(r"(0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:\.[0-9]{3})+) assistindo agora", re.I)

def _normalize_spaces(s):
    return re.sub(r"\s+", " ", (s or "").strip())

def parse_ptbr_int_from_text(text):
    # Full match: never accept a fragment, abbreviation or animated digit soup.
    match = _PTBR_INT_RE.fullmatch(_normalize_spaces(text))
    return int(match[1].replace(".", "")) if match else None

def extract_viewers_for_url(driver, youtube_live_url, retry_reads=3, retry_sleep_ms=1000):
    from urllib.parse import urlparse, parse_qs
    expected = parse_qs(urlparse(youtube_live_url).query).get("v", [None])[0]
    if not expected:
        raise ValueError("Use URL completa https://www.youtube.com/watch?v=ID")
    driver.get(youtube_live_url)
    last_raw = ""
    for _ in range(max(1, retry_reads)):
        try:
            root = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-watch-flexy")))
            # Require the main player to identify this video as currently live.
            details = driver.execute_script("""
                const p = document.getElementById('movie_player');
                return p && p.getPlayerResponse ? p.getPlayerResponse() : null;
            """) or {}
            video = details.get("videoDetails", {})
            live = details.get("microformat", {}).get("playerMicroformatRenderer", {}).get("liveBroadcastDetails", {})
            current = parse_qs(urlparse(driver.current_url).query).get("v", [None])[0]
            if current != expected or video.get("videoId") != expected:
                raise ValueError("Identidade do vídeo não confirmada")
            if not (video.get("isLive") is True or live.get("isLiveNow") is True):
                raise ValueError("Transmissão não confirmada como ao vivo")
            elems = driver.find_elements(By.CSS_SELECTOR, VIEW_SELECTOR)
            # aria-label has precedence across all main-video candidates.
            for source in ("aria-label", "text"):
                for elem in elems:
                    if not elem.is_displayed():
                        continue
                    if source == "text" and elem.find_elements(By.CSS_SELECTOR, "yt-animated-rolling-number, yt-animated-number"):
                        continue
                    raw = _normalize_spaces(elem.get_attribute("aria-label") if source == "aria-label" else elem.text)
                    if raw:
                        last_raw = raw
                    value = parse_ptbr_int_from_text(raw)
                    if value is not None:
                        log(f"[contador] origem={source} video={expected}")
                        return value, raw, driver.title or ""
        except Exception as exc:
            last_raw = "indisponível: " + str(exc).splitlines()[0][:180]
        time.sleep(max(0, retry_sleep_ms) / 1000)
    return None, last_raw, driver.title or ""


# Runtime separado para agendamento, bloqueios e snapshots recuperáveis.
if __name__ == "__main__":
    from monitor_runtime import main
    sys.exit(main())
