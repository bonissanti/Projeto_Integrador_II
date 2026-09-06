from botCore.interfaces import IMessageSender
from botCore.state_machine import processar_mensagem
from TelegramBot.sender import TelegramSender


def processar_mensagem_telegram(mensagem_do_usuario: str, chat_id: str, nome_usuario: str) -> None:
    sender: IMessageSender = TelegramSender()
    processar_mensagem(mensagem_do_usuario, chat_id, nome_usuario, sender)
