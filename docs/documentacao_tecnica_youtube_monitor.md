# Arquitetura atual

`scripts/monitor_youtube_live_multi.py` contém configuração, coleta Selenium, CSV e SMTP. `scripts/monitor_runtime.py` controla agendamento, processos, bloqueios e recuperação de relatórios.

O supervisor inicia um processo `--collect-only` e continua verificando os horários. O coletor grava cada leitura com seu horário efetivo, sob um bloqueio curto de dados. SMTP não depende de o Chrome iniciar ou concluir. Em modo contínuo, a próxima rodada ocorre a cada 180 segundos por padrão; rodadas não se sobrepõem.

## Contador

Confirma o ID solicitado no player, o endereço atual e o estado ao vivo. Consulta somente `ytd-watch-flexy #primary #view-count`, priorizando aria-label. O parser exige o texto completo `número assistindo agora`, aceita inteiros sem separador ou milhares com ponto e rejeita abreviações. O fallback textual ignora componentes animados conhecidos. Nunca pesquisa números em toda a página. OUTLIER_ABS_MAX limita a leitura antes da gravação.

## Relatórios

Cada horário é identificado por data/hora com fuso. A tolerância inclui horários do dia anterior. Slots preparados persistem mesmo depois de sua janela expirar; horários nunca preparados e vencidos não são recuperados automaticamente.

Snapshot: `__daily_snapshot_YYYY-MM-DD_HH-MM_<csv>`. Diário: `<csv-sem-extensão>.send-journal.json`. Estados: prepared, sending, uncertain, accepted, done. Um estado ilegível interrompe o processamento de relatórios, em vez de fingir que nada foi enviado. O CSV é limpo somente após confirmação SMTP, preservando o sufixo de novas linhas.

Após falha entre envio e confirmação local, não há como provar entrega exatamente uma vez. Sending/uncertain requer conferência. Após accepted, a limpeza é retomada sem reenviar. Em divergência de conteúdo após interrupção, preserva dados em vez de adivinhar quais linhas excluir.

## Operação

Bloqueios Windows msvcrt: supervisor, coletor e dados, identificados pelo CSV. O supervisor limita a duração da coleta e encerra apenas a árvore de seu próprio processo filho. Timeout SMTP de 30 segundos por operação de socket; esse timeout não é um prazo global para toda a conversa SMTP.

Não há serviço instalado automaticamente nem garantia de horário exato de entrega. Ver [operação](operacao.md) e [validação](validacao.md). Os documentos Word nesta pasta descrevem a versão anterior e são históricos.
