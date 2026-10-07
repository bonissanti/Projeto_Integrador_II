from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from Agendamento.models import (
    Appointment,
    Customer,
    HairMovement,
    HairStock,
    Service,
    ServiceHairStock,
)


class EstoqueDeCabeloTest(TestCase):
    """
    Verifica se Agendamento_hairstock, Agendamento_hairmovement e
    Agendamento_servicehairstock são populadas/atualizadas como esperado
    quando um agendamento é criado via marcar_agendamento (fluxo
    compartilhado pelo site e pelo bot do Telegram/WhatsApp).
    """

    def setUp(self):
        self.cliente = Customer.objects.create(
            name="Cliente de Teste",
            email="teste.estoque@example.com",
            phone="11999998888",
        )
        self.servico = Service.objects.create(
            name="Tranças Soltas",
            description="Serviço de teste",
            price=Decimal('150.00'),
            duration=120,
        )
        self.cabelo = HairStock.objects.create(
            name="Larilou",
            unit='g',
            unit_price=Decimal('2.50'),
            quantity_on_hand=Decimal('10'),
            minimum_stock=Decimal('5'),
        )

    def _futuro(self, hora=14):
        base = datetime.now() + timedelta(days=2)
        return timezone.make_aware(base.replace(hour=hora, minute=0, second=0, microsecond=0))

    def test_service_hair_stock_e_criado_e_vinculado_corretamente(self):
        consumo = ServiceHairStock.objects.create(
            service=self.servico,
            hair_stock=self.cabelo,
            quantity=Decimal('6'),
        )

        self.assertEqual(ServiceHairStock.objects.count(), 1)
        self.assertEqual(self.servico.hair_stock_usages.count(), 1)
        self.assertEqual(self.servico.hair_stock_usages.first(), consumo)
        self.assertEqual(consumo.hair_stock, self.cabelo)

    @patch('Agendamento.calendar_utils.criar_evento_google_calendar', return_value=None)
    def test_agendamento_debita_hair_stock_e_gera_hair_movement(self, _mock_google):
        ServiceHairStock.objects.create(
            service=self.servico,
            hair_stock=self.cabelo,
            quantity=Decimal('6'),
        )

        agendamento = Appointment.objects.marcar_agendamento(
            customer=self.cliente,
            scheduled_at=self._futuro(),
            location='Rua de Teste, 123',
            services=[self.servico],
        )

        self.cabelo.refresh_from_db()
        self.assertEqual(self.cabelo.quantity_on_hand, Decimal('4'))

        movimentos = HairMovement.objects.filter(hair_stock=self.cabelo)
        self.assertEqual(movimentos.count(), 1)

        movimento = movimentos.first()
        self.assertEqual(movimento.movement_type, 'saida')
        self.assertEqual(movimento.quantity, Decimal('6'))
        self.assertEqual(movimento.appointment, agendamento)
        self.assertEqual(movimento.unit_price_at_time, self.cabelo.unit_price)

    @patch('Agendamento.calendar_utils.criar_evento_google_calendar', return_value=None)
    def test_agendamento_sem_service_hair_stock_nao_debita_nada(self, _mock_google):
        Appointment.objects.marcar_agendamento(
            customer=self.cliente,
            scheduled_at=self._futuro(),
            location='Rua de Teste, 123',
            services=[self.servico],
        )

        self.cabelo.refresh_from_db()
        self.assertEqual(self.cabelo.quantity_on_hand, Decimal('10'))
        self.assertEqual(HairMovement.objects.count(), 0)

    @patch('Agendamento.calendar_utils.criar_evento_google_calendar', return_value=None)
    def test_agendamento_com_estoque_insuficiente_nao_derruba_criacao(self, _mock_google):
        ServiceHairStock.objects.create(
            service=self.servico,
            hair_stock=self.cabelo,
            quantity=Decimal('999'),
        )

        agendamento = Appointment.objects.marcar_agendamento(
            customer=self.cliente,
            scheduled_at=self._futuro(),
            location='Rua de Teste, 123',
            services=[self.servico],
        )

        self.assertIsNotNone(agendamento.id)
        self.cabelo.refresh_from_db()
        self.assertEqual(self.cabelo.quantity_on_hand, Decimal('10'))
        self.assertEqual(HairMovement.objects.count(), 0)

    @patch('Agendamento.notifications.notificar_estoque_baixo')
    @patch('Agendamento.calendar_utils.criar_evento_google_calendar', return_value=None)
    def test_agendamento_que_deixa_estoque_baixo_dispara_notificacao(self, _mock_google, mock_notificar):
        ServiceHairStock.objects.create(
            service=self.servico,
            hair_stock=self.cabelo,
            quantity=Decimal('6'),
        )

        with self.captureOnCommitCallbacks(execute=True):
            Appointment.objects.marcar_agendamento(
                customer=self.cliente,
                scheduled_at=self._futuro(),
                location='Rua de Teste, 123',
                services=[self.servico],
            )

        self.cabelo.refresh_from_db()
        self.assertTrue(self.cabelo.is_low_stock)
        mock_notificar.assert_called_once_with(self.cabelo)

    @patch('Agendamento.calendar_utils.criar_evento_google_calendar', return_value=None)
    def test_agendamento_sem_estoque_baixo_nao_dispara_notificacao(self, _mock_google):
        self.cabelo.quantity_on_hand = Decimal('100')
        self.cabelo.save(update_fields=['quantity_on_hand'])

        ServiceHairStock.objects.create(
            service=self.servico,
            hair_stock=self.cabelo,
            quantity=Decimal('6'),
        )

        with patch('Agendamento.notifications.notificar_estoque_baixo') as mock_notificar:
            with self.captureOnCommitCallbacks(execute=True):
                Appointment.objects.marcar_agendamento(
                    customer=self.cliente,
                    scheduled_at=self._futuro(),
                    location='Rua de Teste, 123',
                    services=[self.servico],
                )

        self.cabelo.refresh_from_db()
        self.assertFalse(self.cabelo.is_low_stock)
        mock_notificar.assert_not_called()

    def test_registrar_entrada_gera_hair_movement_de_entrada(self):
        HairStock.objects.registrar_entrada(
            self.cabelo.id,
            Decimal('20'),
            note='Reposição de teste',
        )

        self.cabelo.refresh_from_db()
        self.assertEqual(self.cabelo.quantity_on_hand, Decimal('30'))

        movimento = HairMovement.objects.filter(hair_stock=self.cabelo).latest('id')
        self.assertEqual(movimento.movement_type, 'entrada')
        self.assertEqual(movimento.quantity, Decimal('20'))
        self.assertIsNone(movimento.appointment)
