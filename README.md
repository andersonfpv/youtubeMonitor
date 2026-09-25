# YouTube Monitor

Monitor de espectadores simultâneos de lives do YouTube para Windows, com Selenium, CSV e relatórios SMTP. Oferece execução única ou contínua, sem exigir Agendador de Tarefas.

## Instalação

Requisitos: Windows 10/11, Python 3.10+, Chrome e acesso à internet. Na raiz do repositório:

```powershell
py -3 -m venv scripts\venv
scripts\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item scripts\.env.example scripts\.env
```

Preencha o `.env` local com SMTP, remetente e destinatário. Se já existir uma configuração, preserve-a em vez de sobrescrever. As URLs dos inicializadores são as duas lives originais; ajuste-as se a transmissão mudar.

Para instalação em `C:\scripts`, siga o [guia de instalação](docs/guia_instalacao_youtube_monitor.md). O instalador guarda backup do código e não substitui `.env`, CSV ou estados existentes.

## Executar

- `scripts\iniciar_continuo.bat`: coleta a cada 180 segundos e verifica relatórios a cada aproximadamente 5 segundos, enquanto o computador estiver acordado. Ctrl+C encerra.
- `scripts\rodar_monitor.bat`: uma rodada, compatível com a tarefa existente. O VBS aguarda o processo e propaga seu resultado.
- `scripts\abrir_dashboard.bat`: abre o dashboard local de picos por link, dia e hora. Consulte [dashboard](docs/dashboard.md).

Desabilite a tarefa antiga antes de usar o modo contínuo. Para início no boot e recuperação automática, o modo contínuo pode ser instalado como serviço via [WinSW](https://github.com/winsw/winsw); isso não é feito automaticamente.

Os inicializadores procuram `scripts\venv\Scripts\python.exe`. Alternativamente, defina `MONITOR_PYTHON` com o caminho absoluto de outro Python que tenha as dependências. Não dependem de um nome de usuário específico.

```powershell
scripts\venv\Scripts\python.exe scripts\monitor_youtube_live_multi.py --collect-only --env scripts\.env --csv C:\logs\dados_live.csv --url "https://www.youtube.com/watch?v=juUt-rN5CVo"
```

`--collect-only` não envia relatórios. `--test-daily-email` e `--force-daily-email` enviam um snapshot manual sem apagar dados nem consumir o horário agendado. `--report-only` processa somente relatórios pendentes.

## Confiabilidade e limites

- Contador inteiro completo, priorizando `aria-label`, restrito ao vídeo principal e confirmado como ao vivo. Números abreviados/ambíguos não são convertidos em contagens exatas.
- CSV mantém as cinco colunas originais. Ausência de leitura é campo vazio; zero só é gravado quando observado.
- Fuso `America/Sao_Paulo`, validação de horários e tolerância que atravessa a meia-noite.
- Coleta em processo isolado com timeout. Bloqueios impedem concorrência sobre o mesmo CSV.
- Snapshot imutável com data e hora antes do envio. Novas linhas coletadas durante SMTP são preservadas na limpeza.
- Diário de envio atômico em `dados_live.send-journal.json`; compatibilidade de leitura com o estado antigo. Nunca apague estados em produção para forçar reenvio.
- Em entrega SMTP incerta, preserva o snapshot e suspende o reenvio desse horário até conferência humana. SMTP não oferece garantia de entrega exatamente uma vez.

Os horários do exemplo são **08:57, 09:00 e 09:05**. Com `CLEAR_CSV_AFTER_DAILY=1`, cada relatório cobre o intervalo desde a limpeza anterior. Atrasos do Windows, da rede ou do SMTP podem atrasar envios. Mudanças no YouTube podem impedir a coleta; testes simulados não substituem validação das lives reais.

## Testes

Na raiz do repositório:

```powershell
scripts\venv\Scripts\python.exe -m unittest discover -s scripts -p "test_*.py" -v
scripts\venv\Scripts\python.exe -m py_compile scripts\monitor_youtube_live_multi.py scripts\monitor_runtime.py
```

Testes não acessam YouTube nem enviam e-mails. Veja [validação e migração](docs/validacao.md), [arquitetura](docs/documentacao_tecnica_youtube_monitor.md) e [operação e recuperação](docs/operacao.md).

## Configuração e dados privados

Somente `.env.example` deve ser versionado. CSV, logs, snapshots, credenciais e estados são locais e estão no `.gitignore`. A versão antiga incluía configuração SMTP no histórico público: revogue qualquer credencial real publicada antes de reutilizar a conta. A remoção na versão atual não limpa commits antigos.

Os documentos `.docx` existentes são históricos e não foram atualizados; os guias Markdown são a referência desta versão. `ALERT_ERROR_*` e `ANOMALY_LOG` antigos não implementam alertas de erro; a operação deve acompanhar os logs. Serviço Windows, monitor externo de saúde e retenção de arquivos são melhorias futuras.

## Aplicativo Windows integrado (2.0)

O instalador inclui Python e cria pastas e atalhos. Consulte [instalação e uso do aplicativo](docs/aplicativo-windows.md). A tela reúne Audiência, Agenda, Configurações SMTP e controles Iniciar/Parar/Sair. Para executar a versão em código, use `python scripts/app.py`; o perfil novo usa a pasta de dados do usuário e começa com agenda vazia. A execução antiga em `C:\scripts` continua sendo uma instalação independente.
