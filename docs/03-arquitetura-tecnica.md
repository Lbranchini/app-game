# 03 — Arquitetura Técnica

> **Decisões fechadas (abr 2026):**
> - Cliente: **Godot 4.x** (2D, exporta Android e iOS)
> - Backend: **Python 3.12 + FastAPI**
> - Direção de arte: **Cartoon 2D** (paleta vibrante, contornos claros, expressividade exagerada)
> - Roster MVP: **16 personagens**

---

## 1. Stack do cliente (Godot 4)

**Por quê Godot:**
- Engine de jogo de verdade (animações 2D, partículas, áudio, tween).
- Exporta nativamente para Android e iOS.
- 100% grátis, open-source, sem royalties.
- GDScript fácil de escrever; perfil de habilidade similar a Python.
- Comunidade ativa e cresceu muito desde 2023.

**O que será no cliente:**
- Renderização da batalha, animações, efeitos visuais.
- UI de menus, deckbuilding, perfil, loja.
- Camada de rede (WebSocket cliente).
- **Nunca** lógica de regras autoritativa — só predição visual.

**Layout interno (Godot):**

```
client/
├── project.godot
├── scenes/
│   ├── main_menu.tscn
│   ├── team_select.tscn
│   ├── battle/
│   │   ├── battle.tscn
│   │   ├── character_card.tscn
│   │   └── skill_button.tscn
│   ├── profile.tscn
│   └── shop.tscn
├── scripts/
│   ├── net/                # WebSocket, REST
│   ├── battle/             # lógica de UI da batalha
│   ├── data/               # carrega YAMLs de personagens
│   └── autoload/           # singletons (auth, settings)
├── assets/
│   ├── sprites/
│   ├── sfx/
│   ├── music/
│   └── ui/
└── addons/
```

---

## 2. Stack do servidor (Python)

**Por quê Python (vs Node.js / Go):**
- Sintaxe limpa para lógica de regras complexa (status effects, prioridade, modificadores).
- `pydantic` para validação de payloads e dos YAMLs de personagens — é praticamente um superpoder neste projeto.
- `pytest` excelente para testar centenas de combinações de habilidades.
- FastAPI: async-first, WebSockets nativos, OpenAPI auto-gerado, performance suficiente para um turn-based.
- Equipe brasileira média conhece Python melhor que Go.

**Trade-offs aceitos:**
- Python é mais lento que Go para CPU-heavy. Não é problema aqui — turnos resolvem em milissegundos com muita folga.
- Concorrência via `asyncio` (não threads) — exige disciplina, mas FastAPI já guia bem.

### Componentes

| Componente | Tecnologia | Motivo |
|---|---|---|
| API HTTP / WebSocket | **FastAPI** | Async, WebSockets nativos, OpenAPI |
| Validação de schemas | **Pydantic v2** | YAML/JSON dos personagens validados em memória |
| Banco principal | **PostgreSQL 16** | Perfis, partidas, ranking |
| ORM | **SQLAlchemy 2.0** + **Alembic** | Padrão Python maduro |
| Cache + matchmaking | **Redis** | Filas, Elo lookups, sessions |
| Workers | **arq** ou **dramatiq** | Tarefas em background (recompensas, cleanup) |
| Auth | **Firebase Auth** (cliente) → JWT verificado no servidor | Google + Apple Sign-in prontos |
| Testes | **pytest + hypothesis** | Property-based testing nas regras |
| Lint/format | **ruff + mypy** | Estrito |
| Hosting | **Fly.io** ou **Railway** | Deploy simples, escala razoável |
| Container | **Docker** + **uv** para deps | uv = pip moderno, super rápido |

### Diagrama

```
Cliente (Godot)
    │
    │ HTTPS (REST) ─── auth, perfil, matchmaking
    │ WSS ─────────── partida em andamento
    ↓
┌─────────────────────────────────────────┐
│  FastAPI app                            │
│  ├── /auth        (verifica JWT)        │
│  ├── /profile     (CRUD perfil)         │
│  ├── /matchmaking (entra/sai da fila)   │
│  └── /ws/match    (WebSocket da partida)│
└─────────────────────────────────────────┘
        │             │              │
        ↓             ↓              ↓
   PostgreSQL      Redis         Game Engine
   (persistente)   (transient)   (módulo Python puro)
```

---

## 3. Engine de regras (módulo Python puro)

A "engine" é um pacote `game/` puro — **sem I/O**, **sem rede**, **sem banco**. Recebe estado + ação, devolve novo estado + eventos.

```python
# server/src/game/engine.py (esboço)

from pydantic import BaseModel
from typing import Literal

class Action(BaseModel):
    character_id: str
    skill_id: str
    target_ids: list[str]
    energy_paid: dict[Literal["vigor","espirito","mente","sangue"], int]

def resolve_turn(
    state: MatchState,
    actions_a: list[Action],
    actions_b: list[Action],
) -> tuple[MatchState, list[Event]]:
    """Aplica todas as ações de um turno. Determinístico (mesma seed => mesmo resultado)."""
    ...
```

**Vantagens dessa separação:**
- Testa-se sem subir banco/rede.
- Pode rodar batch de simulações para balanceamento (10.000 partidas IA vs IA em segundos).
- Seed-based RNG para replays e debugging.

---

## 4. Estrutura de pastas (alvo)

```
app-game/
├── docs/                         # você está aqui
├── client/                       # projeto Godot
│   └── (ver layout acima)
├── server/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── src/
│   │   ├── api/                  # FastAPI: routers, deps
│   │   ├── auth/
│   │   ├── matchmaking/
│   │   ├── game/                 # engine de regras (puro Python)
│   │   ├── data_loader/          # carrega YAMLs
│   │   ├── db/                   # SQLAlchemy models, migrations
│   │   └── main.py
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── balance/              # simulações IA vs IA
│   └── Dockerfile
├── data/                         # SHARED entre cliente e servidor
│   ├── characters/
│   │   ├── grega/
│   │   ├── nordica/
│   │   ├── egipcia/
│   │   └── ...
│   ├── schema.json               # validação JSON Schema
│   └── balance.yaml              # constantes globais (HP base, custo de troca, etc.)
├── .github/workflows/            # CI: lint, mypy, pytest, validação YAMLs
└── README.md
```

`data/` é symlink para `client/data/` (ou submódulo) — única fonte da verdade dos personagens.

---

## 5. Esquema de dados (PostgreSQL)

```sql
CREATE TABLE players (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  firebase_uid TEXT UNIQUE NOT NULL,
  username TEXT UNIQUE NOT NULL,
  elo INT NOT NULL DEFAULT 1000,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_seen TIMESTAMPTZ
);

CREATE TABLE matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  player_a UUID NOT NULL REFERENCES players(id),
  player_b UUID NOT NULL REFERENCES players(id),
  team_a JSONB NOT NULL,           -- ["aquiles","atena","isis"]
  team_b JSONB NOT NULL,
  state JSONB NOT NULL,            -- snapshot completo (HPs, cooldowns, status)
  current_turn INT NOT NULL DEFAULT 0,
  current_player UUID REFERENCES players(id),
  winner UUID REFERENCES players(id),
  rng_seed BIGINT NOT NULL,        -- determinismo / replay
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ended_at TIMESTAMPTZ
);

CREATE INDEX idx_matches_active ON matches(current_player) WHERE ended_at IS NULL;

CREATE TABLE match_actions (    -- log para replays/auditoria
  match_id UUID NOT NULL REFERENCES matches(id),
  turn INT NOT NULL,
  player UUID NOT NULL REFERENCES players(id),
  actions JSONB NOT NULL,
  ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (match_id, turn, player)
);
```

Personagens **não** ficam no banco — vivem em `data/characters/*.yaml`, versionados.

---

## 6. Fluxo de uma partida

```
[Player A]                  [FastAPI Server]              [Player B]
    │                              │                            │
    ├── POST /matchmaking/join ───>│                            │
    │                              │<── POST /matchmaking/join ─┤
    │                              │ (Redis match-maker pareou) │
    │                              │                            │
    │<── WS: match_found ──────────┼─── WS: match_found ───────>│
    │                              │                            │
    ├── WS: actions(turn=1) ──────>│                            │
    │                              │ engine.resolve_turn(...)   │
    │<── WS: state(turn=1) ────────┼─── WS: state(turn=1) ─────>│
    │                              │                            │
    │                              │<── WS: actions(turn=2) ────┤
    │<── WS: state(turn=2) ────────┼─── WS: state(turn=2) ─────>│
    │             ...                                           │
```

---

## 7. Anti-cheat

- Servidor é **única fonte da verdade**. Cliente só renderiza.
- Validação no servidor de toda ação:
  - O personagem está vivo?
  - Cooldown zerado?
  - Essência suficiente para o custo?
  - Alvo é válido (vivo, alcançável, condição "furtivo" respeitada)?
  - Personagem está livre de stun/silêncio/desarme aplicáveis?
- Ação inválida → ignorada + cliente recebe `state_correction`.
- RNG semeado pelo servidor → cliente nunca controla o "aleatório".

---

## 8. Decisões em aberto

- [ ] 🔧 Hosting: Fly.io (mais barato) ou GCP Cloud Run (mais escalável)?
- [ ] 🔧 Painel de balanceamento: dashboard interno em Streamlit ou só queries no PostgreSQL?
- [ ] 🔧 Tradução: i18n nos YAMLs (chave por idioma) ou arquivos `.po` separados?
