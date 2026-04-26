# 05 — Roster Inicial (12 personagens do MVP)

> Todos figuras de **domínio público** (mitologia ou história antiga). Habilidades são originais, inspiradas nos mitos. Spread proposital de mitologias para apelo global e cobertura de arquétipos.

| # | Personagem | Origem | Arquétipo | Tipo principal de essência |
|---|---|---|---|---|
| 1 | Aquiles | Grécia | Damage físico (calcanhar = vulnerabilidade interessante) | Vigor |
| 2 | Atena | Grécia | Suporte/buff defensivo | Mente |
| 3 | Thor | Nórdica | AOE / burst | Espírito |
| 4 | Loki | Nórdica | Controle / cópia / reflect | Mente |
| 5 | Anúbis | Egípcia | Damage over time / debuff de morte | Sangue |
| 6 | Ísis | Egípcia | Healer principal | Espírito |
| 7 | Sun Wukong | Chinesa | Mobilidade / multi-ataque | Sangue |
| 8 | Amaterasu | Japonesa | Buffs de dano / wall (escudo) | Espírito |
| 9 | Quetzalcóatl | Asteca | Drainer (rouba essência) | Mente |
| 10 | Anansi | Africana (Akan) | Stunner / armadilhas | Mente |
| 11 | Joana d'Arc | Histórica | Tank / damage reduction de equipe | Vigor |
| 12 | Cleópatra | Histórica | Charme/controle (transferir alvo de ataque) | Mente |

---

## Cobertura de arquétipos no MVP

| Arquétipo | Personagens |
|---|---|
| Damage burst | Aquiles, Thor |
| DoT/sangramento | Anúbis, Aquiles (sangramento) |
| Healer | Ísis |
| Tank/redução | Joana d'Arc, Amaterasu |
| Controle (stun) | Anansi, Cleópatra |
| Drainer | Quetzalcóatl |
| Reflect/cópia | Loki |
| Multi-ataque | Sun Wukong |
| Suporte/buff | Atena, Amaterasu |

Permite **vários arquétipos de equipe** (ver `06-balanceamento.md`) sem inflar o roster cedo demais.

---

## Especificação completa — exemplo (Aquiles)

```yaml
id: aquiles
nome: Aquiles
mitologia: Grega
arquetipo: damage_dealer
hp_base: 110
descricao: |
  Maior guerreiro grego da Guerra de Troia. Quase invencível em combate,
  mas seu calcanhar é seu único ponto fraco.

habilidades:
  - id: lanca
    nome: "Lança Mortal"
    tipo: instantânea
    custo: { vigor: 1 }
    cooldown: 0
    alvo: inimigo_unico
    efeito:
      - { tipo: dano, valor: 20, classe: físico }

  - id: investida
    nome: "Carga dos Mirmidões"
    tipo: instantânea
    custo: { vigor: 2 }
    cooldown: 2
    alvo: inimigo_unico
    efeito:
      - { tipo: dano, valor: 35, classe: físico }
      - { tipo: status, status: sangramento, duracao: 2, valor: 10 }

  - id: furia
    nome: "Fúria de Pélida"
    tipo: ação_contínua
    custo: { vigor: 2, generica: 1 }
    cooldown: 4
    duracao: 3
    alvo: si_mesmo
    efeito:
      - { tipo: buff_dano, valor: 15, duracao: 3 }
      - { tipo: reducao_dano, valor: 10, duracao: 3 }
      - { tipo: status, status: vulneravel_perfurante, duracao: 3 }
        # downside flavorful: o calcanhar fica exposto

  - id: esquiva
    nome: "Esquivar"
    tipo: instantânea
    custo: { generica: 1 }
    cooldown: 4
    alvo: si_mesmo
    efeito:
      - { tipo: invulneravel, duracao: 1 }
```

---

## Especificação resumida — outros 11

> Os 11 abaixo precisam de YAMLs completos como o do Aquiles antes do começo da Fase 1. Aqui ficam só as ideias-chave.

### Atena
- Dom: dar **redução de dano + 1 essência Mente** a um aliado.
- Ultimate: **Égide** — equipe inteira ganha defesa destrutível por 2 turnos.

### Thor
- Burst: **Mjolnir** — 30 de dano em 1 alvo + chance de stun 1 turno.
- Ultimate: **Tempestade** — 25 AOE, ignora redução de dano.

### Loki
- Truque: **Cópia** — copia próxima habilidade lançada num aliado seu.
- Ultimate: **Engano** — todos ataques inimigos no próximo turno são redirecionados ao próprio lançador.

### Anúbis
- Aplica **veneno (15 dano/turno por 3 turnos)**.
- Ultimate: **Julgamento** — se o alvo está com veneno, dano é dobrado e remove regenerações.

### Ísis
- Cura: 25 HP num aliado.
- Ultimate: **Ressureição parcial** — restaura 50 HP ao aliado de menor HP, remove afflictions.

### Sun Wukong
- Multi-ataque: 3 acertos de 12 (clones).
- Ultimate: **Transformação** — fica furtivo e próximo ataque causa dano triplo.

### Amaterasu
- Buff: **Luz solar** — aliado ganha +20% dano por 2 turnos.
- Ultimate: **Cubrir-se na caverna** — equipe invulnerável por 1 turno (custo altíssimo).

### Quetzalcóatl
- Drena 2 essências aleatórias do oponente.
- Ultimate: **Vento Sagrado** — nenhum inimigo gera essência no próximo turno.

### Anansi
- Stun: 1 alvo atordoado por 1 turno.
- Ultimate: **Teia de mentiras** — todos inimigos atordoados por 1 turno (custo alto, cooldown 6).

### Joana d'Arc
- Tank: redução de dano para si + 1 aliado por 2 turnos.
- Ultimate: **Estandarte sagrado** — próximo turno toda dano contra equipe é -50%.

### Cleópatra
- Charme: alvo inimigo ataca aliado dele no próximo turno.
- Ultimate: **Aliança egípcia** — rouba o controle de 1 inimigo por 1 turno (ele usa habilidade básica em outro inimigo).

---

## Princípios para criar novos personagens (após MVP)

1. **Fidelidade ao mito** acima de "balanceamento perfeito" — character first.
2. Cada personagem deve ter **1 fraqueza clara** (Aquiles → calcanhar; Sun Wukong → vulnerável quando não em transformação).
3. Toda nova habilidade deve poder ser explicada em **1 frase**.
4. **Não** adicionar mecânicas novas só para 1 personagem. Reusar o vocabulário existente.
5. Spread cultural: cada wave de 4 personagens deve cobrir ≥ 3 mitologias diferentes.
