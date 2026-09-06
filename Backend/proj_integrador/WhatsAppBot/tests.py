import uuid
from unittest.mock import patch, MagicMock
from datetime import date, datetime, timedelta, time as dt_time

from django.test import TestCase
from django.utils import timezone

from Agendamento.models import Customer, Appointment, Service
from WhatsAppBot.engine import processar_mensagem_whatsapp
from botCore.conversation_store import get_conversation, conversations
from botCore.bot_enums import Status
from botCore.helper import MensagemBOT

MOCK_DATAS_DISPONIVEIS = [date.today() + timedelta(days=i) for i in range(1, 6)]

# Ponto real de saída pro mundo externo: a chamada HTTP pro Graph API do
# WhatsApp. É aqui (e só aqui) que precisamos mockar pra não bater na rede
# de verdade durante os testes — tudo entre o webhook e esse ponto é
# código nosso e roda de verdade no teste.
PATCH_ENVIAR = 'WhatsAppBot.sender.enviar_mensagem_via_whats'

PATCH_BUSCAR_DATAS = 'Agendamento.managers.AppointmentsManager.buscar_agendamentos_disponiveis_no_periodo'
PATCH_CHECAR_USUARIO = 'Agendamento.managers.CustomerManager.checar_se_usuario_existe_por_telefone'
PATCH_BUSCAR_AGENDAMENTOS = 'Agendamento.managers.AppointmentsManager.buscar_agendamentos_por_numero_telefone'
PATCH_CHECAR_DATA_EM_USO = 'Agendamento.managers.AppointmentsManager.checar_se_data_esta_em_uso'


class StateMachineIntegrationTest(TestCase):
    """
    Testes de integração da máquina de estados do bot (compartilhada em
    botCore.state_machine) através da entrada do WhatsApp
    (processar_mensagem_whatsapp). Cobrem os principais fluxos de
    conversa: autenticação, agendamento, cancelamento, consulta e
    tratamento de opções inválidas.

    Só a chamada HTTP real (enviar_mensagem_via_whats) é mockada — o
    resto (máquina de estados, banco de dados via Customer/Appointment/
    Service, conversation_store) roda de verdade a cada teste.
    """

    def setUp(self):
        conversations.clear()
        self.usuario_telefone = "+5511999999999"
        self.nome_usuario = "Test User"
        self.bot_telefone = "+5511888888888"

        unique_id = uuid.uuid4()
        self.email = f"test_{unique_id}@example.com"

        self.customer = Customer.objects.create(
            name="Fulano de Tal",
            email=self.email,
            phone=self.usuario_telefone,
        )

        Service.objects.registrar_servicos([
            {
                "name": "Corte",
                "description": "Corte básico",
                "price": 50,
                "duration": 30,
            }
        ])

    def tearDown(self):
        conversations.clear()

    @patch(PATCH_ENVIAR)
    def test_usuario_existente_deve_marcar_agendamento(self, mock_enviar):
        # 1 - Estado inicial
        with patch(PATCH_BUSCAR_DATAS, return_value=MOCK_DATAS_DISPONIVEIS):
            processar_mensagem_whatsapp("Oi", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.AGUARDANDO_OPCAO_MENU)

        # 2 - Escolhe opção 1 (Agendar)
        processar_mensagem_whatsapp("1", self.bot_telefone, self.usuario_telefone, self.nome_usuario)
        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.DEFININDO_DATA)

        # 3 - Escolhe uma data
        with patch(PATCH_CHECAR_DATA_EM_USO, return_value=False):
            processar_mensagem_whatsapp("1", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.AGUARDANDO_ESCOLHA_SERVICO)

        # 4 - Escolhe o serviço (opção 1)
        processar_mensagem_whatsapp("1", self.bot_telefone, self.usuario_telefone, self.nome_usuario)
        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.LOCAL_ATENDIMENTO)

        # 5 - Escolhe local (opção 2 - Salão)
        processar_mensagem_whatsapp("2", self.bot_telefone, self.usuario_telefone, self.nome_usuario)
        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.CONFIRMANDO_AGENDAMENTO)

        # 6 - Confirma o agendamento
        processar_mensagem_whatsapp("1", self.bot_telefone, self.usuario_telefone, self.nome_usuario)
        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.IDLE)

        mock_enviar.assert_any_call(
            self.usuario_telefone,
            MensagemBOT.AGENDAMENTO_CONFIRMADO,
            self.bot_telefone,
        )

        appointment = Appointment.objects.filter(customer=self.customer).first()
        self.assertIsNotNone(appointment)
        self.assertEqual(appointment.status, 'scheduled')
        self.assertEqual(appointment.scheduled_at.date(), MOCK_DATAS_DISPONIVEIS[0])

    @patch(PATCH_ENVIAR)
    def test_usuario_recusa_criar_conta(self, mock_enviar):
        Customer.objects.all().delete()

        with patch(PATCH_BUSCAR_DATAS, return_value=MOCK_DATAS_DISPONIVEIS):
            processar_mensagem_whatsapp("Oi", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        processar_mensagem_whatsapp("Novo Usuario", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.SOLICITACAO_PARA_CRIAR_CONTA)

        processar_mensagem_whatsapp("2", self.bot_telefone, self.usuario_telefone, self.nome_usuario)
        conv = get_conversation(self.usuario_telefone)

        self.assertEqual(conv.state, Status.INICIAL)
        mock_enviar.assert_called_with(
            self.usuario_telefone,
            MensagemBOT.SAIR,
            self.bot_telefone,
        )

    @patch(PATCH_ENVIAR)
    def test_agendamento_a_domicilio_com_endereco(self, mock_enviar):
        with patch(PATCH_BUSCAR_DATAS, return_value=MOCK_DATAS_DISPONIVEIS):
            processar_mensagem_whatsapp("Oi", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        # Usuário já cadastrado (self.customer, criado no setUp) -> vai
        # direto pro menu principal após informar o nome.
        processar_mensagem_whatsapp("João Silva", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.AGUARDANDO_OPCAO_MENU)

        processar_mensagem_whatsapp("1", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        # Escolher data
        with patch(PATCH_CHECAR_DATA_EM_USO, return_value=False):
            processar_mensagem_whatsapp("1", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.AGUARDANDO_ESCOLHA_SERVICO)

        # Escolher serviço (opção 1)
        processar_mensagem_whatsapp("1", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.LOCAL_ATENDIMENTO)

        # Escolher local (1 = domicílio)
        processar_mensagem_whatsapp("1", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.AGUARDANDO_ENDERECO)

        mock_enviar.assert_called_with(
            self.usuario_telefone,
            MensagemBOT.INFORMAR_ENDERECO,
            self.bot_telefone,
        )

        endereco = "Rua Teste, 123, Apto 45, CEP: 12345-678, Bairro Centro"
        processar_mensagem_whatsapp(endereco, self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.CONFIRMANDO_AGENDAMENTO)
        self.assertEqual(conv.data["agendamento"].local_atendimento, endereco)

        processar_mensagem_whatsapp("1", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.IDLE)

        appointment = Appointment.objects.filter(customer=self.customer).first()
        self.assertIsNotNone(appointment)

    @patch(PATCH_ENVIAR)
    def test_cancelar_agendamento_com_sucesso(self, mock_enviar):
        app1 = Appointment.objects.create(
            customer=self.customer,
            scheduled_at=timezone.make_aware(datetime.combine(date.today() + timedelta(days=5), dt_time(10, 0))),
            status="scheduled",
        )
        Appointment.objects.create(
            customer=self.customer,
            scheduled_at=timezone.make_aware(datetime.combine(date.today() + timedelta(days=6), dt_time(14, 0))),
            status="scheduled",
        )

        with patch(PATCH_BUSCAR_DATAS, return_value=MOCK_DATAS_DISPONIVEIS):
            processar_mensagem_whatsapp("Oi", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        processar_mensagem_whatsapp("2", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.CANCELAMENTO)

        processar_mensagem_whatsapp("1", self.bot_telefone, self.usuario_telefone, self.nome_usuario)
        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.CONFIRMANDO_CANCELAMENTO)

        processar_mensagem_whatsapp("1", self.bot_telefone, self.usuario_telefone, self.nome_usuario)
        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.IDLE)

        mock_enviar.assert_any_call(
            self.usuario_telefone,
            MensagemBOT.CANCELAMENTO_CONFIRMADO,
            self.bot_telefone,
        )

        app1.refresh_from_db()
        self.assertEqual(app1.status, 'canceled')

    @patch(PATCH_ENVIAR)
    def test_abortar_cancelamento(self, mock_enviar):
        with patch(PATCH_BUSCAR_DATAS, return_value=MOCK_DATAS_DISPONIVEIS):
            processar_mensagem_whatsapp("Oi", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        mock_agendamentos = [
            MagicMock(
                scheduled_at=datetime(2026, 4, 5, 10, 0),
                location="Rua Nelson Tigrão, 15, Vila Missionária, CEP: 04430-165",
            )
        ]

        with patch(PATCH_BUSCAR_AGENDAMENTOS, return_value=mock_agendamentos):
            processar_mensagem_whatsapp("2", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        processar_mensagem_whatsapp("1", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.CONFIRMANDO_CANCELAMENTO)

        processar_mensagem_whatsapp("2", self.bot_telefone, self.usuario_telefone, self.nome_usuario)
        conv = get_conversation(self.usuario_telefone)

        self.assertEqual(conv.state, Status.IDLE)
        mock_enviar.assert_any_call(
            self.usuario_telefone,
            MensagemBOT.CANCELAMENTO_ABORTADO,
            self.bot_telefone,
        )

    @patch(PATCH_ENVIAR)
    def test_consultar_agendamentos_com_sucesso(self, mock_enviar):
        with patch(PATCH_BUSCAR_DATAS, return_value=MOCK_DATAS_DISPONIVEIS):
            processar_mensagem_whatsapp("Oi", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        mock_agendamentos = [
            MagicMock(
                scheduled_at=datetime(2026, 4, 5, 10, 0),
                location="Rua Nelson Tigrão, 15, Vila Missionária, CEP: 04430-165",
            ),
            MagicMock(
                scheduled_at=datetime(2026, 4, 15, 10, 0),
                location="Rua Nelson Tigrão, 15, Vila Missionária, CEP: 04430-165",
            ),
        ]

        with patch(PATCH_BUSCAR_AGENDAMENTOS, return_value=mock_agendamentos):
            processar_mensagem_whatsapp("3", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.IDLE)

    @patch(PATCH_ENVIAR)
    def test_consultar_sem_agendamentos(self, mock_enviar):
        with patch(PATCH_BUSCAR_DATAS, return_value=MOCK_DATAS_DISPONIVEIS):
            processar_mensagem_whatsapp("Oi", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        with patch(PATCH_BUSCAR_AGENDAMENTOS, return_value=[]):
            processar_mensagem_whatsapp("3", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        mock_enviar.assert_any_call(
            self.usuario_telefone,
            MensagemBOT.SEM_AGENDAMENTOS,
            self.bot_telefone,
        )

    @patch(PATCH_ENVIAR)
    def test_validacao_nome_invalido(self, mock_enviar):
        novo_usuario = "+551122222222"

        with patch(PATCH_BUSCAR_DATAS, return_value=MOCK_DATAS_DISPONIVEIS):
            processar_mensagem_whatsapp("Oi", self.bot_telefone, novo_usuario, self.nome_usuario)

        processar_mensagem_whatsapp("123", self.bot_telefone, novo_usuario, self.nome_usuario)

        conv = get_conversation(novo_usuario)
        self.assertEqual(conv.state, Status.VALIDANDO_USUARIO)
        mock_enviar.assert_any_call(
            novo_usuario,
            MensagemBOT.NOME_NAO_INFORMADO,
            self.bot_telefone,
        )

        processar_mensagem_whatsapp("", self.bot_telefone, novo_usuario, self.nome_usuario)
        conv = get_conversation(novo_usuario)
        self.assertEqual(conv.state, Status.VALIDANDO_USUARIO)

    @patch(PATCH_ENVIAR)
    def test_opcao_invalida_no_menu_principal(self, mock_enviar):
        with patch(PATCH_BUSCAR_DATAS, return_value=MOCK_DATAS_DISPONIVEIS):
            processar_mensagem_whatsapp("Oi", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        processar_mensagem_whatsapp("99", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        mock_enviar.assert_called_with(
            self.usuario_telefone,
            MensagemBOT.OPCAO_INVALIDA,
            self.bot_telefone,
        )

        processar_mensagem_whatsapp("abc", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        mock_enviar.assert_called_with(
            self.usuario_telefone,
            MensagemBOT.OPCAO_INVALIDA,
            self.bot_telefone,
        )

    @patch(PATCH_ENVIAR)
    def test_abortar_agendamento_na_confirmacao(self, mock_enviar):
        with patch(PATCH_BUSCAR_DATAS, return_value=MOCK_DATAS_DISPONIVEIS):
            processar_mensagem_whatsapp("Oi", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        # Menu -> Agendar
        processar_mensagem_whatsapp("1", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        # Escolher data
        with patch(PATCH_CHECAR_DATA_EM_USO, return_value=False):
            processar_mensagem_whatsapp("1", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.AGUARDANDO_ESCOLHA_SERVICO)

        # Escolher serviço
        processar_mensagem_whatsapp("1", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.LOCAL_ATENDIMENTO)

        # Escolher local (2 = salão)
        processar_mensagem_whatsapp("2", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.CONFIRMANDO_AGENDAMENTO)

        # Abortar (opção 2)
        processar_mensagem_whatsapp("2", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.IDLE)

        mock_enviar.assert_any_call(
            self.usuario_telefone,
            MensagemBOT.CANCELAMENTO_CONFIRMADO,
            self.bot_telefone,
        )

    @patch(PATCH_ENVIAR)
    def test_sair_do_menu_principal(self, mock_enviar):
        with patch(PATCH_BUSCAR_DATAS, return_value=MOCK_DATAS_DISPONIVEIS):
            processar_mensagem_whatsapp("Oi", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        processar_mensagem_whatsapp("4", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.SAIR)
        self.assertEqual(len(conv.data), 0)
        mock_enviar.assert_called_with(
            self.usuario_telefone,
            MensagemBOT.SAIR,
            self.bot_telefone,
        )

    @patch(PATCH_ENVIAR)
    def test_selecao_data_invalida(self, mock_enviar):
        with patch(PATCH_BUSCAR_DATAS, return_value=MOCK_DATAS_DISPONIVEIS):
            processar_mensagem_whatsapp("Oi", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        processar_mensagem_whatsapp("1", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.DEFININDO_DATA)

        processar_mensagem_whatsapp("99", self.bot_telefone, self.usuario_telefone, self.nome_usuario)

        conv = get_conversation(self.usuario_telefone)
        self.assertEqual(conv.state, Status.DEFININDO_DATA)
        mock_enviar.assert_called_with(
            self.usuario_telefone,
            MensagemBOT.OPCAO_INVALIDA,
            self.bot_telefone,
        )
