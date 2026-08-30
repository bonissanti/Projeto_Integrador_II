import json

from django.conf import settings
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .engine import processar_mensagem_whatsapp


def healthcheck():
    return JsonResponse({"status": "OK"})

@csrf_exempt
def webhook(request):
    if request.method == 'GET':
        hub_mode = request.GET.get('hub.mode')
        hub_verify_token = request.GET.get('hub.verify_token')
        hub_challenge = request.GET.get('hub.challenge')

        if hub_mode and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(hub_challenge, status=200)
        return HttpResponseForbidden("Token inválido", status=403)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("Webhook recebido:", data)

            for entry in data.get('entry', []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})

                    if "statuses" in value:
                        continue

                    bot_telefone = value.get("metadata", {}).get("phone_number_id")

                    contacts = value.get("contacts", [])
                    usuario_telefone = contacts[0].get("wa_id") if contacts else None
                    nome_usuario = contacts[0].get("profile", {}).get("name") if contacts else None

                    message_data = value.get("messages", [{}])
                    for message in message_data:
                        message_text = message.get("text", {}).get("body", "")
                        processar_mensagem_whatsapp(message_text, bot_telefone, usuario_telefone, nome_usuario)

            return JsonResponse({"status": "EVENT_RECEIVED"}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"status": "Invalid JSON"}, status=400)

    return JsonResponse({"status": "Method not allowed"}, status=405)