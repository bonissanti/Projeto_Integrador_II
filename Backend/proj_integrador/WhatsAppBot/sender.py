from botCore.send_message import enviar_mensagem_via_whats


class WhatsAppSender:
    def __init__(self, bot_telefone: str):
        self.bot_telefone = bot_telefone

    def enviar(self, destinatario: str, mensagem: str) -> None:
        enviar_mensagem_via_whats(destinatario, mensagem, self.bot_telefone)