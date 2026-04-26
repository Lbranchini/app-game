# Server — Engine + API (Python)

Engine determinística de regras + API (FastAPI virá em fase posterior).

## Setup

```bash
cd server
pip install -e ".[dev]"
```

## Rodar testes

```bash
pytest
```

## Rodar simulação bot vs bot

```bash
agora-sim                  # 1 partida com seed 42
agora-sim --seed 7         # seed específica
agora-sim --runs 100       # 100 partidas, mostra estatísticas
agora-sim --quiet          # só o resultado
```

## Estrutura

```
src/agora/
├── schemas.py          # Pydantic v2: Personagem, Habilidade, MatchState, Action, Event
├── data_loader.py      # Carrega YAMLs de data/characters/
├── game/
│   ├── engine.py       # resolve_turn, start_match
│   └── rng.py          # SeededRng (replay determinístico)
└── cli.py              # bot vs bot

tests/
├── conftest.py         # fixtures de personagens
├── test_data_loader.py
├── test_engine_basico.py
└── test_status_effects.py
```

## Status atual (slice vertical)

- ✅ 3 personagens jogáveis: Aquiles, Atena, Anúbis (cobrem damage físico, suporte, DoT)
- ✅ 15 testes passando
- ✅ Engine: dano, cura, cooldowns, custos, alternância de jogador, geração de essência, win condition
- ✅ Status: veneno (DoT), redução de dano, escudo destrutível, buff de dano, invulnerável, perfurante
- ✅ CLI bot vs bot funcional

## Próximos (fora deste slice)

- 13 personagens restantes do roster MVP
- Status faltantes: stun, silenciado, drenado, sangramento (versão proporcional ao dano), regeneração, marcado, vulnerável, refletivo, furtivo
- Mais tipos de efeito: drena_essencia (tem implementação parcial), copia, reflect, counter
- API FastAPI por cima da engine
- Persistência (PostgreSQL + Redis)
