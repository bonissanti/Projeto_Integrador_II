import datetime
import random
from typing import List

from botCore.bot_enums import LocalAtendimento


def buscarAgendamentosDisponiveisNoPeriodoMock(total_dias: int)-> List[dict]:
    disponiveis = []
    hoje = datetime.datetime.now()

    if hoje.hour >= 10:
        data_base = hoje + datetime.timedelta(days=1)
    else:
        data_base = hoje

    for i in range(total_dias):
        data_atual = data_base + datetime.timedelta(days=i)

        if random.choice([True, False]):
            agendamento = {
                "data": data_atual.strftime("%d/%m/%Y"),
                "horario": "10:00",
                "local": random.choice(list(LocalAtendimento)),
            }
            disponiveis.append(agendamento)
    return disponiveis


def checarSeUsuarioExistePorTelefoneMock(numero_telefone: str):
    return random.choice([True, False])

def buscarAgendamentosPorTelefoneMock(numero_telefone: str) -> List[dict]:
    agendamento_do_usuario = []
    hoje = datetime.date.today()
    agendamentos_marcados = random.randint(1, 3)

    for i in range(agendamentos_marcados):
        data_atual = hoje + datetime.timedelta(days=i)

        if random.choice([True, False]):
            agendamento = {
                "data": data_atual.strftime("%d/%m/%Y"),
                "horario": "10:00",
                "local": random.choice([LocalAtendimento.A_DOMICILIO, LocalAtendimento.SALAO]),
            }
            agendamento_do_usuario.append(agendamento)
    return agendamento_do_usuario
