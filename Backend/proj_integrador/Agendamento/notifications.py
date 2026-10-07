"""
Notificações administrativas relacionadas ao estoque de cabelo. Isolado
num módulo próprio pra evitar que Agendamento/managers.py dependa
diretamente dos detalhes de transporte (Telegram, e-mail, etc).
"""
from django.conf import settings


def notificar_estoque_baixo(hair_stock: 'HairStock') -> None:
    """
    Avisa a Tati (via Telegram) quando um item de estoque de cabelo fica
    igual ou abaixo do nível mínimo configurado.
    """
    chat_id = getattr(settings, 'TELEGRAM_ADMIN_CHAT_ID', None)
    if not chat_id:
        return

    try:
        from botCore.send_message import enviar_mensagem_via_telegram

        mensagem = (
            f"⚠️ Estoque baixo: {hair_stock.name}\n"
            f"Disponível: {hair_stock.quantity_on_hand} {hair_stock.unit}\n"
            f"Mínimo: {hair_stock.minimum_stock} {hair_stock.unit}"
        )
        enviar_mensagem_via_telegram(chat_id, mensagem)
    except Exception as e:
        print(f'Erro ao notificar estoque baixo de "{hair_stock.name}": {e}')
