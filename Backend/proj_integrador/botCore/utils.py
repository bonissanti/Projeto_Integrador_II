from Agendamento.models import Appointment
from botCore.bot_enums import Status
from botCore.helper import MensagemBOT, Conversation
from botCore.interfaces import IMessageSender


def checar_email(email: str) -> bool:
    return "@" in email and "." in email


def opcao_cancelar(conv: Conversation, usuario_telefone: str, sender: IMessageSender, mensagem_do_usuario: str) -> None:
    agendamentos_do_usuario: list[Appointment] = Appointment.objects.buscar_agendamentos_por_numero_telefone(
        usuario_telefone)

    if not agendamentos_do_usuario:
        sender.enviar(usuario_telefone, MensagemBOT.SEM_AGENDAMENTOS)
        return

    msg = MensagemBOT.selecionar_agendamento(agendamentos_do_usuario)

    sender.enviar(usuario_telefone, msg)
    conv.data["agendamentos"] = agendamentos_do_usuario
    set_state(usuario_telefone, Status.CANCELAMENTO)


def opcao_consultar(usuario_telefone: str, sender: IMessageSender, mensagem_do_usuario: str) -> None:
    agendamentos_do_usuario: list[Appointment] = Appointment.objects.buscar_agendamentos_por_numero_telefone(
        usuario_telefone)
    sender.enviar(usuario_telefone, MensagemBOT.listar_agendamentos(agendamentos_do_usuario))
    set_state(usuario_telefone, Status.IDLE)
    sender.enviar(usuario_telefone, MensagemBOT.IDLE)


def opcao_agendar(conv: Conversation, usuario_telefone: str, sender: IMessageSender, mensagem_do_usuario: str) -> None:
    agendamentos = conv.data["agendamento"].datas_disponiveis
    datas_disponiveis = MensagemBOT.informarDatasDisponiveis(agendamentos)
    sender.enviar(usuario_telefone, datas_disponiveis)
    set_state(usuario_telefone, Status.DEFININDO_DATA)


def opcao_sair(conv: Conversation, usuario_telefone: str, sender: IMessageSender) -> None:
    conv.data.clear()
    sender.enviar(usuario_telefone, MensagemBOT.SAIR)
    set_state(usuario_telefone, Status.SAIR)

def set_state(phone: str, new_state: Status):
    from WhatsAppBot.engine import get_conversation

    conv = get_conversation(phone)
    conv.state = new_state