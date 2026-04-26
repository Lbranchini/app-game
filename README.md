# Ágora dos Mitos (nome provisório)

Jogo mobile (Android + iOS) de batalhas estratégicas por turnos 3v3, com **personagens clássicos da história e das mitologias mundiais** (grega, nórdica, egípcia, japonesa, asteca, africana, mesopotâmica, britânica e mais).

## Pitch em uma frase

> Xadrez com superpoderes: monte uma equipe de 3 lendas, gerencie energia e cooldowns, e duele contra outros jogadores em partidas de 8–12 minutos.

## Decisões fechadas

| Item | Decisão |
|---|---|
| Cliente | **Godot 4** (2D, exporta Android + iOS, grátis) |
| Backend | **Python 3.12 + FastAPI** |
| Banco | PostgreSQL 16 + Redis |
| Direção de arte | **Cartoon 2D** (paleta vibrante, contornos claros, expressivo) |
| Roster MVP | **16 personagens** (10 mitologias diferentes) |
| Modelo | Free-to-play, monetização por cosméticos e expansões temáticas (sem pay-to-win) |
| Escopo MVP | Apenas batalhas (sem modo carreira, sem narrativa, sem hub) |

## Sobre direitos autorais

**Mecânicas de jogo** (turnos, custos de essência, cooldowns, formação 3v3, status effects) são padrão do gênero turn-based tático e não são protegidas por copyright — podem ser livremente usadas.

**Personagens, nomes e habilidades** são desenhados do zero usando figuras de **domínio público** (mitologia e história antiga). Nenhum kit é cópia de personagem identificável de outra obra protegida — todos os 16 são desenhos originais que ocupam arquétipos clássicos do gênero.

## Estrutura da documentação

| Arquivo | Conteúdo |
|---|---|
| [`docs/01-visao-geral.md`](docs/01-visao-geral.md) | Visão de produto, público-alvo, diferencial |
| [`docs/02-mecanicas-de-jogo.md`](docs/02-mecanicas-de-jogo.md) | Sistema de turnos, essências, tipos de habilidade, status |
| [`docs/03-arquitetura-tecnica.md`](docs/03-arquitetura-tecnica.md) | Godot + FastAPI + Postgres + Redis |
| [`docs/04-roadmap.md`](docs/04-roadmap.md) | Fases de MVP até v1.0 |
| [`docs/05-personagens-iniciais.md`](docs/05-personagens-iniciais.md) | Roster de 16 personagens com kits completos |
| [`docs/06-balanceamento.md`](docs/06-balanceamento.md) | Filosofia de balanceamento, arquétipos de equipe |
| [`docs/07-glossario.md`](docs/07-glossario.md) | Termos técnicos do jogo |

## Status

📋 **Fase atual:** Pré-produção (planejamento). Próximo passo: aprovar este planejamento e escrever os 16 YAMLs de personagens antes de começar a Fase 1 (engine de regras em Python).
