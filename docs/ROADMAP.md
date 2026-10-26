 Roadmap — Projeto Integrador I

Lista de achados, melhorias priorizadas e próximos passos identificados durante a revisão do backend em `Backend/proj_integrador/` (2026-04-20).

## 🔴 Bug crítico confirmado

**`Agendamento/models.py:64`** — `save()` só cria evento no Google Calendar quando `status == 'confirmado'`, mas `STATUS_CHOICES` usa `'scheduled' | 'completed' | 'canceled'`. **Nenhum agendamento está sendo sincronizado com o Google Calendar.** Fix: trocar `'confirmado'` por `'scheduled'`.

## 🔴 Outros problemas críticos

| # | Arquivo | Problema |
|---|---------|----------|
| 1 | `config/settings.py:39-48` | App `Usuario` não está em `INSTALLED_APPS` — models/migrações não rodam |
| 2 | `WhatsAppBot/helper.py:68` | `conversations = {}` em memória global — estado do bot se perde ao reiniciar |
| 3 | `config/settings.py` | ~~`DEBUG = True` hardcoded~~ → ✅ resolvido: `DEBUG` vem do ambiente e usa `False` como padrão. |
| 4 | `config/settings.py` | Host do ngrok mantido para dev; hosts do Render e domínios personalizados são configuráveis pelo ambiente. |
| 5 | ~~`config/settings.py:115`~~ | ~~`TIME_ZONE = 'UTC'` mas calendário usa `America/Sao_Paulo`~~ → ✅ resolvido: `TIME_ZONE='America/Sao_Paulo'` e `calendar_utils.py` lê de `settings.TIME_ZONE` (fonte única). |
| 6 | `Agendamento/calendar_utils.py` | Credenciais do Google em arquivo local + erros só em `print()` |
| 7 | `WhatsAppBot/views.py` | Webhook com `@csrf_exempt` sem validar assinatura HMAC |

## 🟡 Importantes (design)

- Validações em `Usuario/validacoes.py` são fracas (`"@" in email`) — usar `django.core.validators` + lib `phonenumbers`
- Acoplamento forte `WhatsAppBot.engine` ↔ models — criar `Agendamento/services.py`
- Lógica do Google Calendar dentro de `Model.save()` → usar signals ou service layer (evita double-save e race condition)
- ~~Exclusão no Google quando status vira `'canceled'`~~ → resolvido: evento agora é **marcado** como cancelado (prefixo `[CANCELADO]` no título, anotação na descrição com data/hora, cor vermelha). Preserva histórico.
- Substituir `print()` por `logging` estruturado

## 🟢 Nice-to-have

- Revisar se `.github/workflows/django.yaml` roda testes/lint de fato
- DTOs em `bot/dtos.py` sem validação (`__post_init__`)
- Sem paginação em listagens
- SQLite segue como padrão local; PostgreSQL via `DATABASE_URL` está configurado para produção, faltando criar/conectar o banco no Render e validar o deploy real

## 🚀 Incrementos (ordem recomendada)

1. **Fix rápido**: `'confirmado'` → `'scheduled'` + adicionar `'Usuario'` em `INSTALLED_APPS`
2. **Persistir estado do bot**: model `WhatsAppConversation(phone, state, data_json, updated_at)` substituindo o dict global
3. **Service layer**: mover lógica do Google Calendar de `Model.save()` para `AgendamentoService` + signals, com retry e logging
4. **Segurança do webhook**: validar `X-Hub-Signature-256` via HMAC + rate-limit por telefone
5. **Settings por ambiente**: `DEBUG` e hosts agora são configuráveis via ambiente; ainda parametrizar `TIME_ZONE` e validar `SECRET_KEY`
6. **Validação robusta**: refatorar `validacoes.py` usando `EmailValidator` + `phonenumbers`
7. ~~**Cancelamento no Google Calendar**~~ → ✅ implementado: ao cancelar, o evento é marcado com prefixo `[CANCELADO]`, anotação de data/hora na descrição e cor vermelha.
8. **Testes de integração reais**: fluxo `webhook → BD → Calendar` (atuais só mockam)
