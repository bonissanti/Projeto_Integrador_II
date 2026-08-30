from datetime import datetime, time
from Agendamento.models import Appointment, Customer, Service
from botCore.dtos import UsuarioContextoDTO, AgendamentoDTO
from botCore.utils import opcao_cancelar, opcao_consultar, opcao_agendar, opcao_sair, checar_email, set_state
from botCore.helper import MensagemBOT, Conversation, conversations
from .bot_enums import Status, LocalAtendimento
from botCore.send_message import enviar_mensagem_via_whats
import secrets

def processar_mensagem_whatsapp(mensagem_do_usuario: str, bot_telefone: str, usuario_telefone: str, nome_usuario: str):
    conv = get_conversation(usuario_telefone)

    endereco_padrao: str = "Rua Nelson Tigrão, 15, Vila Missionária, CEP: 04430-165"

    if conv.state == Status.IDLE and not conv.data:
        agendamentos: list[datetime] = Appointment.objects.buscar_agendamentos_disponiveis_no_periodo(20)
        conv.state = Status.INICIAL
        conv.data = {
            "usuario": UsuarioContextoDTO(wa_id=usuario_telefone, nome=nome_usuario),
            "agendamento": AgendamentoDTO(usuario_wa_id=usuario_telefone, datas_disponiveis=agendamentos),
            "LocalAtendimento": LocalAtendimento.SALAO,
            "servico": None,
        }

    match conv.state:
        case Status.INICIAL:
            gerenciar_status_inicial(usuario_telefone, bot_telefone)

        case Status.VALIDANDO_USUARIO:
            gerenciar_validacao_usuario(usuario_telefone, bot_telefone, mensagem_do_usuario)

        case Status.SOLICITACAO_PARA_CRIAR_CONTA:
            gerenciar_solicitacao_para_criar_conta(usuario_telefone, bot_telefone, mensagem_do_usuario)

        case Status.SOLICITACAO_PARA_EMAIL:
            gerenciar_solicitacao_para_email(usuario_telefone, bot_telefone, mensagem_do_usuario)

        case Status.AGUARDANDO_OPCAO_MENU:
            gerenciar_menu_principal(usuario_telefone, bot_telefone, mensagem_do_usuario)

        case Status.DEFININDO_DATA:
            gerenciar_escolha_data(usuario_telefone, bot_telefone, mensagem_do_usuario)

        # case Status.SOLICITACAO_PARA_SERVICO:
        #     gerenciar_solicitacao_para_servico(usuario_telefone, bot_telefone, mensagem_do_usuario)

        case Status.AGUARDANDO_ESCOLHA_SERVICO:
            gerenciar_escolha_servico(usuario_telefone, bot_telefone, mensagem_do_usuario)

        case Status.LOCAL_ATENDIMENTO:
            gerenciar_local_atendimento(usuario_telefone, bot_telefone, mensagem_do_usuario, endereco_padrao)

        case Status.AGUARDANDO_ENDERECO:
            gerenciar_endereco(usuario_telefone, bot_telefone, mensagem_do_usuario)

        case Status.CONFIRMANDO_AGENDAMENTO:
            gerenciar_confirmacao_agendamento(usuario_telefone, bot_telefone, mensagem_do_usuario)

        case Status.CANCELAMENTO:
            gerenciar_cancelamento(usuario_telefone, bot_telefone, mensagem_do_usuario)

        case Status.CONFIRMANDO_CANCELAMENTO:
            gerenciar_confirmar_cancelamento(usuario_telefone, bot_telefone, mensagem_do_usuario)

        case Status.IDLE:
            gerenciar_menu_principal(usuario_telefone, bot_telefone, mensagem_do_usuario)

        case Status.SAIR:
            reset_conversation(usuario_telefone)


def gerenciar_status_inicial(usuario_telefone: str, bot_telefone: str) -> None:
    usuario = Customer.objects.buscar_usuario_por_telefone(usuario_telefone)

    if usuario:
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.bem_vindo_customizado(usuario.name), bot_telefone)
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.MENU_PRINCIPAL, bot_telefone)
        set_state(usuario_telefone, Status.AGUARDANDO_OPCAO_MENU)
        return

    enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.BOAS_VINDAS, bot_telefone)
    set_state(usuario_telefone, Status.VALIDANDO_USUARIO)


def gerenciar_validacao_usuario(usuario_telefone: str, bot_telefone: str, mensagem_do_usuario: str) -> None:
    mensagem = mensagem_do_usuario.strip()

    if not mensagem or mensagem.isdigit() or len(mensagem) < 2:
        set_state(usuario_telefone, Status.VALIDANDO_USUARIO)
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.NOME_NAO_INFORMADO, bot_telefone)
        return

    conv = get_conversation(usuario_telefone)
    conv.data["usuario"].nome = mensagem

    usuario_existe: bool = Customer.objects.checar_se_usuario_existe_por_telefone(usuario_telefone)

    if usuario_existe:
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.MENU_PRINCIPAL, bot_telefone)
        usuario: Customer = Customer.objects.buscar_usuario_por_telefone(usuario_telefone)
        conv.data["usuario"].wa_id = usuario.phone
        conv.data["usuario"].email = usuario.email
        conv.data["usuario"].nome = usuario.name
        set_state(usuario_telefone, Status.AGUARDANDO_OPCAO_MENU)

    else:
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.NUMERO_NAO_CADASTRADO, bot_telefone)
        set_state(usuario_telefone, Status.SOLICITACAO_PARA_CRIAR_CONTA)


def gerenciar_solicitacao_para_criar_conta(usuario_telefone: str, bot_telefone: str, mensagem_do_usuario: str) -> None:
    if not mensagem_do_usuario.isdigit():
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)
        return

    if mensagem_do_usuario == "1":
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.SOLICITAR_DADOS_CADASTRO, bot_telefone)
        set_state(usuario_telefone, Status.SOLICITACAO_PARA_EMAIL)

    elif mensagem_do_usuario == "2":
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.SAIR, bot_telefone)
        set_state(usuario_telefone, Status.INICIAL)

    else:
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)


def gerenciar_solicitacao_para_email(usuario_telefone: str, bot_telefone: str, mensagem_do_usuario: str) -> None:
    if not checar_email(mensagem_do_usuario):
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.EMAIL_INVALIDO, bot_telefone)
        return

    conv = get_conversation(usuario_telefone)
    conv.data["usuario"].email = mensagem_do_usuario
    senha = secrets.token_urlsafe(12)
    Customer.objects.cadastrar_usuario(conv.data["usuario"].nome, conv.data["usuario"].email, conv.data["usuario"].wa_id, senha)
    enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.MENU_PRINCIPAL, bot_telefone)
    set_state(usuario_telefone, Status.AGUARDANDO_OPCAO_MENU)


def gerenciar_menu_principal(usuario_telefone: str, bot_telefone: str, mensagem_do_usuario: str) -> None:
    if not mensagem_do_usuario.isdigit():
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)
        return

    conv = get_conversation(usuario_telefone)

    if mensagem_do_usuario == "1":
        opcao_agendar(conv, usuario_telefone, bot_telefone, mensagem_do_usuario)

    elif mensagem_do_usuario == "2":
        opcao_cancelar(conv, usuario_telefone, bot_telefone, mensagem_do_usuario)

    elif mensagem_do_usuario == "3":
        opcao_consultar(usuario_telefone, bot_telefone, mensagem_do_usuario)

    elif mensagem_do_usuario == "4":
        opcao_sair(conv, usuario_telefone, bot_telefone)

    else:
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)


def gerenciar_escolha_data(usuario_telefone: str, bot_telefone: str, mensagem_do_usuario: str) -> None:
    mensagem = mensagem_do_usuario.strip()
    conv = get_conversation(usuario_telefone)
    agendamentos = conv.data["agendamento"].datas_disponiveis

    if not mensagem.isdigit():
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)
        return

    indice = int(mensagem)

    if indice < 1 or indice > len(agendamentos):
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)
        return

    data_em_uso: bool = Appointment.objects.checar_se_data_esta_em_uso(agendamentos[indice - 1])

    if data_em_uso:
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.DATA_EM_USO, bot_telefone)
        return

    agendamento_escolhido = agendamentos[indice - 1]

    conv = get_conversation(usuario_telefone)
    conv.data["agendamento"].data_hora = agendamento_escolhido

    servicos = Service.objects.listar_servicos_por_nome()
    enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.selecionar_servico(servicos), bot_telefone)
    set_state(usuario_telefone, Status.AGUARDANDO_ESCOLHA_SERVICO)


def gerenciar_escolha_servico(usuario_telefone: str, bot_telefone: str, mensagem_do_usuario: str) -> None:
    if not mensagem_do_usuario.isdigit():
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)
        return

    indice = int(mensagem_do_usuario)
    numero_servicos_oferecidos = Service.objects.buscar_numero_de_servicos_oferecidos()

    if indice < 1 or indice > numero_servicos_oferecidos:
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)
        return

    servico_escolhido = Service.objects.buscar_servico_por_id(indice)
    conv = get_conversation(usuario_telefone)
    conv.data["servico"] = servico_escolhido
    enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.LOCAL_ATENDIMENTO, bot_telefone)
    set_state(usuario_telefone, Status.LOCAL_ATENDIMENTO)


def gerenciar_local_atendimento(usuario_telefone: str, bot_telefone: str, mensagem_do_usuario: str, endereco_padrao: str) -> None:
    mensagem = mensagem_do_usuario.strip()

    if not mensagem_do_usuario.isdigit():
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)
        return

    conv = get_conversation(usuario_telefone)

    if mensagem == "1":
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.INFORMAR_ENDERECO, bot_telefone)
        set_state(usuario_telefone, Status.AGUARDANDO_ENDERECO)

    elif mensagem == "2":
        gerenciar_bot_confirmacao_agendamento(usuario_telefone, bot_telefone, endereco_padrao)

    else:
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)


def gerenciar_endereco(usuario_telefone: str, bot_telefone: str, mensagem_do_usuario: str) -> None:
    endereco = mensagem_do_usuario.strip()

    if not endereco:
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)
        return

    gerenciar_bot_confirmacao_agendamento(usuario_telefone, bot_telefone, endereco)


def gerenciar_confirmacao_agendamento(usuario_telefone: str, bot_telefone: str, mensagem_do_usuario: str) -> None:
    conv = get_conversation(usuario_telefone)
    mensagem = mensagem_do_usuario.strip()

    if not mensagem.isdigit():
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)
        return

    if mensagem == "1":
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.AGENDAMENTO_CONFIRMADO, bot_telefone)
        set_state(usuario_telefone, Status.IDLE)

        conv = get_conversation(usuario_telefone)
        agendamento_dto = conv.data["agendamento"]

        data_escolhida = agendamento_dto.data_hora.get('data') if isinstance(agendamento_dto.data_hora,
                                                                             dict) else agendamento_dto.data_hora
        horario_padrao = time(11, 0)

        from datetime import datetime
        scheduled_at = datetime.combine(data_escolhida, horario_padrao)
        customer = Customer.objects.buscar_usuario_por_telefone(usuario_telefone)
        local = conv.data["agendamento"].local_atendimento
        servico = conv.data["servico"]
        Appointment.objects.marcar_agendamento(
            customer,
            scheduled_at,
            local,
            [servico],
        )

        set_state(usuario_telefone, Status.IDLE)
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.IDLE, bot_telefone)

    elif mensagem == "2":
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.CANCELAMENTO_CONFIRMADO, bot_telefone)
        set_state(usuario_telefone, Status.IDLE)
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.IDLE, bot_telefone)

    else:
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)

def gerenciar_cancelamento(usuario_telefone: str, bot_telefone: str, mensagem_do_usuario: str) -> None:
    mensagem = mensagem_do_usuario.strip()

    if not mensagem.isdigit():
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)
        return

    indice = int(mensagem)

    conv = get_conversation(usuario_telefone)
    agendamentos = conv.data.get("agendamentos", [])

    if indice < 1 or indice > len(agendamentos):
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)
        return

    agendamento = agendamentos[indice - 1]
    conv.data["agendamento_para_cancelar"] = agendamento

    msg = MensagemBOT.confirmar_cancelamento(agendamento)
    enviar_mensagem_via_whats(usuario_telefone, msg, bot_telefone)
    set_state(usuario_telefone, Status.CONFIRMANDO_CANCELAMENTO)


def gerenciar_confirmar_cancelamento(usuario_telefone: str, bot_telefone: str, mensagem_do_usuario: str) -> None:
    mensagem = mensagem_do_usuario.strip()

    if not mensagem_do_usuario.isdigit():
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)
        return

    conv = get_conversation(usuario_telefone)
    agendamento = conv.data.get("agendamento_para_cancelar")

    if mensagem == "1":
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.CANCELAMENTO_CONFIRMADO, bot_telefone)
        set_state(usuario_telefone, Status.IDLE)
        Appointment.objects.cancelar_agendamento(agendamento)
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.IDLE, bot_telefone)

    elif mensagem == "2":
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.CANCELAMENTO_ABORTADO, bot_telefone)
        set_state(usuario_telefone, Status.IDLE)
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.IDLE, bot_telefone)

    else:
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.OPCAO_INVALIDA, bot_telefone)


def reset_conversation(phone: str):
    conversations.pop(phone, None)


def gerenciar_bot_confirmacao_agendamento(usuario_telefone: str, bot_telefone: str, endereco_padrao: str):
    conv = get_conversation(usuario_telefone)

    conv.data["agendamento"].local_atendimento = endereco_padrao
    agendamento = conv.data["agendamento"].data_hora
    nome_usuario = conv.data["usuario"].nome
    servico: Service = conv.data["servico"]

    msg = MensagemBOT.confirmar_agendamento(nome_usuario, agendamento, endereco_padrao, servico.name)
    enviar_mensagem_via_whats(usuario_telefone, msg, bot_telefone)
    set_state(usuario_telefone, Status.CONFIRMANDO_AGENDAMENTO)

def get_conversation(phone: str) -> Conversation:
    if phone not in conversations:
        conversations[phone] = Conversation()
    return conversations[phone]

