from Agendamento.models import Appointment
from WhatsAppBot.bot_enums import Status
from botCore.helper import MensagemBOT, Conversation
from botCore.send_message import enviar_mensagem_via_whats


def checar_email(email: str) -> bool:
    return "@" in email and "." in email


def opcao_cancelar(conv: Conversation, usuario_telefone: str, bot_telefone: str, mensagem_do_usuario: str) -> None:
    agendamentos_do_usuario: list[Appointment] = Appointment.objects.buscar_agendamentos_por_numero_telefone(
        usuario_telefone)

    if not agendamentos_do_usuario:
        enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.SEM_AGENDAMENTOS, bot_telefone)
        return

    msg = MensagemBOT.selecionar_agendamento(agendamentos_do_usuario)

    enviar_mensagem_via_whats(usuario_telefone, msg, bot_telefone)
    conv.data["agendamentos"] = agendamentos_do_usuario
    set_state(usuario_telefone, Status.CANCELAMENTO)


def opcao_consultar(usuario_telefone: str, bot_telefone: str, mensagem_do_usuario: str) -> None:
    agendamentos_do_usuario: list[Appointment] = Appointment.objects.buscar_agendamentos_por_numero_telefone(
        usuario_telefone)
    enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.listar_agendamentos(agendamentos_do_usuario), bot_telefone)
    set_state(usuario_telefone, Status.IDLE)
    enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.IDLE, bot_telefone)


def opcao_agendar(conv: Conversation, usuario_telefone: str, bot_telefone: str, mensagem_do_usuario: str) -> None:
    agendamentos = conv.data["agendamento"].datas_disponiveis
    datas_disponiveis = MensagemBOT.informarDatasDisponiveis(agendamentos)
    enviar_mensagem_via_whats(usuario_telefone, datas_disponiveis, bot_telefone)
    set_state(usuario_telefone, Status.DEFININDO_DATA)


def opcao_sair(conv: Conversation, usuario_telefone: str, bot_telefone: str) -> None:
    conv.data.clear()
    enviar_mensagem_via_whats(usuario_telefone, MensagemBOT.SAIR, bot_telefone)
    set_state(usuario_telefone, Status.SAIR)

def set_state(phone: str, new_state: Status):
    from WhatsAppBot.engine import get_conversation

    conv = get_conversation(phone)
    conv.state = new_state