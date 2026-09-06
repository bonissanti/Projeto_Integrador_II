import json

from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .engine import processar_mensagem_telegram


def healthcheck(request):
    return JsonResponse({"status": "OK"})


@csrf_exempt
def webhook(request):
    if request.method != 'POST':
        return JsonResponse({"status": "Method not allowed"}, status=405)

    if settings.TELEGRAM_WEBHOOK_SECRET:
        header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header_secret != settings.TELEGRAM_WEBHOOK_SECRET:
            return HttpResponseForbidden("Token inválido")

    try:
        update = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "Invalid JSON"}, status=400)

    print("Webhook recebido:", update)

    message = update.get("message")

    if message:
        chat_id = str(message["chat"]["id"])
        user_text = message.get("text", "")
        nome_usuario = message["chat"].get("first_name", "")

        processar_mensagem_telegram(user_text, chat_id, nome_usuario)

    # Update sem "message" (ex: edited_message, callback_query, etc) —
    # por enquanto ignoramos, mas ainda respondemos 200 pro Telegram não
    # ficar reenviando o mesmo update.
    return JsonResponse({"status": "EVENT_RECEIVED"}, status=200)
