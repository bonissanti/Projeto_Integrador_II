from datetime import datetime, timedelta, time

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db import models, transaction
from decimal import Decimal
from django.core.exceptions import ValidationError


class CustomerManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted=False)

    def checar_se_usuario_existe_por_telefone(self, numero_telefone: str) -> bool:
        return self.filter(phone=numero_telefone).exists()

    def cadastrar_usuario(self, nome: str, email: str, numero_telefone: str, senha: str) -> 'Customer':
        return self.create(name=nome, email=email, phone=numero_telefone, senha=make_password(senha))

    def editar_usuario(self, numero_telefone_atual: str, nome: str | None, email: str | None,
                       novo_numero_telefone: str | None, senha: str | None) -> int:
        updates = {}
        if nome is not None:
            updates['name'] = nome
        if email is not None:
            updates['email'] = email
        if novo_numero_telefone is not None:
            updates['phone'] = novo_numero_telefone
        if senha is not None:
            updates['senha'] = make_password(senha)

        if not updates:
            return 0

        return self.filter(phone=numero_telefone_atual).update(**updates)

    def deletar_usuario(self, numero_telefone: str) -> int:
        linhas_alteradas = self.filter(phone=numero_telefone).update(deleted=True)
        return linhas_alteradas > 0

    def buscar_usuario_por_telefone(self, numero_telefone: str) -> 'Customer | None':
        return self.filter(phone=numero_telefone).first()

    def buscar_usuario_por_email(self, email: str) -> 'Customer | None':
        return self.filter(email=email).first()

    def buscar_usuarios_nao_deletados(self) -> list['Customer']:
        return list(self.filter(deleted=False))

    def verificar_senha(self, numero_telefone: str, senha: str):
        usuario = self.buscar_usuario_por_telefone(numero_telefone)

        if usuario:
            return usuario.check_password(senha)
        return False

    def buscar_usuario_por_id(self, id: int) -> 'Customer | None':
        return self.filter(id=id).first()


class AppointmentsManager(models.Manager):
    HORARIO_PADRAO = time(11, 0)

    def buscar_agendamentos_disponiveis_no_periodo(self, total_dias: int = 20) -> list:
        hoje = timezone.now().date()

        if timezone.now().hour >= 10:
            data_inicio = hoje + timedelta(days=1)
        else:
            data_inicio = hoje

        data_final = data_inicio + timedelta(days=total_dias)

        dias_ocupados = set(
            self.filter(
                scheduled_at__date__range=[data_inicio, data_final],
                status='scheduled',
            ).values_list('scheduled_at__date', flat=True)
        )

        possiveis_dias = [data_inicio + timedelta(days=i) for i in range(total_dias)]
        return [dia for dia in possiveis_dias if dia not in dias_ocupados]

    def buscar_agendamentos_por_numero_telefone(self, numero_telefone: str) -> list['Appointment']:
        query = self.filter(customer__phone=numero_telefone, status='scheduled')
        return list(query)

    def marcar_agendamento(self, customer: 'Customer', scheduled_at: datetime, location: str,
                           services: list['Service']) -> 'Appointment':
        from .models import AppointmentxService, HairStock

        if timezone.is_naive(scheduled_at):
            scheduled_at = timezone.make_aware(scheduled_at, timezone.get_current_timezone())

        appointment = self.create(
            customer=customer,
            scheduled_at=scheduled_at,
            status='scheduled',
            location=location,
        )

        for service in services:
            AppointmentxService.objects.create(
                appointment=appointment,
                service=service,
                applied_price=service.price,
            )

            for consumo in service.hair_stock_usages.all():
                try:
                    HairStock.objects.registrar_saida(
                        consumo.hair_stock_id,
                        consumo.quantity,
                        appointment=appointment,
                        note=f'Consumo automático do agendamento #{appointment.id} ({service.name})',
                    )
                except ValidationError as e:
                    print(f'Erro ao debitar estoque de cabelo para "{service.name}": {e}')

        return appointment

    def cancelar_agendamento(self, appointment: 'Appointment') -> 'Appointment':
        appointment.status = 'canceled'
        appointment.save(update_fields=['status'])
        return appointment

    def checar_se_data_esta_em_uso(self, data) -> bool:
        return self.filter(scheduled_at__date=data, status='scheduled').exists()

class ServiceManager(models.Manager):
    def registrar_servicos(self, servicos: list[str]):
        for servico in servicos:
            self.get_or_create(
                name=servico["name"],
                defaults={
                    "description": servico["description"],
                    "price": servico["price"],
                    "duration": servico["duration"],
                }
            )

    def listar_servicos(self) -> list['Service']:
        return list(self.values_list('name', 'price'))

    def listar_servicos_por_nome(self) -> list['Service']:
        return list(self.values_list('name', flat=True))

    def buscar_numero_de_servicos_oferecidos(self) -> int:
        return self.count()

    def buscar_servico_por_id(self, id: int) -> 'Service | None':
        return self.filter(id=id).first()


class HairStockManager(models.Manager):

    def listar_ativos(self):
        return self.filter(deleted=False)

    @transaction.atomic
    def registrar_entrada(self, hair_stock_id, quantity, unit_price=None, note=''):
        """
        Repõe estoque. Se unit_price for informado, também atualiza o
        preço de referência do HairStock (preço pode mudar entre compras).
        """
        from .models import HairMovement  # import local evita ciclo com models.py

        quantity = Decimal(str(quantity))
        if quantity <= 0:
            raise ValidationError('Quantidade de entrada deve ser positiva.')

        hair_stock = self.select_for_update().get(id=hair_stock_id, deleted=False)
        preco_usado = unit_price if unit_price is not None else hair_stock.unit_price

        HairMovement.objects.create(
            hair_stock=hair_stock,
            movement_type='entrada',
            quantity=quantity,
            unit_price_at_time=preco_usado,
            note=note,
        )

        hair_stock.quantity_on_hand += quantity
        if unit_price is not None:
            hair_stock.unit_price = unit_price
        hair_stock.save(update_fields=['quantity_on_hand', 'unit_price'])

        return hair_stock

    @transaction.atomic
    def registrar_saida(self, hair_stock_id, quantity, appointment=None, note=''):
        """
        Consome estoque. Levanta ValidationError se não houver saldo
        suficiente — não permite estoque negativo.
        """
        from .models import HairMovement  # import local evita ciclo com models.py

        quantity = Decimal(str(quantity))
        if quantity <= 0:
            raise ValidationError('Quantidade de saída deve ser positiva.')

        hair_stock = self.select_for_update().get(id=hair_stock_id, deleted=False)

        if hair_stock.quantity_on_hand < quantity:
            raise ValidationError(
                f'Estoque insuficiente de "{hair_stock.name}": '
                f'disponível {hair_stock.quantity_on_hand}, solicitado {quantity}.'
            )

        HairMovement.objects.create(
            hair_stock=hair_stock,
            movement_type='saida',
            quantity=quantity,
            unit_price_at_time=hair_stock.unit_price,
            appointment=appointment,
            note=note,
        )

        hair_stock.quantity_on_hand -= quantity
        hair_stock.save(update_fields=['quantity_on_hand'])

        if hair_stock.is_low_stock:
            from .notifications import notificar_estoque_baixo
            transaction.on_commit(lambda: notificar_estoque_baixo(hair_stock))

        return hair_stock

    def baixo_estoque(self):
        return self.filter(deleted=False, quantity_on_hand__lte=models.F('minimum_stock'))
