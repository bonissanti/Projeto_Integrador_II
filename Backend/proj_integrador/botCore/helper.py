from dataclasses import dataclass, field
from xmlrpc.client import DateTime

from Agendamento.models import Appointment
from botCore.bot_enums import Status

class MensagemBOT:
    DATA_EM_USO = "Opa, esta data já está ocupada, por favor, informe uma outra opção."
    BOAS_VINDAS = "Olá, bem-vindo(a) ao meu serviço de agendamento para tranças! Por favor, para darmos andamento, informe seu nome e sobrenome 🙂"
    INFORMAR_ENDERECO = "Por favor, informe seu endereço com Rua, Número, complemento (se houver), CEP e bairro:"
    NUMERO_NAO_CADASTRADO = "Você não possui cadastro. Gostaria de criar uma conta?\nDigite um dos valores abaixo:\n\n1 - Sim\n2 - Não"
    SOLICITAR_DADOS_CADASTRO = "Por favor, informe o seu email\n"
    MENU_PRINCIPAL = "O que deseja fazer?\nDigite um dos valores abaixo:\n\n1 - Agendar\n2 - Cancelar agendamento\n3 - Consultar agendamentos\n4 - Sair"
    OPCAO_INVALIDA = "Opção inválida. Por favor, escolha uma das opções disponíveis."
    EMAIL_INVALIDO = "Opa, parece que o email informado não é válido, revise e tente novamente!"
    NOME_NAO_INFORMADO = "Opa! Esse nome me parece incorreto, por favor, informe seu nome novamente."
    LOCAL_ATENDIMENTO = "Em qual local deseja ser atendido(a)?\nDigite um dos valores abaixo:\n\n1 - Em sua residência (Taxa adicional)\n2 - Em meu salão"
    AGENDAMENTO_CONFIRMADO = "Agendamento confirmado! ✅\n"
    CANCELAMENTO_CONFIRMADO = "Agendamento cancelado! ❌"
    CANCELAMENTO_ABORTADO = "Cancelamento abortado! ✅"
    SAIR = "OK! Atendimento finalizado! Caso deseje iniciar uma nova conversa posteriormente, digite 'Oi' para reiniciarmos 😉"
    SEM_AGENDAMENTOS = "Você não possui agendamentos."
    IDLE = "Deseja fazer algo mais?\n1 - Agendar\n2 - Cancelar agendamento\n3 - Consultar agendamentos\n4 - Sair"

    @staticmethod
    def informarDatasDisponiveis(datas: list) -> str:
        lista = "\n".join(
            f"{i + 1} - {d.strftime('%d/%m/%Y')} às 14:00"
            for i, d in enumerate(datas)
        )
        return f"Estas são minhas datas disponíveis nos próximos 20 dias:\n{lista}\n\nEscolha uma opção:"

    @staticmethod
    def confirmar_agendamento(nome: str, agendamento: list, endereco: str, nome_servico: str) -> str:
        data_formatada = agendamento.strftime('%d/%m/%Y')
        return f"Ok, {nome}, posso confirmar o agendamento para:\n\n📅 {data_formatada}\n✨ Serviço: {nome_servico}\n🏠 Local: {endereco}\n\n1 - Sim\n2 - Não"

    @staticmethod
    def listar_agendamentos(agendamentos: list[Appointment]) -> str:
        if not agendamentos:
            return MensagemBOT.SEM_AGENDAMENTOS
        lista = "\n".join(
            f"{i+1} - {a.scheduled_at.strftime('%d/%m/%y às %H:%M')} - local: {a.location}"
            for i, a in enumerate(agendamentos)
        )
        return f"Seus agendamentos:\n{lista}"

    @staticmethod
    def selecionar_agendamento(agendamentos: list[Appointment]) -> str:
        if not agendamentos:
            return MensagemBOT.SEM_AGENDAMENTOS
        lista = "\n".join(
            f"{i+1} - {a.scheduled_at.strftime('%d/%m/%y às %H:%M')} - local: {a.location}"
            for i, a in enumerate(agendamentos)
        )
        return f"Qual agendamento deseja cancelar? Selecione um dos valores:\n{lista}"

    @staticmethod
    def confirmar_cancelamento(agendamento: Appointment) -> str:
        return (
            f"Cancelar este agendamento? Digite um dos valores abaixo: \n"
            f"📅 {agendamento.scheduled_at.strftime('%d/%m/%y às %H:%M')}\n\n1 - Sim\n2 - Não"
        )

    @staticmethod
    def criar_conta_com_cpf_informado_previamente(cpf: str) -> str:
        return f"Deseja criar uma conta com o CPF {cpf}, informado anteriormente?"

    def bem_vindo_customizado(nome: str) -> str:
        return f"Olá, bem-vindo(a) de volta, {nome}! 🫶"

    @staticmethod
    def selecionar_servico(servicos: list[str]) -> str:
        lista = "\n".join(f"{i + 1} - {name}" for i, name in enumerate(servicos))
        return f"Selecione o número do seu serviço desejado:\n{lista}"

@dataclass
class Conversation:
    state: Status = Status.IDLE
    data: dict = field(default_factory=dict)