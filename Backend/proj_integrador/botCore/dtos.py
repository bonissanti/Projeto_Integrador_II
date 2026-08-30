from dataclasses import dataclass, field
from typing import Optional

@dataclass
class UsuarioContextoDTO:
    wa_id: str
    nome: Optional[str] = None
    email: Optional[str] = None


@dataclass
class AgendamentoDTO:
    usuario_wa_id: str
    data_hora: Optional[dict] = None
    datas_disponiveis: Optional[list] = None
    local_atendimento: Optional[str] = None


