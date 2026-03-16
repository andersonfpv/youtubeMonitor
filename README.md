# YouTube Monitor

Monitor de lives do YouTube com coleta de espectadores simultâneos via Selenium, persistência em CSV e envio diário de relatório por e-mail.

## Visão geral

Este projeto foi criado para:

- monitorar uma ou mais URLs de live do YouTube
- capturar o contador de espectadores simultâneos
- gravar as leituras em arquivo CSV
- enviar um relatório diário por e-mail com o CSV em anexo
- criar backup diário no formato `__daily_snapshot_YYYY-MM-DD_<arquivo>.csv`
- evitar envios duplicados com controle em `daily_send_state.json`

O script foi pensado para execução local em Windows, com agendamento via **Agendador de Tarefas**.

---

## Funcionalidades

- Coleta robusta do contador da live com múltiplos fallbacks:
  - `aria-label` do elemento `#view-count`
  - texto visível do DOM
  - busca no `page_source`
- Suporte a múltiplas URLs com `--url` repetido
- Envio diário por SMTP
- Suporte a múltiplos horários por dia com `DAILY_SEND_TIMES`
- Janela de tolerância para não perder o envio se o script rodar alguns minutos depois
- Compatibilidade com limpeza automática do CSV após envio
- Backup automático do CSV antes da limpeza
- Bloqueio de mídias no navegador para reduzir consumo

---

## Estrutura do projeto

```text
monitor_youtube_live_multi_fixed.py   # script principal
.env                                  # configuração local
daily_send_state.json                 # controle de envios diários
C:\logs\dados_live.csv               # saída das leituras
```

---

## Requisitos

- Windows 10 ou 11
- Python 3.10+
- Google Chrome instalado
- Selenium
- Acesso à internet
- Conta SMTP válida para envio dos relatórios

---

## Instalação

### 1. Criar pasta do projeto

```powershell
mkdir C:\scripts
mkdir C:\logs
```

### 2. Criar ambiente virtual

```powershell
py -3 -m venv C:\scripts\venv
C:\scripts\venv\Scripts\activate
```

### 3. Instalar dependências

```powershell
pip install --upgrade pip
pip install selenium
```

### 4. Copiar os arquivos

Coloque em `C:\scripts`:

- `monitor_youtube_live_multi_fixed.py`
- `.env`

---

## Configuração do .env

Exemplo:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu_email@gmail.com
SMTP_PASS=sua_senha_de_app

ALERT_FROM=seu_email@gmail.com
ALERT_TO=destinatario@empresa.com
ALERT_SUBJECT=[MONITOR YT] Relatório diário

BLOCK_MEDIA=1
BLOCK_MEDIA_EXT=jpg,jpeg,png,gif,webp,mp4,m4s,webm,m3u8,ts
MOBILE_UA=0
CLEAR_CSV_AFTER_DAILY=1

DAILY_SEND_TIMES=07:49;12:00;18:30
DAILY_SEND_TOLERANCE_MINUTES=6

RETRY_READS=3
RETRY_SLEEP_MS=1000
```

### Variáveis principais

| Variável | Descrição |
|---|---|
| `SMTP_HOST` | Servidor SMTP |
| `SMTP_PORT` | Porta SMTP |
| `SMTP_USER` | Usuário SMTP |
| `SMTP_PASS` | Senha SMTP |
| `ALERT_FROM` | Remetente lógico |
| `ALERT_TO` | Destinatário do relatório |
| `ALERT_SUBJECT` | Assunto do e-mail |
| `DAILY_SEND_TIMES` | Lista de horários em `HH:MM`, separados por `;` ou `,` |
| `DAILY_SEND_TOLERANCE_MINUTES` | Tolerância para disparo após o horário planejado |
| `CLEAR_CSV_AFTER_DAILY` | Limpa o CSV após envio e backup |
| `BLOCK_MEDIA` | Ativa bloqueio de mídias |
| `BLOCK_MEDIA_EXT` | Extensões bloqueadas |
| `RETRY_READS` | Número de tentativas de leitura |
| `RETRY_SLEEP_MS` | Intervalo entre tentativas |

---

## Como executar

### Coleta normal

```powershell
cd C:\scripts
python monitor_youtube_live_multi_fixed.py --url https://www.youtube.com/watch?v=URL1 --url https://www.youtube.com/watch?v=URL2
```

### Testar envio de e-mail

```powershell
cd C:\scripts
python monitor_youtube_live_multi_fixed.py --test-daily-email
```

### Forçar envio diário

```powershell
cd C:\scripts
python monitor_youtube_live_multi_fixed.py --force-daily-email
```

---

## Saída CSV

O arquivo CSV contém as colunas:

- `timestamp_iso`
- `video_url`
- `video_title`
- `concurrent_viewers`
- `raw_counter_text`

Exemplo:

```csv
timestamp_iso,video_url,video_title,concurrent_viewers,raw_counter_text
2026-03-16T08:00:00,https://www.youtube.com/watch?v=abc123,Minha Live,1094,1.094 assistindo agora
```

---

## Lógica do envio diário

O script compara o horário atual com os horários definidos em `DAILY_SEND_TIMES`.

O envio acontece quando:

- a execução ocorre no horário planejado ou alguns minutos depois
- esse atraso está dentro da tolerância configurada
- aquele horário ainda não foi marcado como enviado no `daily_send_state.json`

Exemplo:

```env
DAILY_SEND_TIMES=12:00;18:30
DAILY_SEND_TOLERANCE_MINUTES=10
```

Se o agendador rodar às `12:05`, o envio de `12:00` ainda poderá ocorrer.

---

## daily_send_state.json

Esse arquivo é usado para impedir duplicidade de envio.

Exemplo simplificado:

```json
{
  "2026-03-16": {
    "12:00": true,
    "18:30": true
  }
}
```

Em ambiente de teste, ele pode ser apagado ou zerado para reiniciar o controle:

```json
{}
```

---

## Agendador de Tarefas do Windows

Recomendação:

- executar o script a cada **5 minutos**
- usar tolerância de **6 a 10 minutos**
- habilitar a opção de executar o mais rápido possível após um agendamento perdido

### Exemplo de ação

**Programa/script**
```text
C:\scripts\venv\Scripts\python.exe
```

**Adicionar argumentos**
```text
C:\scripts\monitor_youtube_live_multi_fixed.py --env C:\scripts\.env --csv C:\logs\dados_live.csv --url https://www.youtube.com/watch?v=URL1 --url https://www.youtube.com/watch?v=URL2
```

**Iniciar em**
```text
C:\scripts
```

---

## Troubleshooting

### O e-mail não chega

Verifique:

- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER` e `SMTP_PASS`
- uso de senha de app, se necessário
- conectividade com o servidor SMTP

Teste com:

```powershell
python monitor_youtube_live_multi_fixed.py --force-daily-email
```

### O CSV não recebe dados

Verifique:

- URL válida de live
- acesso ao YouTube na máquina
- Chrome instalado
- Selenium instalado corretamente

### O envio diário falha em alguns horários

Verifique:

- se o script está sendo executado em frequência compatível com a tolerância
- se `DAILY_SEND_TIMES` está correto
- se o relógio do Windows está sincronizado
- se o `daily_send_state.json` não está bloqueando o horário por conta de testes anteriores

### O contador não aparece

O script já usa fallbacks, mas lives com mudança de layout, delay no carregamento ou bloqueios podem exigir ajuste em:

- `RETRY_READS`
- `RETRY_SLEEP_MS`
- bloqueio de mídia

---

## Boas práticas

- manter `.env` fora do versionamento
- não subir credenciais SMTP para o GitHub
- usar um único caminho padrão para script, `.env` e CSV
- testar o envio sempre que alterar destinatários ou credenciais
- monitorar os logs do agendador e do stdout

---

## Sugestão de .gitignore

```gitignore
.env
venv/
__pycache__/
*.pyc
daily_send_state.json
*.log
```

---

## Roadmap

Melhorias futuras possíveis:

- logs estruturados
- resumo analítico no corpo do e-mail
- watchdog para reinício automático
- integração com API do YouTube como fallback
- empacotamento como serviço Windows

---

## Licença

Defina aqui a licença do projeto conforme sua necessidade.
