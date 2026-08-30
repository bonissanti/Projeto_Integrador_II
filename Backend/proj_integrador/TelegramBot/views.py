from django.views.decorators.csrf import csrf_exempt


def healthcheck():
    return JsonResponse({"status": "OK"})

@csrf_exempt
def webhook(request):
    if request.method == 'POST':
        payload = request.body.decode('utf-8')

        if "message" in payload:
            chat_id = str(payload["message"]["chat"]["id"])
            user_text = payload["message"].get("text", "")
            first_name = payload["message"]["chat"].get("first_name", "")

            proce