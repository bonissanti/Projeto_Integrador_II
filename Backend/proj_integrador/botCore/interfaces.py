from typing import Protocol

class IMessageSender(Protocol):
    def enviar(self, destinatario: str, mensagem: str) -> None:
        ...