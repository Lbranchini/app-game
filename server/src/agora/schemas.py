"""Schemas de dados validados por Pydantic.

Vocabulário do jogo:
  - Essência: recurso para usar habilidades. 4 tipos + Genérica.
  - Habilidade: 4 por personagem (3 únicas + esquiva universal).
  - Status: efeito temporário (positivo ou negativo) aplicado a um personagem.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class Essencia(str, Enum):
    VIGOR = "vigor"
    ESPIRITO = "espirito"
    MENTE = "mente"
    SANGUE = "sangue"
    GENERICA = "generica"


class Arquetipo(str, Enum):
    DAMAGE_DEALER = "damage_dealer"
    HEALER = "healer"
    TANK = "tank"
    STUNNER = "stunner"
    DRAINER = "drainer"
    TRICK = "trick"
    SUPPORT = "support"
    LEADER = "leader"


class TipoHabilidade(str, Enum):
    INSTANTANEA = "instantanea"
    ACAO_CONTINUA = "acao_continua"
    CONTROLE = "controle"


class Alvo(str, Enum):
    INIMIGO_UNICO = "inimigo_unico"
    TODOS_INIMIGOS = "todos_inimigos"
    ALIADO_UNICO = "aliado_unico"
    TODOS_ALIADOS = "todos_aliados"
    SI_MESMO = "si_mesmo"


class TipoEfeito(str, Enum):
    DANO = "dano"
    CURA = "cura"
    INVULNERAVEL = "invulneravel"
    REDUCAO_DANO = "reducao_dano"
    BUFF_DANO = "buff_dano"
    ESCUDO_DESTRUTIVEL = "escudo_destrutivel"
    STATUS = "status"          # aplica status nomeado (sangramento, veneno, etc.)
    DRENO_ESSENCIA = "dreno_essencia"
    REMOVE_AFLICOES = "remove_aflicoes"


class ClasseDano(str, Enum):
    FISICO = "fisico"
    MAGICO = "magico"
    SAGRADO = "sagrado"
    MENTAL = "mental"


CustoEssencia = dict[Essencia, int]


class Efeito(BaseModel):
    """Um efeito atômico aplicado quando a habilidade resolve."""

    model_config = ConfigDict(extra="forbid")

    tipo: TipoEfeito
    valor: int = 0
    duracao: int = 0
    classe: ClasseDano | None = None
    status: str | None = None  # nome do status quando tipo == STATUS
    perfurante: bool = False
    verdadeiro: bool = False


class Habilidade(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    nome: str
    tipo: TipoHabilidade
    custo: CustoEssencia = Field(default_factory=dict)
    cooldown: Annotated[int, Field(ge=0)] = 0
    duracao: Annotated[int, Field(ge=0)] = 0
    alvo: Alvo
    efeitos: list[Efeito]


class Personagem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    nome: str
    mitologia: str
    arquetipo: Arquetipo
    hp_base: Annotated[int, Field(ge=50, le=200)]
    descricao: str | None = None
    habilidades: list[Habilidade]


# ---------- Estado de partida ----------


class StatusAtivo(BaseModel):
    """Instância de um status aplicado a um personagem em partida."""

    model_config = ConfigDict(extra="forbid")

    nome: str           # "sangramento", "veneno", "invulneravel", ...
    duracao: int        # turnos restantes
    valor: int = 0      # dano por turno, redução, etc.
    fonte: str | None = None  # personagem id que aplicou (para sangramento)


class CharacterState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str                       # ex: "aquiles"
    nome: str
    hp: int
    hp_max: int
    cooldowns: dict[str, int] = Field(default_factory=dict)  # skill_id -> turnos
    status: list[StatusAtivo] = Field(default_factory=list)
    escudo: int = 0  # HP de defesa destrutível absorvendo antes do HP

    @property
    def vivo(self) -> bool:
        return self.hp > 0


class PlayerSide(str, Enum):
    A = "A"
    B = "B"


class PlayerState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    side: PlayerSide
    personagens: list[CharacterState]
    essencias: dict[Essencia, int] = Field(
        default_factory=lambda: {e: 0 for e in Essencia if e != Essencia.GENERICA}
    )

    @property
    def derrotado(self) -> bool:
        return all(not c.vivo for c in self.personagens)


class MatchState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_id: str
    turno: int = 1
    jogador_atual: PlayerSide = PlayerSide.A
    a: PlayerState
    b: PlayerState
    rng_seed: int = 0
    encerrado: bool = False
    vencedor: PlayerSide | None = None

    def player(self, side: PlayerSide) -> PlayerState:
        return self.a if side == PlayerSide.A else self.b

    def oponente(self, side: PlayerSide) -> PlayerState:
        return self.b if side == PlayerSide.A else self.a


# ---------- Ações ----------


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")

    char_id: str           # personagem que age
    skill_id: str          # habilidade usada
    target_ids: list[str] = Field(default_factory=list)  # personagens-alvo
    paid: CustoEssencia = Field(default_factory=dict)    # essências pagas


# ---------- Eventos (log da partida) ----------


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal[
        "skill_usada",
        "dano",
        "cura",
        "status_aplicado",
        "status_expirou",
        "personagem_derrotado",
        "essencia_gerada",
        "essencia_drenada",
        "turno_iniciado",
        "turno_encerrado",
        "partida_encerrada",
        "acao_invalida",
    ]
    detalhes: dict[str, object] = Field(default_factory=dict)
