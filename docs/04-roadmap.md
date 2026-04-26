# 04 — Roadmap

> Estimativas presumem 1 dev em tempo parcial. Multiplique/divida conforme o time real.

---

## Fase 0 — Pré-produção (2–3 semanas)

**Objetivo:** validar o conceito antes de escrever código.

- [ ] Aprovar este planejamento.
- [ ] Decisões em aberto remanescentes (hosting, i18n).
- [ ] Mood board cartoon: paleta, peso de contorno, estilo de animação (referências: Hades 2D, Slay the Spire, Cult of the Lamb).
- [ ] Prototipar **em papel** uma partida completa: imprimir 6 cards de personagem com habilidades e jogar contra você mesmo. Identificar furos de regra antes de codar.
- [ ] Setup do repositório: CI básico, linter, formatter, regras de PR.

**Entregável:** documento único "Game Design Document v1" (este `/docs` consolidado) + protótipo de papel jogável.

---

## Fase 1 — Engine de regras (4–6 semanas)

**Objetivo:** servidor Python autoritativo que resolve partidas via API, sem UI.

- [ ] Setup do projeto FastAPI + uv + ruff + mypy + pytest.
- [ ] Schema YAML dos 16 personagens (validado por Pydantic v2).
- [ ] Loader: carrega `data/characters/*.yaml` no boot.
- [ ] Engine de turnos (módulo Python puro): estado da partida, fila de ações, resolução, cooldowns, status.
- [ ] Suite de testes unitários cobrindo:
  - Cada tipo de habilidade (instantânea, ação, controle).
  - Cada status effect.
  - Casos de prioridade (esquiva antes de ataque, reflect antes de heal, etc.).
- [ ] CLI para simular partida 3v3 entre dois bots determinísticos.

**Entregável:** `pytest` verde com ≥ 80% coverage. CLI roda partida ponta-a-ponta em < 1s.

---

## Fase 2 — Cliente jogável local (4–6 semanas)

**Objetivo:** UI que joga uma partida contra IA simples.

- [ ] Tela principal (logo + botão "Jogar").
- [ ] Tela de seleção de equipe (3 personagens dos 16 do MVP).
- [ ] Tela de batalha: HUD de essências, painel de personagens, painel de habilidades, fila, botão "PRONTO".
- [ ] Animações básicas (placeholder ok): ataque, dano, cura, status.
- [ ] IA "burra" (escolhe ação aleatória válida).
- [ ] Build APK e IPA testados em dispositivo real.

**Entregável:** APK instalável que joga 1 partida 3v3 vs IA do início ao fim.

---

## Fase 3 — Multiplayer + conta (4–6 semanas)

**Objetivo:** PvP funcional.

- [ ] Auth (Google + Apple Sign-in).
- [ ] Matchmaking (fila simples por Elo).
- [ ] WebSocket cliente↔servidor.
- [ ] Sincronização de estado autoritativa.
- [ ] Tratamento de desconexão (timeout 60s → derrota).
- [ ] Telemetria básica (tempo de partida, ações por turno, taxa de desistência).

**Entregável:** beta fechado com 20 amigos jogando partidas reais.

---

## Fase 4 — Conteúdo + Polimento (6–8 semanas)

- [ ] Roster de 16 → 20 personagens (4 novos: cobrir mitologias menos representadas).
- [ ] Balanceamento: 3 rodadas de playtest, ajustes via PR.
- [ ] Animações reais (artista contratado ou asset pack).
- [ ] Áudio: música ambiente + SFX por habilidade.
- [ ] Efeitos visuais (partículas).
- [ ] Tela de progressão/perfil.
- [ ] Localização: PT-BR + EN.

**Entregável:** v0.9, qualidade de soft-launch.

---

## Fase 5 — Lançamento (4 semanas)

- [ ] Stores: Google Play (taxa 25 USD), App Store (99 USD/ano).
- [ ] Política de privacidade + termos.
- [ ] LGPD/GDPR compliance.
- [ ] Página de lançamento (landing page simples).
- [ ] Plano de marketing inicial (Reddit, TikTok, Discord de mitologia/games táticos).

**Entregável:** v1.0 nas lojas.

---

## Pós-lançamento (contínuo)

- Patches de balanceamento mensais.
- 1 personagem novo a cada 2 semanas.
- Eventos sazonais (Halloween → mitologia celta; Carnaval → orixás; etc.).
- Battle Pass trimestral.

---

## Não-objetivos do MVP (cortes deliberados)

Tudo abaixo fica para **depois** da v1.0. Não tentar fazer no MVP:

- Modo guilda/clã.
- Chat in-game.
- Replays.
- Espectador.
- Cosméticos.
- Web client.
- Modo PvE / campanha.
- Voice acting.

Lembrete: **escopo curto entrega**. Escopo grande não entrega.
