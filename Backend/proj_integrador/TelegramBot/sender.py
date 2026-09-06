from botCore.send_message import enviar_mensagem_via_telegram

class TelegramSender:
    def __init__(self, bot_telefone: str):
        self.bot_telefone = bot_telefone

    def enviar(self, destinatario: str, mensagem: str) -> None:
        enviar_mensagem_via_telegram(destinatario, mensagem)