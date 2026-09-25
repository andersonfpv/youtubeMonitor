# Monitor YouTube — aplicativo Windows 2.0.1

## Instalar e começar

1. Execute `Instalar-Monitor-YouTube.exe` no Windows 10 ou 11, 64 bits (x64). O instalador cria as pastas e atalhos para o usuário atual. Python e bibliotecas já estão incluídos; mantenha o Google Chrome instalado e acesso à internet para coletar as lives.
2. Abra o atalho Monitor YouTube. O painel abre no navegador em `http://127.0.0.1:8766`.
3. Na aba Configurações, cadastre SMTP, remetente, destinatários, links e intervalo. SMTP nesta versão usa STARTTLS (normalmente porta 587). Salve.
4. Na aba Agenda de e-mails, escolha horários diários ou datas específicas. Adicione datas e clique em Salvar agenda. Na primeira instalação, a agenda começa vazia para evitar envios não configurados.
5. Clique em Iniciar coleta. Esse botão ativa também a verificação dos relatórios.

Parar coleta suspende tanto a coleta quanto novos disparos. Se um envio já estiver em andamento, aguarde sua conclusão. Sair solicita essa mesma parada e encerra o aplicativo. Fechar apenas a aba do navegador mantém o aplicativo ativo; o atalho reabre a tela. Após reiniciar o Windows, abra o aplicativo e inicie a coleta novamente. Não há inicialização automática nem serviço nesta versão.

O computador precisa estar ligado, conectado à internet e acordado. O monitor verifica a agenda aproximadamente a cada cinco segundos; SMTP/rede e suspensão do Windows podem atrasar os envios. SMTP aceito não garante chegada à caixa de entrada. A agenda pode ser alterada durante a execução; as configurações exigem a coleta parada.

## Pastas

- Programa: `%LOCALAPPDATA%\Programs\YouTubeMonitor`.
- Configuração, agenda e links: `%LOCALAPPDATA%\YouTubeMonitor\data`.
- CSVs e logs: `%LOCALAPPDATA%\YouTubeMonitor\data\logs`.

As configurações e históricos não são removidos ao desinstalar nem sobrescritos nas atualizações. A senha SMTP é armazenada no `.env` local do usuário, não é devolvida pela API e não é incluída no instalador. Não compartilhe a pasta de configuração.

## Nesta máquina, que já usa C:\scripts

Desabilite a tarefa antiga e encerre o monitor antigo antes de ativar a coleta pelo novo aplicativo, para evitar duas coletas e dois agendamentos independentes. A instalação nova usa uma pasta própria e não migra automaticamente configurações, agenda ou estados de envio existentes. Reconfigure os próximos horários na nova tela; não recrie horários já enviados.

Para consultar o histórico antigo, copie os CSVs e snapshots de `C:\logs` para uma subpasta `historico` dentro da pasta de logs nova. Copie somente os CSVs; mantenha os originais. O painel lê subpastas e ignora arquivos incompatíveis com o cabeçalho esperado, exibindo avisos.

## Validação

43 testes automatizados passaram, incluindo preservação de senha, rejeição de campos inválidos, agenda e estados, picos e controle de execução. A interface foi testada no Chrome com dados temporários: salvar configuração, cadastrar data pela aba Agenda e rejeitar gravação sem token. O executável também foi testado: abertura, criação de pastas, API, início/parada do processo, saída e verificação de relatórios com agenda vazia. O instalador foi compilado; não foi instalado sobre a instalação atual. O pacote não contém credenciais reais nem histórico do usuário. A compatibilidade foi verificada nesta máquina Windows; outros computadores ainda precisam de validação do acesso ao YouTube e SMTP.

O instalador não possui assinatura digital. Políticas corporativas podem exigir liberação pelo TI.

## Horários diários opcionais (2.0.1)

O campo Horários diários pode ficar vazio. Na aba Agenda selecione Somente agendamentos por data e hora, cadastre as datas e salve. As datas cadastradas funcionam sem preencher horários diários. Campo vazio não cria horário padrão de envio. Em atualização, horários já configurados são preservados: apague-os se quiser desativá-los.

Para atualizar, use Sair no aplicativo, aguarde a parada e execute o instalador 2.0.1. Configurações, agenda e histórico permanecem na pasta do usuário.
