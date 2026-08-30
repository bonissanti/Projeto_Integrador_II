from botCore.send_message import enviar_mensagem_via_telegram

class TelegramSender:
    def enviar(self, destinatario: str, mensagem: str) -> None:
        enviar_mensagem_via_telegram(destinatario, mensagem)