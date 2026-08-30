from enum import Enum

class Status(str, Enum):
    AGUARDANDO_ESCOLHA_SERVICO = "aguardando_servico"
    SOLICITACAO_PARA_SERVICO = "solicitacao_servico"
    SAIR = "Sair"
    INICIAL = "inicial"
    IDLE = "idle"
    VALIDANDO_USUARIO = "validando_usuario"
    SOLICITACAO_PARA_CRIAR_CONTA = "criando_conta"
    SOLICITACAO_PARA_EMAIL = "solicitacao_email"
    AGUARDANDO_EMAIL = "aguardando_email"
    AGUARDANDO_OPCAO_MENU = "aguardando_opcao"
    LOCAL_ATENDIMENTO = "local_atendimento"
    AGUARDANDO_ENDERECO = "aguardando_endereco"
    DEFININDO_DATA = "agendamento"
    CANCELAMENTO = "cancelamento"
    CONFIRMANDO_AGENDAMENTO = "confirmando_agendamento"
    CONFIRMANDO_CANCELAMENTO = "aguardando_cancelamento"

class LocalAtendimento(str, Enum):
    A_DOMICILIO = "A Domicílio"
    SALAO = "No Salão"