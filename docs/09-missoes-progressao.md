# 09 — Missões e Progressão (Desbloqueio de Personagens)

> Sistema de progressão estilo "career mode" turn-based: alguns personagens vêm liberados desde o primeiro login, outros são desbloqueados completando **missões** que incentivam o jogador a experimentar mecânicas e arquétipos diferentes.

---

## 1. Princípios

1. **Onboarding suave.** Roster inicial cobre **todos** os arquétipos básicos — o jogador novo nunca sente que precisa pagar para ter variedade.
2. **Missões ensinam o jogo.** Cada missão expõe o jogador a uma mecânica (stun, cura, drain, AOE...) que ele talvez não usasse espontaneamente.
3. **Sem pay-to-skip.** Personagens desbloqueáveis **só** se obtêm jogando. Cosméticos podem ser comprados; personagens não.
4. **Tempo razoável.** Cada personagem deve desbloquear em 10–30 partidas para um jogador que foca nele. Sem grind absurdo.
5. **Missões são acumulativas.** Progresso conta entre partidas. Nada é "tudo ou nada" numa única partida (exceto missões expressamente marcadas como "feito x").

---

## 2. Roster: liberados vs desbloqueáveis

### Liberados desde o login (8 personagens)

Cobrem todos os 8 arquétipos clássicos. Permitem montar qualquer comp básica.

| Personagem | Arquétipo |
|---|---|
| Aquiles | Burst físico |
| Atena | Suporte/buff defensivo |
| Thor | AOE |
| Anúbis | DoT |
| Ísis | Healer |
| Anansi | Stun |
| Joana d'Arc | Tank |
| Loki | Trick/cópia |

### Desbloqueáveis via missões (8 personagens)

São **variantes especializadas** dos arquétipos básicos — funcionam como upgrade lateral, não vertical (não são "melhores", são diferentes).

| Personagem | Arquétipo (variante) | Especialidade que adiciona |
|---|---|---|
| Medusa | Stun longo | Disable de 3 turnos com restrição |
| Sun Wukong | Multi-ataque | Acertar múltiplos alvos ou múltiplas vezes |
| Mulan | Burst furtivo | Combo de furtividade + perfurante |
| Amaterasu | Wall + buff | Invulnerabilidade da equipe inteira |
| Quetzalcóatl | Drainer | Negação de essência |
| Inanna | Híbrido | Dual cura+dano |
| Cleópatra | Controle de comportamento | Charme / redirect de ataque |
| Rei Arthur | Leader | Buffs com escala em equipe inteira |

---

## 3. Estrutura de missão

Cada personagem desbloqueável tem **3 missões**. Precisa completar **todas as 3** para desbloquear.

```yaml
# data/missions/medusa.yaml
character_unlock: medusa
missions:
  - id: medusa_1
    titulo: "O olhar paralisa"
    descricao: "Atordoe 50 inimigos ao longo da sua carreira."
    contador: status_aplicado.atordoado
    meta: 50
  - id: medusa_2
    titulo: "Sabedoria táctica"
    descricao: "Vença 10 partidas usando Atena na equipe."
    contador: vitorias_com.atena
    meta: 10
  - id: medusa_3
    titulo: "Silêncio absoluto"
    descricao: "Vença 5 partidas em que nenhum inimigo usou ultimate."
    contador: vitorias_com_condicao.nenhum_ultimate_inimigo
    meta: 5
```

### Tipos de contador suportados

| Tipo | Exemplo | Como incrementa |
|---|---|---|
| `cumulativo_simples` | `dano_total_causado` | +N a cada acerto |
| `evento_contado` | `status_aplicado.veneno` | +1 cada vez que aplica |
| `vitorias_com.<personagem>` | `vitorias_com.aquiles` | +1 a cada vitória com Aquiles em campo |
| `vitorias_com_condicao.<cond>` | `comp_so_vigor` | +1 ao vencer com a condição satisfeita |
| `marcos_unicos` | `desbloqueio_inanna` | binário (feito ou não) |

Contadores ficam no `players.progress` (JSONB) ou em tabela própria `player_counters` (decisão na Fase 1).

---

## 4. Catálogo completo de missões

### Medusa — Disable longo

1. **O olhar paralisa** — Atordoe 50 inimigos.
2. **Sabedoria táctica** — Vença 10 partidas com Atena na equipe.
3. **Silêncio absoluto** — Vença 5 partidas onde nenhum inimigo usou ultimate.

### Sun Wukong — Multi-ataque

1. **Bastão incansável** — Acerte 200 habilidades básicas.
2. **Punhos do Olimpo** — Cause 5.000 de dano físico cumulativo.
3. **Time guerreiro** — Vença 10 partidas com uma comp 100% essência Vigor.

### Mulan — Burst furtivo

1. **Primeiro golpe** — Cause 3.000 de dano em "primeiros ataques" do turno (primeira habilidade resolvida).
2. **Vitória relâmpago** — Vença 5 partidas em ≤ 8 turnos.
3. **Eliminação cirúrgica** — Derrote 25 inimigos com habilidades perfurantes.

### Amaterasu — Wall + buff

1. **Cuidado dos seus** — Cure 2.000 HP totais com Ísis.
2. **Equipe intacta** — Vença 5 partidas em que nenhum aliado morreu.
3. **Sol nascente** — Aplique buffs em aliados 100 vezes.

### Quetzalcóatl — Drainer

1. **Ladrão de mistérios** — Drene 200 essências de oponentes.
2. **Mestre do engano** — Vença 10 partidas com Loki na equipe.
3. **Asfixia táctica** — Vença 5 partidas em que o oponente terminou pelo menos 1 turno com 0 essências.

### Inanna — Híbrido

1. **A balança** — Cause 2.000 de dano **e** cure 2.000 HP cumulativamente.
2. **Bênção dupla** — Vença 10 partidas com Ísis na equipe.
3. **Comp equilibrada** — Vença 5 partidas com comp de 1 healer + 2 damage dealers.

### Cleópatra — Controle de comportamento

1. **Manipuladora** — Use habilidades de stun/charme/silêncio 50 vezes.
2. **Defensa perfeita** — Vença 5 partidas em que o ultimate do oponente nunca acertou um aliado seu.
3. **Tecedora de cordas** — Vença 10 partidas com Anansi na equipe.

### Rei Arthur — Leader

1. **Veterano da Ágora** — Vença 25 partidas (qualquer comp).
2. **Mesa redonda** — Vença 10 partidas em que todos os 3 personagens sobreviveram.
3. **Cavalheiresco** — Atinja Elo 1300+.

---

## 5. UI proposta (esboço)

```
┌─────────────────────────────────────────┐
│  PERSONAGENS                            │
├─────────────────────────────────────────┤
│  Disponíveis (8/16)                     │
│  [Aquiles][Atena][Thor][Anúbis]...      │
│                                         │
│  Bloqueados                             │
│  ┌──────────────────────────────────┐   │
│  │ 🔒 MEDUSA                        │   │
│  │  ▰▰▰▱▱  Atordoar 50 (32/50)      │   │
│  │  ▰▰▰▰▰  Vencer com Atena (10/10) │   │
│  │  ▰▰▱▱▱  Sem ultimates (2/5)      │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │ 🔒 SUN WUKONG                    │   │
│  │  ...                             │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

Notificação tipo "achievement unlocked" quando completa as 3.

---

## 6. Implementação no servidor

### Fluxo por partida

```
1. Partida termina (servidor já sabe vencedor + estado final)
2. Coletor de telemetria gera evento:
   {
     match_id, player_id,
     dano_causado: 2150,
     status_aplicados: { atordoado: 3, veneno: 8 },
     personagens_em_campo: [aquiles, atena, anansi],
     personagens_aliados_sobreviventes: 3,
     resultado: vitoria,
     turnos: 11,
     ...
   }
3. MissionService recebe evento e:
   - Incrementa contadores correspondentes em players.progress
   - Para cada personagem bloqueado, checa se as 3 missões batem
   - Se sim, marca personagem como desbloqueado e emite evento
4. Cliente recebe estado novo + push notification "Você desbloqueou X!"
```

### Modelo de dados

```sql
ALTER TABLE players ADD COLUMN unlocked_characters JSONB
  NOT NULL DEFAULT '["aquiles","atena","thor","anubis","isis","anansi","joana","loki"]';

ALTER TABLE players ADD COLUMN progress JSONB NOT NULL DEFAULT '{}';
-- ex: {"dano_total_causado": 14230, "status_aplicado.atordoado": 32, ...}
```

Mantemos contadores em JSONB por simplicidade no MVP. Migra para tabela dedicada se a query ficar lenta (dificilmente acontece — read-on-event, não query intensiva).

### Onde rodar

`MissionService` é um módulo Python puro, chamado **após** a engine resolver o último turno. Não bloqueia o cliente — pode rodar em worker `arq` se ficar pesado.

---

## 7. Trade-offs e decisões

- **Por que 3 missões por personagem (não 1, não 5)?** 1 vira grind tedioso. 5+ vira barreira longa demais. 3 dá variedade sem desencorajar.
- **Por que não missões diárias rotativas no MVP?** Adiciona complexidade (refresh, estado por dia) sem ganho central. Fica para v0.5.
- **E se o jogador quiser pular?** Nenhum atalho pago no MVP. Pode-se considerar "ficha de desbloqueio" via Battle Pass futuro (cosmético + 1 ficha por temporada), mas **nunca** venda direta de personagem.
- **Personagens novos pós-MVP**: cada um vem com seu próprio set de 3 missões temáticas.

---

## 8. Impacto no roadmap

Adiciona **+1 a +2 semanas** na Fase 3 (Multiplayer + conta):
- Schema de progresso e personagens desbloqueados
- MissionService + telemetria de partida
- UI de missões (tela "Personagens" com progress bars)

Sem impacto na Fase 1 (engine de regras) ou Fase 2 (cliente local — nessa fase, todos os 16 ficam liberados para teste).
