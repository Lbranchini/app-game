# 03 — Arquitetura Técnica

## Decisões a tomar primeiro

Marcadas com 🔧 — precisam de validação antes de começar a codar.

---

## 1. Stack do cliente (mobile)

### Opção A — **Godot 4** (recomendada para jogo) 🔧

- **Prós:** engine de jogo de verdade (animações, partículas, áudio espacial); 2D maduro; grátis e open-source; exporta para Android e iOS; GDScript fácil; comunidade ativa.
- **Contras:** menos pacotes de UI prontos que Flutter; ecossistema mobile menor.

### Opção B — **Flutter + Flame**

- **Prós:** UI declarativa excelente para menus/inventário/loja; hot reload; um codebase Android+iOS+Web; Flame engine integrada para a parte de jogo.
- **Contras:** Flame é mais limitado que Godot para efeitos visuais; performance de animações complexas pior.

### Opção C — **Unity 2D**

- **Prós:** mais maduro do mercado; assets prontos; multiplataforma garantida.
- **Contras:** licenciamento pago acima de receita X; runtime fee polêmico; mais pesado.

**Recomendação inicial:** começar com **Godot 4**. UI do jogo é principalmente cards + ícones de habilidade — Godot dá conta com folga e mantém o projeto 100% gratuito.

---

## 2. Stack do servidor

Multiplayer turn-based com latência tolerante (não é FPS) — não precisa de servidor de tempo real ultra-otimizado.

### Recomendação

```
Cliente (Godot)
    ↓ WebSocket / HTTPS
API Gateway (Node.js + Fastify ou Go)
    ↓
┌─────────────┬──────────────┬──────────────┐
│ Match-maker │ Game Engine  │ Auth/Profile │
│ (Redis)     │ (autoritativo)│ (Postgres)   │
└─────────────┴──────────────┴──────────────┘
```

### Componentes

| Componente | Tecnologia sugerida | Motivo |
|---|---|---|
| Auth | Firebase Auth ou Supabase | Login com Google/Apple/email pronto |
| Banco principal | PostgreSQL | Perfis, inventário, ranking |
| Cache + matchmaking | Redis | Filas, Elo lookups, sessions |
| Game logic (autoritativo) | Node.js ou Go | Resolve turnos no servidor (anti-cheat) |
| Real-time | WebSockets | Push de turnos do oponente |
| Hosting | Fly.io, Railway, ou GCP Cloud Run | Auto-scale fácil |

### Por que **autoritativo no servidor**

O servidor calcula o resultado de cada turno e envia o estado canônico para os dois clientes. Cliente nunca decide dano — só renderiza. Isso impede trapaça (alteração de memória, mods).

---

## 3. Estrutura de dados (esboço)

```sql
-- Perfil
CREATE TABLE players (
  id UUID PRIMARY KEY,
  username TEXT UNIQUE,
  elo INT DEFAULT 1000,
  created_at TIMESTAMPTZ
);

-- Partida
CREATE TABLE matches (
  id UUID PRIMARY KEY,
  player_a UUID REFERENCES players,
  player_b UUID REFERENCES players,
  team_a JSONB,        -- ids dos 3 personagens
  team_b JSONB,
  state JSONB,         -- estado completo (HPs, cooldowns, status)
  current_turn INT,
  current_player UUID,
  winner UUID,
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ
);

-- Definição de personagem (carregada do client + validada no servidor)
-- Idealmente em arquivos YAML/JSON versionados no repositório,
-- não no banco — facilita balanceamento via PR.
```

Personagens e habilidades vivem em **arquivos JSON/YAML versionados** (`data/characters/*.yaml`), não no banco. Balanceamento vira pull request.

---

## 4. Estrutura de pastas (proposta para quando começar a codar)

```
app-game/
├── docs/                    # você está aqui
├── client/                  # projeto Godot
│   ├── project.godot
│   ├── scenes/
│   │   ├── menu/
│   │   ├── battle/
│   │   └── deckbuilder/
│   ├── scripts/
│   ├── assets/
│   └── data/                # mesmo data/ do servidor (symlink ou submódulo)
├── server/
│   ├── src/
│   │   ├── api/             # endpoints REST
│   │   ├── game/            # engine autoritativa de turnos
│   │   ├── matchmaking/
│   │   └── data/            # carrega personagens dos YAMLs
│   ├── tests/
│   └── package.json
├── data/                    # shared: definições de personagens e skills
│   ├── characters/
│   │   ├── grega/
│   │   ├── nordica/
│   │   ├── egipcia/
│   │   └── ...
│   └── schema.json
└── .github/workflows/       # CI: lint, testes, validação dos YAMLs
```

---

## 5. Diagrama de fluxo de uma partida

```
[Player A]                  [Server]                  [Player B]
    │                          │                          │
    ├── encontrar partida ────>│                          │
    │                          │<──── encontrar partida ──┤
    │                          │                          │
    │<───── match_found ───────┼──── match_found ────────>│
    │                          │                          │
    ├── ações do turno ───────>│                          │
    │                          │ (resolve turno)          │
    │<──── novo_estado ────────┼──── novo_estado ────────>│
    │                          │                          │
    │                          │<──── ações do turno ─────┤
    │<──── novo_estado ────────┼──── novo_estado ────────>│
    │             ...                                     │
```

---

## 6. Anti-cheat e validação

- Servidor é a única fonte da verdade. Cliente envia: "personagem X usou skill Y no alvo Z, paguei custo W".
- Servidor valida: cooldown? essência suficiente? alvo válido? personagem vivo? não atordoado?
- Se inválido → ignora ação (cliente "corrige" e exibe estado real).

---

## 7. Decisões em aberto

- [ ] 🔧 Engine: Godot vs Flutter+Flame?
- [ ] 🔧 Linguagem do backend: Node.js (TS) ou Go?
- [ ] 🔧 Hospedar onde? (Fly.io é mais barato; GCP é mais escalável)
- [ ] 🔧 Identidade visual / direção de arte (pixel art? cartoon? semi-realista?) — define muito o budget de assets.
