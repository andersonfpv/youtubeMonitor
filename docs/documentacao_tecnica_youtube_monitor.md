# Documentação Técnica - Projeto YouTube Monitor

**Base analisada:** `monitor_youtube_live_multi_fixed.py`, `.envexemple_fixed`, `daily_send_state.json`

## 1. Objetivo

O projeto monitora uma ou mais lives do YouTube, coleta o número de espectadores simultâneos, grava as leituras em CSV e dispara um relatório diário por e-mail com o arquivo de dados em anexo.

## 2. Arquitetura da solução

A solução é composta por um único script principal em Python, apoiado por arquivos de configuração e estado:

| Componente | Função | Observação |
|---|---|---|
| `monitor_youtube_live_multi_fixed.py` | Script principal | Coleta, grava CSV, envia e-mail, gera backup e controla disparo diário |
| `.env` | Configuração local | SMTP, horários, retries, bloqueio de mídia, limpeza do CSV |
| `dados_live.csv` | Base operacional | Recebe uma linha por URL monitorada em cada execução |
| `__daily_snapshot_<data>_<csv>` | Backup diário | Cópia do CSV no momento do envio |
| `daily_send_state.json` | Estado de disparo | Impede duplicidade por data e horário planejado |

## 3. Fluxo operacional

1. O script lê o arquivo `.env`.
2. Resolve os horários de envio a partir de `DAILY_SEND_TIMES`.
3. Resolve a tolerância pelo parâmetro `DAILY_SEND_TOLERANCE_MINUTES` e, por compatibilidade, `DAILY_SEND_WINDOW_MIN`.
4. Garante a existência do CSV.
5. Abre um navegador headless do Chrome via Selenium.
6. Para cada URL informada, coleta o contador de espectadores e o título da live.
7. Grava uma linha no CSV.
8. Verifica se a execução atual está dentro da janela de envio de algum horário planejado.
9. Se estiver, envia o e-mail, gera o backup `__daily_snapshot_...`, limpa o CSV se configurado e marca o horário como enviado no `daily_send_state.json`.

## 4. Estratégia de coleta do contador

O script usa uma abordagem em camadas para tornar a leitura mais robusta:

- tenta o `aria-label` do elemento `#view-count`
- faz fallback para o texto visível do próprio elemento
- faz uma varredura no DOM procurando expressões como `assistindo agora`
- usa `page_source` como último recurso

Essa estratégia ajuda a reduzir falhas quando o YouTube muda parcialmente o layout ou quando o carregamento está incompleto.

## 5. Estrutura do CSV

O arquivo CSV usa as seguintes colunas:

| Coluna | Significado |
|---|---|
| `timestamp_iso` | Data/hora ISO da coleta |
| `video_url` | URL da live monitorada |
| `video_title` | Título da live/página |
| `concurrent_viewers` | Número de espectadores simultâneos normalizado |
| `raw_counter_text` | Texto bruto capturado para auditoria |

## 6. Modos de execução

### 6.1 Coleta normal

```bash
python monitor_youtube_live_multi_fixed.py --url <URL1> --url <URL2>
```

### 6.2 Teste do e-mail diário

```bash
python monitor_youtube_live_multi_fixed.py --test-daily-email
```

### 6.3 Forçar envio diário

```bash
python monitor_youtube_live_multi_fixed.py --force-daily-email
```

## 7. Configurações do `.env`

| Variável | Exemplo | Função |
|---|---|---|
| `SMTP_HOST` | `smtp.gmail.com` | Host SMTP |
| `SMTP_PORT` | `587` | Porta SMTP |
| `SMTP_USER` | `usuario@gmail.com` | Usuário autenticado |
| `SMTP_PASS` | `senha de app` | Senha SMTP |
| `ALERT_FROM` | `nao-responda@...` | Remetente lógico |
| `ALERT_TO` | `equipe@...` | Destinatário do relatório |
| `ALERT_SUBJECT` | `[MONITOR YT] Relatório diário` | Assunto do e-mail |
| `DAILY_SEND_TIMES` | `07:49;12:00;18:30` | Horários planejados |
| `DAILY_SEND_TOLERANCE_MINUTES` | `6` | Janela de tolerância |
| `DAILY_SEND_WINDOW_MIN` | `6` | Nome alternativo aceito por compatibilidade |
| `DAILY_SEND_HOUR` / `DAILY_SEND_MINUTE` | `0` / `1` | Fallback se `DAILY_SEND_TIMES` estiver vazio |
| `CLEAR_CSV_AFTER_DAILY` | `1` | Limpa o CSV após envio bem-sucedido |
| `BLOCK_MEDIA` | `1` | Ativa bloqueio de mídia |
| `BLOCK_MEDIA_EXT` | `jpg,jpeg,png,...` | Extensões bloqueadas |
| `RETRY_READS` | `3` | Número de tentativas de leitura |
| `RETRY_SLEEP_MS` | `1000` | Espera entre tentativas |

## 8. Lógica de disparo diário

O comportamento corrigido do projeto é o seguinte:

- o script não depende mais de executar exatamente no minuto planejado
- ele aceita execução alguns minutos depois, desde que ainda esteja dentro da tolerância configurada
- o estado é salvo pelo horário planejado, não pelo minuto exato da execução

Exemplo:

```env
DAILY_SEND_TIMES=07:49;12:00;18:30
DAILY_SEND_TOLERANCE_MINUTES=6
```

Se o agendador rodar às `07:50`, o envio ainda acontece. Se rodar às `07:57`, já estará fora da janela de tolerância.

## 9. Arquivo `daily_send_state.json`

Esse arquivo não é uma base de negócio. Ele serve apenas como trava operacional para impedir envio duplicado.

Regras práticas:

- pode ser apagado em homologação para reiniciar testes
- não precisa de manutenção manual em produção
- é recriado/atualizado automaticamente pelo script

## 10. Tratamento de falhas

### 10.1 SMTP incompleto

Se as credenciais SMTP estiverem incompletas, o script não envia o e-mail e registra falha em log.

### 10.2 Contador não encontrado

Se o contador não for encontrado, a linha ainda é gravada no CSV com o campo `concurrent_viewers` vazio e o melhor texto bruto disponível.

### 10.3 Execução fora da janela

Se o agendador executar depois do limite da tolerância, o envio diário não ocorre naquele horário planejado.

## 11. Recomendações operacionais

- executar o script em intervalo menor ou igual à tolerância
- manter o relógio do Windows sincronizado
- usar sempre um único diretório de produção para script, `.env`, CSV e arquivo de estado
- testar o SMTP com `--force-daily-email` sempre que alterar credenciais
- monitorar periodicamente se o layout do YouTube mudou e impactou a leitura do contador

## 12. Resumo técnico

O projeto é simples, robusto e adequado para operação local. O ponto mais sensível é a dependência do navegador e do DOM do YouTube. O ponto de controle mais importante é o agendamento da tarefa em intervalo compatível com a tolerância configurada.
