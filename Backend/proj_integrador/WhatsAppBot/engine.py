from botCore.interfaces import IMessageSender
from botCore.state_machine import processar_mensagem
from WhatsAppBot.sender import WhatsAppSender


def processar_mensagem_whatsapp(mensagem_do_usuario: str, bot_telefone: str, usuario_telefone: str, nome_usuario: str) -> None:
    sender: IMessageSender = WhatsAppSender(bot_telefone)
    processar_mensagem(mensagem_do_usuario, usuario_telefone, nome_usuario, sender)
