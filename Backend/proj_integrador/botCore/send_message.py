import os
import requests

ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

def enviar_mensagem_via_whats(usuario_telefone: str, mensagemDoBot: str, bot_telefone: str):
    url = f"https://graph.facebook.com/v22.0/{bot_telefone}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": usuario_telefone,
        "text": {"body": mensagemDoBot}
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        print("Mensagem enviada com sucesso!")
    else:
        print(f"Erro ao enviar mensagem para {usuario_telefone}. Resposta do servidor: {response.text} ({response.status_code})")

def enviar_mensagem_via_telegram(chat_id: str | int, mensagemDoBot: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": mensagemDoBot
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        print(f"Mensagem enviada com sucesso no Telegram para {chat_id}!")
    else:
        print(f"Erro: {response.text} ({response.status_code})")
