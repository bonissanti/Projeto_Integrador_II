# Projeto Integrador II

Sistema web para agendamento e gerenciamento de usuários, desenvolvido em Django como parte do Projeto Integrador I da Univesp.

Os clientes fazem agendamentos via **bot do WhatsApp**; ao confirmar, o agendamento é persistido no banco e um evento é criado automaticamente no **Google Calendar** da profissional. A gestão de clientes, serviços e agendamentos é feita pelo **Django Admin** customizado.

---

## 🛠️ Stack

- **Python 3.10+** — linguagem (compatível com Django 6)
- **Django 6.0** — framework web
- **SQLite** — banco de dados local (padrão)
- **PostgreSQL** — banco persistente para produção no Render, via `DATABASE_URL`
- **Google Calendar API** — integração de eventos
- **WhatsApp Cloud API** — webhook do bot
- **uv** — gerenciador de pacotes
- **Make** — automação de tarefas

---

## 📋 Pré-requisitos

- **Python 3.10+** (o Makefile detecta `python3` automaticamente)
- **Make**
- Opcional para integrações:
  - Arquivo `calendar_credentials.json` na pasta `Backend/proj_integrador/` (service account do Google)
  - Token e webhook do WhatsApp Cloud API

> **Windows**: rode os comandos via **Git Bash** ou **WSL**. O Makefile usa bash e não funciona em `cmd.exe` ou PowerShell puros.

---

## 🚀 Instalação e Configuração

### 1. Clone e prepare o ambiente

```bash
git clone <url-do-repo>
cd Projeto_Integrador_I
make setup            # Cria .venv, instala uv e dependências
```

### 2. Configure o `.env`

O `make setup` já cria o `.env` automaticamente com um `SECRET_KEY` gerado. Se quiser criar/recriar manualmente (ex.: depois de um `make clean`):

```bash
make init-env         # Cria .env com SECRET_KEY forte (não sobrescreve)
```

Depois, edite o `.env` e ajuste o `VERIFY_TOKEN` com o token do seu WhatsApp Cloud API:

```dotenv
SECRET_KEY=<gerado-automaticamente>
DEBUG=True
VERIFY_TOKEN=seu-token-do-whatsapp-webhook
```

O SQLite é usado localmente quando `DATABASE_URL` não está definida. Em produção, basta configurar `DATABASE_URL` com a URL completa de conexão do PostgreSQL. Ela já contém host, porta, nome do banco e credenciais, então não é preciso preencher cada configuração separadamente. Não coloque essa URL nem credenciais no código ou no Git.

### 3. Ative o ambiente e prepare o banco

```bash
make activate         # Abre um shell com o venv ativado
make migrate          # Aplica as migrações
make createsuperuser  # Cria o usuário administrador do painel
```

### 4. Rode o servidor

```bash
make runserver        # http://localhost:8000
```

Acesse o painel em **http://localhost:8000/admin**.

---

## 🧑‍💼 Painel Administrativo

O Django Admin foi customizado para a gestão diária dos agendamentos:

- **Agendamentos**: lista com badge de status colorido, indicador de sincronização com Google Calendar, `date_hierarchy` por data, busca por nome/telefone do cliente, filtros por status e data, e **ações em lote** para *cancelar* ou *marcar como concluídos* vários agendamentos de uma vez.
- **Clientes**: busca por nome, telefone ou email; filtro de clientes deletados.
- **Serviços**: gestão de tipos de trança, preço (em BRL) e duração.
- **Formulário de agendamento**: valida que a data escolhida não esteja no passado (na criação) e usa picker `datetime-local`.

---

## 🤖 Bot do WhatsApp

O fluxo do bot é uma máquina de estados implementada em `WhatsAppBot/engine.py`. Estados cobrem: boas-vindas, cadastro, escolha de data, local de atendimento, confirmação, cancelamento e consulta de agendamentos.

**Webhook**: exposto em `WhatsAppBot/urls.py`. Para desenvolvimento local, use `ngrok` (há um `ngrok.yml` de exemplo) e registre a URL pública no painel do WhatsApp Cloud API.

> ⚠️ **Nota**: o estado das conversas hoje é mantido em memória (`conversations` dict). Reiniciar o servidor descarta as sessões ativas. Persistência em banco está no `docs/ROADMAP.md`.

---

## 🗓️ Integração com Google Calendar

Ao salvar um `Appointment` com `status='scheduled'`, o método `save()` chama `Agendamento.calendar_utils.criar_evento_google_calendar`, que:

1. Usa uma *service account* do Google (arquivo `calendar_credentials.json`).
2. Cria um evento de 2 horas no calendário configurado (`CALENDAR_ID`).
3. Persiste o `google_event_id` no `Appointment`.

Se o arquivo de credenciais estiver ausente, a integração é **pulada com um warning** (o agendamento é gravado no banco normalmente).

**Ao cancelar** um agendamento sincronizado, o evento no Google é atualizado (não deletado): ganha o prefixo `[CANCELADO]` no título, uma anotação `❌ Cancelado em DD/MM/YYYY HH:MM` na descrição e cor vermelha. Isso preserva o histórico do calendário.

---

## 🌎 Timezone

O sistema inteiro — banco, admin, bot do WhatsApp e Google Calendar — usa um **único fuso horário**, definido em `config/settings.py`:

```python
TIME_ZONE = 'America/Sao_Paulo'
```

- O Google Calendar recebe os eventos com `timeZone = settings.TIME_ZONE` (sem hardcode em `calendar_utils.py`), então mudar o fuso da profissional é uma linha só.
- Com `USE_TZ = True`, o banco continua armazenando datetimes em UTC (padrão Django), mas toda a interação no admin, no bot e na exibição do calendário acontece no fuso configurado.
- O horário padrão que o bot sugere (11:00) é interpretado como 11:00 no fuso configurado — não como UTC.

Para trocar de fuso no futuro (ex.: profissional viaja), altere apenas `TIME_ZONE` em `settings.py`. A integração com o Google Calendar segue junto.

---

## ☁️ Persistência no Render com PostgreSQL

O código mantém SQLite para desenvolvimento local e usa PostgreSQL quando `DATABASE_URL` está configurada. Para conectar o Web Service existente:

1. Crie um banco PostgreSQL no Render, de preferência na mesma região do Web Service.
2. No Web Service, adicione `DATABASE_URL` com a **Internal Database URL** fornecida pelo banco. Isso não exige substituir nem recriar o Web Service.
3. Confirme `SECRET_KEY` nas variáveis de ambiente e defina `DEBUG=False`. O Render fornece `RENDER_EXTERNAL_HOSTNAME`; o Django usa esse hostname automaticamente para hosts permitidos e origem CSRF. Se usar um domínio personalizado, adicione-o em `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` como valores separados por vírgula. O proxy HTTPS do Render é reconhecido, o redirecionamento para HTTPS é ativado no Render quando `DEBUG=False` e os cookies de sessão/CSRF são marcados como seguros em produção.
4. Configure o Web Service para instalar dependências e servir a aplicação com Gunicorn. Para um serviço Python com a raiz deste repositório como diretório:

   **Build Command**
   ```bash
   pip install -r requirements.txt && cd Backend/proj_integrador && python manage.py collectstatic --noinput
   ```

   **Start Command**
   ```bash
   cd Backend/proj_integrador && python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
   ```

   O comando de inicialização aplica as migrações no PostgreSQL antes de iniciar a aplicação. Não execute `makemigrations` no deploy: as migrações versionadas no repositório são aplicadas com `migrate`. A migração cria/atualiza o esquema, mas **não transfere registros** de um SQLite anterior; se já houver dados de produção que precisem ser preservados, exporte-os e importe-os para o PostgreSQL antes de trocar o serviço.

Quando `DATABASE_URL` não estiver definida, a aplicação continua usando `Backend/proj_integrador/db.sqlite3`. O Render Web Service não deve depender desse arquivo local para persistência; para produção, conecte o PostgreSQL e confirme nos logs que `migrate` e Gunicorn iniciaram sem erros.

---

## 🧪 Testes

```bash
make test             # Roda a suite completa (21 testes)
make check            # Verifica a configuração do Django
```

---

## 📁 Estrutura

```
Projeto_Integrador_I/
├── Backend/
│   └── proj_integrador/
│       ├── Agendamento/           # models, admin, calendar_utils, managers
│       │   ├── migrations/
│       │   └── tests/
│       ├── Usuario/               # API REST de CRUD de clientes
│       ├── WhatsAppBot/           # engine (state machine), webhook, helper
│       │   └── bot/
│       ├── config/                # settings.py, urls.py
│       └── manage.py
├── Makefile                       # Automação dos comandos do projeto
├── Taskfile.yml                   # Alternativa ao Make (Task runner)
├── docker-compose.yml             # Execução em container
├── requirements.txt               # Dependências Python
├── docs/
│   └── ROADMAP.md                 # Melhorias priorizadas e dívidas técnicas
└── ngrok.yml                      # Config de túnel para dev do webhook
```

---

## 📋 Comandos principais

| Comando | Descrição |
|---|---|
| `make setup` | Cria `.venv`, instala dependências e gera o `.env` |
| `make init-env` | Cria `.env` com `SECRET_KEY` gerado (não sobrescreve) |
| `make activate` | Abre um shell com o venv ativado |
| `make migrate` | Aplica migrações no banco |
| `make makemigrations` | Gera novas migrações a partir das mudanças nos models |
| `make runserver` | Sobe o servidor em `http://localhost:8000` |
| `make createsuperuser` | Cria conta de admin |
| `make test` | Roda os testes |
| `make check` | Verifica a configuração do Django |
| `make update-requirements` | Atualiza `requirements.txt` |
| `make clean` | Remove o `.venv` e caches |
| `make help` | Lista todos os comandos |

---

## 💡 Dicas

- **Erro "SECRET_KEY must not be empty"**: rode `make init-env` para gerar um `.env` com chave válida.
- **Integração Google falhando silenciosamente**: confirme que `calendar_credentials.json` está em `Backend/proj_integrador/` e que a service account tem acesso ao calendário definido em `calendar_utils.CALENDAR_ID`. Sem o arquivo, a sincronização é apenas ignorada (o agendamento é salvo normalmente).
- **Testes falhando com `ImproperlyConfigured: SECRET_KEY`**: o `.env` não foi criado. Rode `make init-env` antes de `make test`.
- **Webhook do WhatsApp não recebe mensagens em dev**: o ngrok precisa estar rodando e a URL pública registrada no painel do WhatsApp Cloud API.
- **Para limpar tudo e recomeçar**: `make clean && make setup`.

---

## 🗺️ Próximos passos

Veja [docs/ROADMAP.md](./docs/ROADMAP.md) para a lista priorizada de melhorias — incluindo persistência de estado do bot em banco, validação HMAC do webhook do WhatsApp e settings por ambiente (dev/prod).
