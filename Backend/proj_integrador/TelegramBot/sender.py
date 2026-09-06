from botCore.send_message import enviar_mensagem_via_telegram


class TelegramSender:
    """
    Diferente do WhatsApp (onde cada mensagem recebida traz o
    phone_number_id do número que deve responder, pois uma mesma conta
    Business pode ter vários números), o Telegram usa um único bot/token
    fixo, configurado em TELEGRAM_BOT_TOKEN. Por isso não recebe nenhum
    identificador de "bot" no construtor — só precisa do chat_id do
    destinatário na hora de enviar.
    """

    def enviar(self, destinatario: str | int, mensagem: str) -> None:
        enviar_mensagem_via_telegram(destinatario, mensagem)