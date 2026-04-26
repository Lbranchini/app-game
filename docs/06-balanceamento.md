# 06 — Filosofia de Balanceamento

## Princípios

1. **Tudo tem counter.** Nenhuma estratégia deve ser inderrotável. Toda comp dominante precisa ter pelo menos 2 contra-comps documentadas.
2. **Habilidades fortes têm custo claro.** Alto dano → alto custo de essência ou alto cooldown.
3. **Nerf por número, não por mecânica.** Ajustar valores (dano, cooldown, custo) é seguro. Mudar como uma habilidade funciona quebra muscle memory dos jogadores.
4. **Personagens icônicos não viram lixo.** Se Thor é fraco demais, sobe ele em vez de tirá-lo do meta.
5. **Diversidade > poder.** Meta com 5 comps viáveis > meta com 1 comp dominante.

---

## Arquétipos de equipe esperados

(Inspirados nos arquétipos clássicos de jogos 3v3 de turnos.)

| Arquétipo | Conceito | Exemplos no roster MVP |
|---|---|---|
| **Damage Reduction** | Sobreviver muito, ganhar no longo prazo | Joana + Atena + Ísis |
| **AOE** | Quebrar o oponente em todas as frentes | Thor + Anansi + Anúbis |
| **Burst foco** | Focar 1 alvo e matar antes que reaja | Aquiles + Sun Wukong + Atena |
| **Drain/Control** | Negar essência e turnos do oponente | Quetzalcóatl + Anansi + Loki |
| **DoT/Veneno** | Matar lentamente sem precisar acertar muito | Anúbis + Aquiles + Ísis |
| **Wall** | Invulnerabilidade rotacional | Amaterasu + Joana + Atena |
| **Trick/Reflect** | Devolver as habilidades do oponente | Loki + Cleópatra + Atena |
| **Mixed** | Sem comp clara, máxima flexibilidade | Qualquer combinação |

Triângulo geral: **Burst > Wall > Drain > Burst** (cíclico). Damage Reduction quebra DoT. AOE quebra Wall.

---

## Métricas de balanceamento

Coletadas via telemetria e revisadas a cada patch:

| Métrica | Saudável | Atenção | Crítico |
|---|---|---|---|
| Pick rate de personagem | 5–25% | <2% ou >40% | <1% ou >60% |
| Win rate de personagem | 47–53% | <44% ou >56% | <40% ou >60% |
| Win rate de comp | 45–55% | <40% ou >60% | <35% ou >65% |
| Duração média | 8–12 min | 5–8 ou 12–18 | <5 ou >18 |

---

## Processo de patch

1. **Coletar dados** das últimas 2 semanas (mínimo 5.000 partidas por personagem).
2. **Identificar outliers** (fora dos limites "atenção/crítico").
3. **Propor mudanças** via PR no `data/characters/*.yaml`. Diff fica no Git.
4. **Playtest interno** (1 sessão de 2h com o time + amigos beta).
5. **Patch notes públicos** explicando o "porquê" de cada mudança.
6. **Deploy + monitorar 1 semana** antes do próximo patch.

---

## Anti-patterns a evitar

- ❌ "Buff todo mundo" para resolver dominância de 1 personagem (power creep).
- ❌ Mudar mecânica fundamental de um personagem sem aviso prévio.
- ❌ Lançar personagem novo OP de propósito para vender (paywall via balanceamento).
- ❌ Ignorar feedback qualitativo do Discord/Reddit em favor só de números.
- ❌ "Hotfix" emergencial sem playtest — quase sempre piora.
