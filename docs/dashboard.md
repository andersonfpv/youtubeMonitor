# Dashboard de audiência

Abra `C:\scripts\abrir_dashboard.bat`. O painel abrirá em `http://127.0.0.1:8766`, somente neste computador. Ele é somente leitura: não altera CSVs, agenda ou diário de envio.

O painel reúne o CSV ativo e snapshots CSV que estejam dentro de `C:\logs`. Arquivos com o cabeçalho do monitor entram automaticamente. Arquivos com outro formato aparecem como avisos e não entram nos cálculos. Leituras repetidas do mesmo horário e link são deduplicadas. Se duas cópias tiverem contagens diferentes, ambas ficam fora do pico e o painel informa o conflito.

Use os filtros de data, faixa de hora, link e qualidade. Sem selecionar link, todos os links encontrados são usados. O modo “Com contagem válida” exclui falhas de coleta. “Sem contagem / divergentes” ajuda a auditar dados incompletos. O botão “Todos os registros” mostra as leituras individuais e “Exportar esta tabela” baixa a visão filtrada em CSV.

O painel mostra:

- maior pico observado no filtro, com link e momento;
- pico de cada link em cada dia;
- pico por faixa de hora do dia;
- comparação dos picos entre links;
- quantidade de leituras válidas, ausentes, duplicadas e conflitantes.

“Espectadores simultâneos” é a métrica registrada pelo monitor. O painel não soma audiências nem estima espectadores únicos. Como a coleta ocorre em intervalos, um pico entre duas coletas pode não aparecer.

O painel não inclui arquivos cujo nome contenha `teste` ou `test` por padrão. Marque “Incluir arquivos de teste” para auditoria. Ele também lê links definidos nos inicializadores e links encontrados no histórico, mesmo que um link antigo não esteja mais configurado.

O horário exibido é convertido para `America/Sao_Paulo`. Timestamps sem fuso são tratados como Brasília e identificados na contagem de qualidade. Atualize o painel depois que uma coleta ou snapshot novo for criado.
