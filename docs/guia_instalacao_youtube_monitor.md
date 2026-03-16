# Guia de Instalação e Operação - Projeto YouTube Monitor

## 1. Objetivo

Este documento mostra como instalar o projeto na sua máquina Windows, configurar as dependências, preparar o `.env`, validar o funcionamento e criar o agendamento automático no Agendador de Tarefas.

## 2. Pré-requisitos

Você vai precisar de:

- Windows 10 ou 11
- Python 3.10 ou superior
- Google Chrome instalado
- acesso à internet para o YouTube e para o servidor SMTP
- credenciais SMTP válidas

## 3. Estrutura recomendada de pastas

```text
C:\scripts\
    monitor_youtube_live_multi_fixed.py
    .env
C:\logs\
    dados_live.csv
```

Essa organização segue os caminhos padrão já usados pelo script.

## 4. Instalação do Python e da dependência

Abra o Prompt de Comando ou PowerShell e execute:

```bash
py -3 -m venv C:\scripts\venv
C:\scripts\venv\Scripts\activate
pip install --upgrade pip
pip install selenium
```

Se você não quiser ambiente virtual, basta instalar o `selenium` no Python do sistema.

## 5. Copiar os arquivos do projeto

1. Copie `monitor_youtube_live_multi_fixed.py` para `C:\scripts\`
2. Copie `.envexemple_fixed` para `C:\scripts\`
3. Renomeie `.envexemple_fixed` para `.env`
4. Crie a pasta `C:\logs\` se ela ainda não existir

## 6. Preencher o `.env`

Exemplo recomendado:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu_email@gmail.com
SMTP_PASS=sua_senha_de_app

ALERT_FROM=seu_email@gmail.com
ALERT_TO=equipe.desenvolvimento@a12.com
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

## 7. Primeiro teste manual de coleta

No terminal:

```bash
cd C:\scripts
python monitor_youtube_live_multi_fixed.py --url https://www.youtube.com/watch?v=SEU_VIDEO
```

Valide os seguintes pontos:

- o terminal deve mostrar logs com data/hora
- o CSV `C:\logs\dados_live.csv` deve ser criado
- deve existir pelo menos uma linha de coleta no CSV

## 8. Teste do e-mail diário

Depois de ter um CSV existente, execute:

```bash
cd C:\scripts
python monitor_youtube_live_multi_fixed.py --force-daily-email
```

Valide:

- recebimento do e-mail no destino configurado em `ALERT_TO`
- criação do arquivo `__daily_snapshot_YYYY-MM-DD_dados_live.csv`
- limpeza do CSV se `CLEAR_CSV_AFTER_DAILY=1`

## 9. Criar a tarefa no Agendador de Tarefas

### 9.1 Abrir o agendador

- pressione `Win + R`
- digite `taskschd.msc`
- pressione Enter

### 9.2 Criar a tarefa

- clique em **Criar Tarefa**
- dê um nome como `YouTube Monitor - Coleta`
- marque a execução mesmo sem o usuário estar logado, se necessário

### 9.3 Configurar o disparador

Na guia **Disparadores**:

- crie um disparador diário
- escolha um horário inicial alguns minutos antes do primeiro envio relevante
- marque **Repetir a tarefa a cada 5 minutos**
- duração: **1 dia**

### 9.4 Configurar a ação

Na guia **Ações**, use algo assim:

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

### 9.5 Configurações finais

Na guia **Configurações**:

- habilite execução o mais rápido possível após um agendamento perdido
- permita execução sob demanda
- revise se a tarefa pode rodar por tempo suficiente

## 10. Estratégia recomendada de agenda

| Item | Valor recomendado |
|---|---|
| Frequência da tarefa | a cada 5 minutos |
| Horários de envio | `07:49;12:00;18:30` |
| Tolerância | `6` a `10` minutos |

Regra prática: a tolerância deve ser igual ou maior que o intervalo da tarefa.

## 11. Checklist pós-instalação

- Python funcionando no terminal
- Selenium instalado
- Chrome instalado
- `.env` preenchido
- teste manual de coleta concluído
- teste manual de e-mail concluído
- tarefa agendada criada
- CSV sendo atualizado
- backup diário sendo gerado
- `daily_send_state.json` sendo atualizado

## 12. Solução rápida de problemas

### E-mail não chega

Verifique:

- `SMTP_USER`
- `SMTP_PASS`
- porta `587`
- senha de app, quando aplicável

### CSV não recebe dados

Verifique:

- se a URL da live está correta
- se o Chrome está instalado
- se o Python usado é o mesmo que recebeu `pip install selenium`

### Envio diário perdido

Verifique:

- intervalo do agendador
- valor de `DAILY_SEND_TOLERANCE_MINUTES`
- horário real do Windows

### Duplicidade ou travas de teste

Pode apagar o arquivo `daily_send_state.json` para reiniciar a lógica de homologação.

## 13. Comandos úteis

### Coleta normal

```bash
python monitor_youtube_live_multi_fixed.py --url https://www.youtube.com/watch?v=URL1 --url https://www.youtube.com/watch?v=URL2
```

### Teste de e-mail

```bash
python monitor_youtube_live_multi_fixed.py --test-daily-email
```

### Forçar envio

```bash
python monitor_youtube_live_multi_fixed.py --force-daily-email
```

## 14. Observação final

Para esse projeto funcionar de forma confiável, o mais importante é manter o agendador executando com frequência compatível com a tolerância e validar periodicamente se o YouTube continua expondo o contador de espectadores da mesma forma.
