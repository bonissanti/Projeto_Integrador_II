# Projeto Integrador II

Sistema de agendamento para um salão de tranças. Clientes podem agendar pelo site ou pelo Telegram; a profissional administra agenda, serviços e estoque pelo painel do sistema.

## Funcionalidades

- Agendamentos pelo site e pelo bot do Telegram
- Gestão de clientes, serviços e agenda pelo Django Admin
- Sincronização de agendamentos com o Google Calendar
- Controle de estoque e alertas de reposição pelo Telegram
- Acessibilidade por teclado, suporte a leitores de tela e modo de alto contraste

> [!NOTE]
> O bot ativo é o do Telegram. O repositório ainda contém código legado de integração com WhatsApp.

## Tecnologias

Python 3.12+, Django 6, SQLite (desenvolvimento), PostgreSQL (produção), Telegram Bot API, Google Calendar API e Gunicorn.

## Executar localmente

### Requisitos

- Python 3.12 ou superior
- Make
- Git

> [!TIP]
> No Windows, execute os comandos pelo Git Bash ou WSL.

### Instalação

```bash
git clone https://github.com/bonissanti/Projeto_Integrador_II.git
cd Projeto_Integrador_II
make setup
make migrate
make createsuperuser
make runserver
```

Site: `http://localhost:8000`<br>
Painel administrativo: `http://localhost:8000/admin/`

### Configurar integrações

O `make setup` cria o `.env` se ainda não existir. Para usar o bot, configure nele:

```dotenv
TELEGRAM_BOT_TOKEN=token-do-seu-bot
TELEGRAM_WEBHOOK_SECRET=segredo-opcional-do-webhook
TELEGRAM_ADMIN_CHAT_ID=chat-id-para-alertas-de-estoque
```

Para sincronizar eventos com o Google Calendar, adicione a credencial da service account em `Backend/proj_integrador/calendar_credentials.json`.

> [!IMPORTANT]
> Nunca envie tokens, credenciais ou URLs de banco de dados para o Git. Sem as credenciais do Google, o sistema salva os agendamentos, mas não sincroniza os eventos.

## Como usar

Consulte o [manual de uso do sistema](./docs/como_usar.md) para acessar o painel e gerenciar o estoque.

## Acessibilidade

- Navegação por teclado e suporte a leitores de tela
- Anúncio de erros e de datas disponíveis no agendamento
- Foco movido entre as etapas do formulário
- Modo de alto contraste, com preferência salva no navegador
- Respeito à preferência do sistema por movimento reduzido

## Testes

```bash
make test
make check
```

`make test` inclui os testes de acessibilidade.

## Publicação no Render

Configure `DATABASE_URL` (PostgreSQL), `SECRET_KEY` e `DEBUG=False` nas variáveis de ambiente do serviço. Para o bot, configure também `TELEGRAM_BOT_TOKEN` e, se usado, `TELEGRAM_WEBHOOK_SECRET` e `TELEGRAM_ADMIN_CHAT_ID`.

No primeiro start, `make render-start` cria o superusuário padrão se ainda não houver nenhum: usuário `admin`, senha `12345`. A conta existente não é alterada. **Troque essa senha imediatamente após o primeiro acesso ao painel.**

Defina os comandos do serviço:

**Build Command**

```bash
make render-build
```

**Start Command**

```bash
make render-start
```

> [!WARNING]
> O Render deve usar a raiz deste repositório como diretório do serviço. As migrações criam o esquema no PostgreSQL, mas não copiam dados existentes do SQLite.

## Comandos úteis

| Comando | Uso |
|---|---|
| `make setup` | Instala dependências e prepara o ambiente local |
| `make migrate` | Aplica migrações |
| `make runserver` | Inicia o servidor local |
| `make test` | Executa os testes |
| `make check` | Verifica a configuração do Django |
| `make render-build` | Instala dependências e coleta estáticos no Render |
| `make render-start` | Aplica migrações e inicia Gunicorn no Render |
