# Agenda de relatórios com tela de cadastro

Abra `C:\scripts\abrir_agenda.bat`. A tela abre no navegador em http://127.0.0.1:8765 e aceita conexões somente deste computador. Não exige componentes gráficos adicionais do Python. Mantenha a janela do inicializador aberta enquanto editar a agenda; Ctrl+C encerra a tela local, sem encerrar o monitor.

1. Escolha **Datas e horas cadastradas**.
2. Informe data em DD/MM/AAAA e hora em HH:MM, no horário de Brasília.
3. Clique em **Adicionar à lista**; repita para outros disparos.
4. Clique em **Salvar agenda** para aplicar.

Você pode editar ou excluir datas futuras antes de salvar. Horários já iniciados não podem ser alterados pela tela. Uma lista vazia nesse modo impede novos agendamentos. Para voltar à configuração antiga, escolha **Horários diários do .env** e salve.

A agenda é salva em `report_schedule.json`, ao lado dos scripts. O monitor relê esse arquivo a cada verificação: não é necessário reiniciar o modo contínuo depois de editar a agenda. Após instalar esta atualização do código, porém, reinicie uma vez o monitor antigo para carregar os novos módulos.

## Condições de execução

A janela pode ser fechada após salvar. Ela não coleta dados, não inicia o monitor e não envia e-mails. O monitor precisa continuar ativo pelo Agendador ou pelo modo contínuo.

No modo contínuo, a agenda é verificada aproximadamente a cada cinco segundos. Se a tarefa Windows roda a cada três minutos, a verificação depende desse intervalo. SMTP, rede e disponibilidade do computador podem atrasar o recebimento; a data cadastrada não garante entrega exata na caixa de entrada.

A tolerância continua sendo DAILY_SEND_TOLERANCE_MINUTES (ou DAILY_SEND_WINDOW_MIN) do .env. Exemplo: 14:00 com tolerância de seis minutos permite envio até 14:06. Depois disso, se nenhum relatório foi preparado, o horário aparece como Prazo vencido e não é enviado automaticamente.

Cada data é usada uma única vez e respeita o diário de envio existente. Uma data já enviada também não será reenviada ao alternar os modos. Relatórios que já estavam preparados continuam sendo processados; trocar o modo ou apagar datas futuras não cancela um envio em andamento.

O relatório contém os dados disponíveis no CSV quando o monitor prepara o snapshot, e não apenas dados do dia cadastrado. CLEAR_CSV_AFTER_DAILY continua definindo se as linhas enviadas são limpas após sucesso.

## Situações exibidas

- Agendado: data futura.
- Aguardando execução: horário chegou e está dentro da tolerância.
- Enviado: SMTP confirmou e a limpeza foi tratada.
- Enviado; limpeza pendente: confirmação SMTP recebida, limpeza a retomar.
- Relatório preparado: snapshot pronto para tentativa.
- Conferir entrega: envio iniciado ou incerto; verificar log/provedor antes de reenviar.
- Prazo vencido: horário passou sem envio registrado, fora da tolerância.

O status reflete o diário do CSV padrão `C:\logs\dados_live.csv`. Se o monitor usa outro CSV, abra `agenda_relatorios.py --csv CAMINHO` para consultar o diário correspondente. A agenda é compartilhada pelos monitores instalados na mesma pasta: mantenha apenas uma instância de produção.

## Atualização local

Pare o monitor durante a atualização. Instale junto monitor_runtime.py, report_schedule.py, agenda_relatorios.py, agenda.html e abrir_agenda.bat; não copie apenas a tela. O instalador completo guarda backup dos arquivos anteriores e preserva .env, CSV, estados e agenda existente. Depois abra a tela e reative a tarefa ou o modo contínuo.

Esta versão não cadastra destinatários individuais, recorrência semanal/mensal nem alertas de erro; os e-mails continuam usando remetente, destinatários e assunto do .env.
