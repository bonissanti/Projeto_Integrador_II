"""
Armazenamento de estado de conversa, compartilhado entre todos os canais
(WhatsApp, Telegram, etc). Cada conversa é identificada por um `user_id`
genérico (string) — o número de telefone no caso do WhatsApp, ou o
`chat_id` (convertido para string) no caso do Telegram.

Mantido em memória por enquanto (dict). Se o processo reiniciar ou rodar
com mais de um worker, o estado se perde / diverge — ok para desenvolvimento,
mas vale migrar para algo persistente (cache/Redis ou tabela no banco)
antes de ir para produção com mais de um worker.
"""

from botCore.bot_enums import Status
from botCore.helper import Conversation

conversations: dict[str, Conversation] = {}


def get_conversation(user_id: str) -> Conversation:
    if user_id not in conversations:
        conversations[user_id] = Conversation()
    return conversations[user_id]


def set_state(user_id: str, new_state: Status) -> None:
    conv = get_conversation(user_id)
    conv.state = new_state


def reset_conversation(user_id: str) -> None:
    conversations.pop(user_id, None)
