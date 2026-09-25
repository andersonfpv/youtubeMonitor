# Monitor corrigido

## Alterações

- Parser exige contador completo, exato e associado a “assistindo agora”. Abreviações e textos ambíguos viram ausência, nunca zero.
- Prioridade do aria-label preservada. Busca limitada ao contador principal, sem varrer recomendações ou HTML global. Confirma identidade e estado ao vivo no player. Mudanças do YouTube podem exigir atualização; na dúvida, não grava número.
- Teto OUTLIER_ABS_MAX aplicado. Não filtra audiências baixas legítimas. Registro bruto preservado no CSV.
- Horário de cada leitura e fuso America/Sao_Paulo explícitos.
- Coleta em processo separado com limite padrão de 150 segundos; verificação dos relatórios a cada 5 segundos enquanto o supervisor estiver executando. Um envio SMTP ainda pode atrasar o próximo; a entrega na caixa postal não tem garantia de horário.
- Lock impede dois supervisores ou dois coletores sobre o mesmo CSV. VBS espera o término e propaga código de saída. Python usa o venv local ou MONITOR_PYTHON com caminho absoluto.
- Snapshots com data e hora; dados recebidos durante SMTP são preservados na limpeza. Diário gravado atomicamente. Estado antigo de envios é respeitado.
- Teste e envio manual nunca limpam CSV nem consomem horário agendado.
- Não existe garantia de “exatamente uma vez” com SMTP: se o envio ficar incerto, o relatório é preservado e não é reenviado automaticamente.

## Instalação compatível com a tarefa atual

Para aplicar, desabilitar temporariamente a tarefa, aguardar a execução atual terminar e abrir scripts\instalar.bat deste repositório. Ele guarda backup e confere os arquivos copiados. Depois escolher reativar a tarefa ou usar o modo contínuo.

Alternativa manual: copiar monitor_youtube_live_multi.py, monitor_runtime.py, rodar_monitor.bat e rodar_monitor_silent.vbs para C:\scripts, guardando backup dos arquivos anteriores. Manter .env e dados existentes. Dependências: selenium e tzdata, declaradas em requirements.txt. Prepare C:\scripts\venv ou defina MONITOR_PYTHON antes de iniciar.

A tarefa atual pode continuar chamando o mesmo VBS. Em execução a cada três minutos, há atraso de até aproximadamente um intervalo, além de indisponibilidades. O novo supervisor verifica relatórios antes, durante e depois da coleta.

Nas propriedades do Agendador, recomendamos:

1. Executar estando o usuário conectado ou não; configurar as credenciais pelo Windows.
2. Em Configurações, não iniciar nova instância se a tarefa já estiver em execução.
3. Executar assim que possível após início agendado perdido.
4. Conferir suspensão, bateria e opção de despertar o computador na aba Condições.
5. Ativar Histórico e acompanhar códigos de retorno. Código 1 representa falha ou leitura indisponível; logs explicam o motivo.
6. Usar compatibilidade apropriada à versão instalada do Windows.

As imagens mostram somente Geral, Disparadores e Ações. Condições, Configurações e Histórico não foram confirmados. Não alteramos essas propriedades via screenshots.

## Sem Agendador: uso simples

Copiar também iniciar_continuo.bat para C:\scripts. Desabilitar a tarefa antiga e abrir iniciar_continuo.bat. O programa coleta a cada 180 segundos e confere horários a cada 5 segundos. Ctrl+C encerra. Requer computador ligado, acordado, conectado e janela em execução; não reinicia sozinho após reiniciar o Windows.

O lock evita dois monitores NOVOS simultâneos; uma instância da versão antiga, iniciada antes da substituição, não reconhece o lock. Concluir a execução antiga antes de iniciar a nova.

## Operação automática permanente

Recomendação: rodar --continuous como serviço Windows via WinSW. O serviço inicia no boot e pode reiniciar após falha, sem tarefa periódica. Instalar e escolher conta/permissões é uma etapa administrativa separada; não instalamos serviço nem software externo nesta entrega. Validar Chrome/Selenium e acesso à rede sob a conta do serviço. Não usar privilégios administrativos para a coleta sem necessidade.

Para não depender deste computador, hospedar o processo em servidor sempre ligado. Isso demanda instalação e manutenção, mas elimina dependência de login, suspensão e desligamento do notebook. Considerar API oficial do YouTube em uma evolução posterior; ela requer credencial e validação da disponibilidade do contador.

Referência WinSW: https://github.com/winsw/winsw

## Configuração preservada e opções novas

Horários atuais: 08:57;09:00;09:05. CLEAR_CSV_AFTER_DAILY=1: cada relatório cobre dados desde a última limpeza. Não representa três cópias do dia completo. Para relatórios acumulados, usar 0 e definir retenção/rotação separadamente.

Opções adicionais, se desejadas no .env:

    COLLECT_INTERVAL_SECONDS=180
    COLLECT_TIMEOUT_SECONDS=150

DAILY_SEND_TOLERANCE_MINUTES=6 permanece. Inclui virada da meia-noite. Horários fora da tolerância sem snapshot preparado não são enviados. Para recuperar períodos maiores de indisponibilidade, aumentar conscientemente a tolerância (máximo de sete dias); os snapshots recuperados contêm os dados disponíveis na recuperação, não uma reconstrução histórica do horário perdido.

MOBILE_UA é desconsiderado: o seletor validado exige layout desktop. ALERT_ON_ERROR, ALERT_ERROR_* e ANOMALY_LOG ainda não têm implementação própria; os erros ficam em yt-monitor.log. Não interpretar essas opções antigas como alertas funcionando. Recomenda-se monitor externo de ausência de coleta e rotação/retenção de logs e snapshots.

## Envio incerto e recuperação

Arquivo de estado novo: C:\logs\dados_live.send-journal.json. Não apagar para “tentar de novo”.

- done: confirmado e limpeza tratada.
- prepared: snapshot preservado e ainda não enviado; tentativa ocorre na próxima execução.
- accepted: SMTP confirmou; limpeza será retomada sem novo envio.
- sending/uncertain: interrupção ou falha sem certeza de entrega. Conferir no provedor e destinatário. Com o monitor parado, após confirmar ausência de entrega, mudar apenas esse registro para prepared. Se já entregue, mudar para accepted. Guardar cópia do estado antes de editar.

Se o CSV foi alterado externamente ou houve falha na janela de limpeza, o sistema prioriza preservá-lo. Pode manter linhas já enviadas em vez de arriscar apagar dados novos; revisar o snapshot antes de correção manual.

## Validação

15 testes automatizados passaram, além da validação de sintaxe. Testes automatizados usam diretórios temporários e SMTP simulado, sem e-mails reais. Execute python -m unittest discover -s scripts -p "test_*.py" -v na raiz do repositório. Cobrem parser, identidade/estado da live, preferência de aria-label, meia-noite, configuração inválida, concorrência, legado, envio incerto, recuperação após aceite e preservação de novas linhas.

A validação real de YouTube e a entrega real de SMTP não são substituídas por esses testes. Após ativação, comparar raw_counter_text e o número da mesma live no mesmo momento; confirmar o próximo relatório e seu atraso no log.

