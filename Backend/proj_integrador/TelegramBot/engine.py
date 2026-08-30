from engine import get_conversation


def processar_mensagem_telegram(mensagem: str, chat_id: str, nome_usuario: str):
    conv = get_conversation()