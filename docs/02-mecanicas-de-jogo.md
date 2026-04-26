# 02 — Mecânicas de Jogo

> Documento técnico das regras. Inspirado nas mecânicas de Naruto Arena (que **não** são protegidas por copyright). Adaptado para nosso tema mitológico com nomenclatura própria.

---

## 1. Estrutura geral da partida

- **Formato:** 3v3, turnos alternados, PvP assíncrono ou em tempo real.
- **Vitória:** zerar os 3 personagens do oponente (HP ≤ 0).
- **Limite:** 60 turnos por partida (após isso, vence quem tiver mais HP total; em empate, vitória do defensor).
- **HP base por personagem:** 100 (varia +/- por arquétipo).

### Fluxo de um turno

```
1. Início do turno
   ├── Cooldowns dos personagens vivos diminuem em 1
   ├── Efeitos de duração tickam (DoT, HoT, buffs)
   └── Jogador recebe N essências aleatórias (N = nº de personagens vivos)

2. Fase de planejamento
   ├── Selecionar habilidade de cada personagem (1 por personagem)
   ├── Escolher alvo (inimigo, aliado, ou self)
   ├── Pagar custo de essência
   └── Reordenar fila de execução (drag-and-drop)

3. Confirmar (botão "PRONTO")
   └── Se não confirmar em 60s, turno passa em branco

4. Resolução
   ├── Habilidades resolvem na ordem da fila
   ├── Animações + cálculos
   └── Aplicação de novos status

5. Fim do turno → vez do oponente
```

---

## 2. Sistema de Essência (energia)

Substitui o "chakra" do Naruto Arena.

### 4 tipos de essência

| Tipo | Cor | Tema | Análogo |
|---|---|---|---|
| **Vigor** | Vermelho | Força física, combate corpo-a-corpo | Taijutsu |
| **Espírito** | Azul | Magia arcana, controle elemental | Ninjutsu |
| **Mente** | Branco | Ilusão, manipulação, conhecimento | Genjutsu |
| **Sangue** | Verde | Linhagem divina, transformação, dons inatos | Bloodline |

### Geração

- A cada início de turno você recebe **1 essência aleatória por personagem vivo** (3 no início, menos conforme perde personagens).
- **Exceção:** quem joga primeiro recebe apenas **1 essência** no turno 1; quem joga segundo recebe **3** (compensa a desvantagem de iniciativa).
- Essência **acumula** entre turnos (sem teto explícito; teto sugerido: 30 para evitar abuso).

### Custo das habilidades

- Cada habilidade exige um custo, ex: `2 Vigor + 1 Genérica`.
- **Genérica** = qualquer cor (você decide qual gastar).
- **Trocar essência:** gaste **5 essências quaisquer** para receber **1 da cor escolhida** (limite 1 troca por turno; alivia a aleatoriedade).

---

## 3. Habilidades

Cada personagem tem **4 slots de habilidade**:

1. **Habilidade básica** (custo 0–1, sem cooldown ou cooldown ≤ 1)
2. **Habilidade secundária** (custo médio, cooldown 2–3)
3. **Habilidade ultimate** (custo alto, cooldown 4–6)
4. **Esquiva** (defesa universal: invulnerável por 1 turno, custo 1 genérica, cooldown 4 — todos os personagens têm)

### Tipos de execução

| Tipo | Comportamento |
|---|---|
| **Instantânea** | Resolve no turno; sem vínculo posterior com o usuário. Não é cancelada se o usuário for atordoado depois. |
| **Ação contínua** | Dura N turnos. Se o usuário for atordoado, o efeito **pausa** e retoma quando ele se recupera. Se o alvo ficar invulnerável, a habilidade **não atinge** durante a invulnerabilidade mas continua depois. |
| **Controle** | Como Ação, mas **quebra** se o vínculo entre usuário e alvo for rompido (atordoamento, morte, invulnerabilidade do alvo). Útil para "agarrar" inimigos. |

### Categorias de alvo

- **Inimigo único**
- **Todos inimigos** (AOE)
- **Aliado único**
- **Todos aliados**
- **Si mesmo**
- **Aleatório** (raro, geralmente em ultimates de alto risco/recompensa)

### Tags secundárias

- **Físico** vs **Mágico** (interage com reduções específicas)
- **Corpo-a-corpo** vs **À distância** (algumas defesas só bloqueiam um tipo)
- **Único** (não pode ser usado mais de uma vez na partida — só ultimates épicas)

---

## 4. Status effects (efeitos)

### Negativos (Aflição)

| Efeito | O que faz |
|---|---|
| **Atordoado** | Não pode usar habilidades nem esquiva. Habilidades-Ação suas pausam. |
| **Silenciado** | Não pode usar habilidades **mágicas** (spell-only block). |
| **Desarmado** | Não pode usar habilidades **físicas**. |
| **Veneno (DoT)** | Sofre X de dano no início de cada turno por N turnos. |
| **Sangramento** | Sofre dano proporcional ao dano que **causou** no último turno. |
| **Drenado** | No início do turno seu time perde 1 essência aleatória. |
| **Marcado** | Sofre +X% de dano de fontes específicas. |
| **Vulnerável** | Não pode ficar invulnerável nem reduzir dano. |

### Positivos (Bênção)

| Efeito | O que faz |
|---|---|
| **Invulnerável** | Imune a habilidades inimigas direcionadas (geralmente 1 turno). |
| **Redução de dano** | Recebe X menos de dano de cada acerto. |
| **Defesa destrutível** | Escudo de Y HP que absorve dano até quebrar. |
| **Regeneração (HoT)** | Cura X HP por turno por N turnos. |
| **Furtivo** | Inimigos não podem alvejá-lo até ele atacar. |
| **Refletivo** | Próxima habilidade inimiga é devolvida ao lançador. |

### Modificadores especiais

- **Perfurante** — ignora redução de dano e defesa destrutível.
- **Verdadeiro** — ignora invulnerabilidade.
- **Inevitável** — ignora esquivas e reflexões.
- **Cópia** — usuário copia a habilidade do alvo para uso próprio.

---

## 5. Personagens — anatomia

```yaml
id: aquiles
nome: Aquiles
mitologia: Grega
arquetipo: Damage Dealer (corpo-a-corpo)
hp_base: 110
habilidades:
  - id: lanca_ferida
    nome: "Lança que Fere"
    custo: { vigor: 1 }
    cooldown: 0
    tipo: instantânea
    alvo: inimigo_unico
    efeito: "Causa 20 de dano físico."
  - id: investida_mirmidao
    nome: "Investida Mirmidão"
    custo: { vigor: 2 }
    cooldown: 2
    tipo: instantânea
    alvo: inimigo_unico
    efeito: "Causa 35 de dano físico. Aplica Sangramento (2 turnos)."
  - id: furia_de_pelida
    nome: "Fúria de Pélida"
    custo: { vigor: 2, generica: 1 }
    cooldown: 4
    tipo: ação_contínua
    duracao: 3
    alvo: si_mesmo
    efeito: "Por 3 turnos, ataques de Aquiles ganham +15 dano e ele recebe -10 dano. Calcanhar exposto: vulnerável a perfurante."
  - id: esquiva
    nome: "Esquivar"
    custo: { generica: 1 }
    cooldown: 4
    tipo: instantânea
    alvo: si_mesmo
    efeito: "Invulnerável por 1 turno."
```

---

## 6. Resolução de prioridade

A ordem de execução das habilidades **importa**. Por padrão, segue a ordem da fila do jogador atual, com regras de prioridade:

1. **Reflexões e contras** ativam **antes** das habilidades que respondem.
2. **Invulnerabilidades e defesas** aplicam-se **antes** dos ataques do mesmo turno.
3. **Curas** resolvem **depois** dos ataques (para não desperdiçar HP).
4. Dentro de cada categoria, segue a ordem manual do jogador.

---

## 7. Modos de jogo (planejados)

| Modo | Descrição | Fase |
|---|---|---|
| **Treinamento** | Vs IA, sem ranking. | MVP |
| **Ranqueada** | PvP com Elo. | MVP |
| **Casual** | PvP sem Elo. | v0.5 |
| **Missões diárias** | Ex: "Ganhe 3 partidas com personagem grego". | v0.5 |
| **Torneios sazonais** | Brackets fixos com prêmios cosméticos. | v1.0 |
| **Co-op 3v3v3** | Dois times contra IA chefe. | v1.5 |

---

## 8. Pontos abertos / decisões pendentes

- [ ] Tempo limite por turno: 45s ou 60s?
- [ ] Permitir reconexão em partida ranqueada?
- [ ] Sistema de banimento de personagens em ranqueada (estilo MOBA)?
- [ ] Quantidade de personagens no MVP: 12 (sugerido) ou 16?
