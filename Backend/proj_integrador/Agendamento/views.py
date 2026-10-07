import json
from datetime import datetime

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from Agendamento.models import Appointment, Service, Customer, HairStock, HairMovement


# Create your views here.
def get_request_data(request):
    if request.method == 'POST':
        return request.POST
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        print("Erro ao decodificar JSON")
        return None


@csrf_exempt
def agendamento(request):
    if request.method == 'POST':
        return criar_agendamento(request)
    return None


def criar_agendamento(request):
    data = json.loads(request.body)

    customer_id = data['customer_id']
    scheduled_at_str = data['scheduled_at']
    location = data['location']
    service_name = data['service_name']

    if not all([customer_id, scheduled_at_str, location, service_name]):
        return JsonResponse({'error': 'Dados incompletos'}, status=400)

    scheduled_at = datetime.fromisoformat(scheduled_at_str)
    customer = Customer.objects.buscar_usuario_por_id(customer_id)
    service = Service.objects.filter(name=service_name).first()

    if customer is None:
        return JsonResponse({'error': 'Cliente não encontrado'}, status=404)
    if service is None:
        return JsonResponse({'error': 'Serviço não encontrado'}, status=404)

    Appointment.objects.marcar_agendamento(customer, scheduled_at, location, [service])
    return JsonResponse({'message': 'Agendamento criado com sucesso!'}, status=200)

def excluir_agendamento(request):
    pass


@csrf_exempt
def estoque_cabelo(request):
    """
    GET  /estoque/           -> lista todos os tipos de cabelo ativos
    POST /estoque/           -> cria um novo tipo de cabelo (cadastro no catálogo)
    """
    if request.method == 'GET':
        return listar_estoque(request)
    if request.method == 'POST':
        return criar_hair_stock(request)
    return JsonResponse({'error': 'Método não permitido'}, status=405)


def listar_estoque(request):
    itens = HairStock.objects.listar_ativos()
    data = [{
        'id': item.id,
        'name': item.name,
        'unit': item.unit,
        'unit_price': str(item.unit_price),
        'quantity_on_hand': str(item.quantity_on_hand),
        'minimum_stock': str(item.minimum_stock),
        'is_low_stock': item.is_low_stock,
    } for item in itens]
    return JsonResponse(data, safe=False, status=200)


def criar_hair_stock(request):
    data = get_request_data(request)
    if data is None:
        return JsonResponse({'error': 'Dados inválidos'}, status=400)

    name = data.get('name')
    unit_price = data.get('unit_price')
    unit = data.get('unit', 'un')
    minimum_stock = data.get('minimum_stock', 0)
    initial_quantity = data.get('quantity_on_hand', 0)

    if not name or unit_price is None:
        return JsonResponse({'error': 'Nome e preço unitário são obrigatórios'}, status=400)

    hair_stock = HairStock.objects.create(
        name=name,
        unit=unit,
        unit_price=unit_price,
        minimum_stock=minimum_stock,
        quantity_on_hand=0,
    )

    # Se veio quantidade inicial, registra como primeira entrada (mantém histórico coerente)
    if float(initial_quantity) > 0:
        HairStock.objects.registrar_entrada(
            hair_stock.id, initial_quantity, unit_price=unit_price, note='Estoque inicial'
        )
        hair_stock.refresh_from_db()

    return JsonResponse({'id': hair_stock.id, 'message': 'Cabelo cadastrado com sucesso!'}, status=201)


@csrf_exempt
def editar_ou_remover_hair_stock(request, hair_stock_id):
    """
    PUT/PATCH /estoque/<id>/  -> edita nome/preço/estoque mínimo (não quantity_on_hand diretamente)
    DELETE    /estoque/<id>/  -> soft delete
    """
    try:
        hair_stock = HairStock.objects.get(id=hair_stock_id, deleted=False)
    except HairStock.DoesNotExist:
        return JsonResponse({'error': 'Item de estoque não encontrado'}, status=404)

    if request.method in ('PUT', 'PATCH'):
        data = get_request_data(request)
        if data is None:
            return JsonResponse({'error': 'Dados inválidos'}, status=400)

        if 'name' in data:
            hair_stock.name = data['name']
        if 'unit' in data:
            hair_stock.unit = data['unit']
        if 'unit_price' in data:
            hair_stock.unit_price = data['unit_price']
        if 'minimum_stock' in data:
            hair_stock.minimum_stock = data['minimum_stock']
        # quantity_on_hand é intencionalmente ignorado aqui — só muda via
        # registrar_entrada/registrar_saida, para preservar o histórico.
        hair_stock.save()
        return JsonResponse({'message': 'Item atualizado com sucesso!'}, status=200)

    if request.method == 'DELETE':
        hair_stock.deleted = True
        hair_stock.save(update_fields=['deleted'])
        return JsonResponse({'message': 'Item removido com sucesso!'}, status=200)

    return JsonResponse({'error': 'Método não permitido'}, status=405)


@csrf_exempt
def movimentar_estoque(request, hair_stock_id):
    """
    POST /estoque/<id>/movimentar/
    body: { "movement_type": "entrada" | "saida", "quantity": 10, "note": "...", "appointment_id": opcional }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    data = get_request_data(request)
    if data is None:
        return JsonResponse({'error': 'Dados inválidos'}, status=400)

    movement_type = data.get('movement_type')
    quantity = data.get('quantity')
    note = data.get('note', '')
    appointment_id = data.get('appointment_id')

    if movement_type not in ('entrada', 'saida') or quantity is None:
        return JsonResponse({'error': 'movement_type e quantity são obrigatórios'}, status=400)

    try:
        if movement_type == 'entrada':
            unit_price = data.get('unit_price')
            hair_stock = HairStock.objects.registrar_entrada(
                hair_stock_id, quantity, unit_price=unit_price, note=note
            )
        else:
            appointment = None
            if appointment_id:
                appointment = Appointment.objects.filter(id=appointment_id).first()
            hair_stock = HairStock.objects.registrar_saida(
                hair_stock_id, quantity, appointment=appointment, note=note
            )
    except HairStock.DoesNotExist:
        return JsonResponse({'error': 'Item de estoque não encontrado'}, status=404)
    except ValidationError as e:
        return JsonResponse({'error': str(e.message) if hasattr(e, 'message') else str(e)}, status=400)

    return JsonResponse({
        'message': 'Movimentação registrada com sucesso!',
        'quantity_on_hand': str(hair_stock.quantity_on_hand),
    }, status=200)


def historico_movimentacoes(request, hair_stock_id):
    """GET /estoque/<id>/historico/ -> lista todas as movimentações desse item"""
    movimentos = HairMovement.objects.filter(hair_stock_id=hair_stock_id)
    data = [{
        'id': m.id,
        'movement_type': m.movement_type,
        'quantity': str(m.quantity),
        'unit_price_at_time': str(m.unit_price_at_time),
        'appointment_id': m.appointment_id,
        'note': m.note,
        'created_at': m.created_at.isoformat(),
    } for m in movimentos]
    return JsonResponse(data, safe=False, status=200)