# 05 — Roster Inicial (16 personagens do MVP)

> Todos figuras de **domínio público** (mitologia ou história antiga). Habilidades são **originais**, projetadas para preencher arquétipos clássicos do gênero turn-based 3v3 (burst, healer, tank, stunner, drainer, trick, etc.) usando o vocabulário mecânico de [`02-mecanicas-de-jogo.md`](02-mecanicas-de-jogo.md).
>
> **Sobre "copiar 1:1 de outro jogo":** kits 100% idênticos a personagens identificáveis de jogos protegidos (Naruto Arena, Soul Arena, etc.) configuram **obra derivada** mesmo com renomeação. Os 16 abaixo cobrem os mesmos arquétipos estratégicos (e portanto produzem profundidade tática equivalente) sem espelhar nenhum kit específico de outra obra.

---

## Roster

| # | Personagem | Origem | Arquétipo | Essência principal |
|---|---|---|---|---|
| 1 | Aquiles | Grécia | Burst físico (com fraqueza única: calcanhar) | Vigor |
| 2 | Atena | Grécia | Suporte defensivo + buffs táticos | Mente |
| 3 | Medusa | Grécia | Disable longo (petrificação) | Mente |
| 4 | Thor | Nórdica | AOE / dano em massa | Espírito |
| 5 | Loki | Nórdica | Trick / cópia / reflect | Mente |
| 6 | Anúbis | Egípcia | DoT (veneno mortal) + finisher | Sangue |
| 7 | Ísis | Egípcia | Healer principal + remoção de aflição | Espírito |
| 8 | Sun Wukong | Chinesa | Multi-ataque / clones | Sangue |
| 9 | Mulan | Chinesa (histórica) | Damage físico + furtividade | Vigor |
| 10 | Amaterasu | Japonesa | Buff de dano + wall (escudo) | Espírito |
| 11 | Quetzalcóatl | Asteca | Drainer (rouba essência) | Mente |
| 12 | Anansi | Africana (Akan) | Stun AOE / armadilhas | Mente |
| 13 | Inanna | Mesopotâmica | Híbrido cura + dano sagrado | Espírito |
| 14 | Joana d'Arc | Histórica francesa | Tank / redução de dano em equipe | Vigor |
| 15 | Cleópatra | Histórica egípcia | Charme / redirecionamento de alvo | Mente |
| 16 | Rei Arthur | Britânica | Leader / buffs de equipe + executor | Vigor |

---

## Cobertura cultural

| Cultura | Personagens |
|---|---|
| Grécia | Aquiles, Atena, Medusa |
| Nórdica | Thor, Loki |
| Egípcia | Anúbis, Ísis |
| Chinesa | Sun Wukong, Mulan |
| Japonesa | Amaterasu |
| Asteca | Quetzalcóatl |
| Africana (Akan) | Anansi |
| Mesopotâmica | Inanna |
| Histórica/Lendária | Joana d'Arc, Cleópatra, Rei Arthur |

10 origens distintas. Boa diversidade para apelo global desde o lançamento.

---

## Cobertura de arquétipos

| Arquétipo | Personagens |
|---|---|
| Burst físico | Aquiles, Mulan, Rei Arthur |
| Burst mágico / AOE | Thor |
| DoT / sustain damage | Anúbis |
| Healer | Ísis, Inanna |
| Tank / redução | Joana d'Arc, Atena, Amaterasu |
| Stun / disable | Medusa, Anansi |
| Controle de comportamento | Cleópatra (charme), Loki (reflect) |
| Drainer (negação de recurso) | Quetzalcóatl |
| Trick / cópia | Loki |
| Multi-ataque | Sun Wukong |
| Buff de equipe | Atena, Amaterasu, Rei Arthur |

Todos os 8 arquétipos clássicos de team-comp do gênero estão cobertos por pelo menos 1 personagem, vários por 2+. Permite construir todas as 8–10 comps documentadas em [`06-balanceamento.md`](06-balanceamento.md).

---

## Especificação completa — exemplo (Aquiles)

Veja `personagens/aquiles.yaml` para o YAML pronto. Resumo:

**Aquiles — Burst físico**
- HP base: 110
- **Lança Mortal** (básica): 20 de dano físico, custo 1 Vigor, sem cooldown.
- **Carga dos Mirmidões** (secundária): 35 de dano físico + Sangramento (10/turno por 2 turnos), custo 2 Vigor, cooldown 2.
- **Fúria de Pélida** (ultimate): por 3 turnos, +15 dano e -10 dano recebido — *mas* fica vulnerável a perfurante (calcanhar), custo 2 Vigor + 1 Genérica, cooldown 4.
- **Esquivar** (defesa universal): invulnerável 1 turno.

---

## Especificação resumida — outros 15

> Todos precisam de YAMLs completos antes do início da Fase 1 (engine de regras). Aqui ficam as ideias-chave + custos/cooldowns aproximados para sinalizar peso.

### 2. Atena — Suporte defensivo
HP 95.
- **Lança da Sabedoria** (básica): 15 dano mágico + revela cooldowns inimigos por 1 turno. Custo 1 Mente. CD 0.
- **Conselho** (secundária): aliado ganha 15 redução de dano + 1 essência Mente extra no próximo turno. Custo 1 Mente + 1 Genérica. CD 2.
- **Égide** (ultimate): equipe inteira ganha defesa destrutível 25 HP por 2 turnos. Custo 2 Mente + 2 Genérica. CD 5.

### 3. Medusa — Disable longo
HP 90.
- **Olhar Perturbador** (básica): 15 dano mágico + alvo ganha "marcado para petrificação" (1 turno). Custo 1 Mente. CD 0.
- **Sibilo das Serpentes** (secundária): 25 dano + se alvo está marcado, atordoa por 1 turno. Custo 2 Mente. CD 2.
- **Petrificação** (ultimate): atordoa 1 alvo por 3 turnos; alvo não pode ficar invulnerável durante. Custo 2 Mente + 2 Genérica. CD 6.

### 4. Thor — AOE
HP 105.
- **Mjolnir** (básica): 25 dano físico em 1 alvo. Custo 1 Vigor + 1 Espírito. CD 0.
- **Trovão Lateral** (secundária): 18 dano AOE em todos inimigos. Custo 2 Espírito. CD 2.
- **Ragnarok** (ultimate): 35 dano AOE perfurante; Thor fica desarmado por 1 turno (recuo). Custo 3 Espírito + 1 Genérica. CD 5.

### 5. Loki — Trick
HP 85.
- **Mentira Dourada** (básica): 15 dano mental; alvo perde 1 essência aleatória. Custo 1 Mente. CD 0.
- **Forma Cambiante** (secundária): copia a próxima habilidade que um aliado seu lançar (uso único na próxima rodada). Custo 1 Mente + 1 Genérica. CD 3.
- **Engano de Asgard** (ultimate): no próximo turno, todos os ataques inimigos são redirecionados ao próprio lançador. Custo 2 Mente + 2 Genérica. CD 6.

### 6. Anúbis — DoT
HP 95.
- **Bandagens Sufocantes** (básica): 10 dano + Veneno (10/turno por 2 turnos). Custo 1 Sangue. CD 0.
- **Sentença** (secundária): 20 dano; se alvo tem veneno, dano dobra. Custo 1 Sangue + 1 Mente. CD 2.
- **Pesar do Coração** (ultimate): consome todo o veneno restante de 1 alvo e converte em dano imediato (10× duração restante). Custo 2 Sangue + 1 Genérica. CD 5.

### 7. Ísis — Healer
HP 95.
- **Mãos da Mãe** (básica): cura 20 HP em 1 aliado. Custo 1 Espírito. CD 0.
- **Asas Protetoras** (secundária): cura 15 HP no aliado + remove uma aflição. Custo 1 Espírito + 1 Genérica. CD 2.
- **Ressurgir** (ultimate): aliado de menor HP recebe 50 HP + remove todas aflições + ganha regeneração 10/turno por 2 turnos. Custo 2 Espírito + 2 Genérica. CD 6.

### 8. Sun Wukong — Multi-ataque
HP 100.
- **Bastão Crescente** (básica): 18 dano físico. Custo 1 Vigor. CD 0.
- **Clones de Pelo** (secundária): 3 acertos de 12 dano físico em alvos à escolha (mesmo ou diferentes). Custo 2 Vigor. CD 3.
- **Rei Macaco** (ultimate): 2 turnos furtivo; próximo ataque após sair da furtividade tem dano triplicado e perfurante. Custo 2 Sangue + 1 Vigor. CD 5.

### 9. Mulan — Damage furtivo
HP 100.
- **Espada Escondida** (básica): 18 dano físico; +5 se Mulan está furtiva. Custo 1 Vigor. CD 0.
- **Disfarce** (secundária): Mulan fica furtiva por 2 turnos. Custo 1 Vigor + 1 Genérica. CD 3.
- **Honra da Família** (ultimate): 40 dano físico perfurante; se acerto enquanto furtiva, ignora invulnerabilidade. Custo 2 Vigor + 1 Genérica. CD 5.

### 10. Amaterasu — Buff/Wall
HP 95.
- **Espelho Solar** (básica): aliado ganha +10 dano por 2 turnos. Custo 1 Espírito. CD 0.
- **Manhã Eterna** (secundária): equipe ganha regeneração 8/turno por 2 turnos. Custo 1 Espírito + 1 Genérica. CD 3.
- **Caverna Sagrada** (ultimate): equipe inteira invulnerável por 1 turno. Custo 3 Espírito + 2 Genérica. CD 7.

### 11. Quetzalcóatl — Drainer
HP 95.
- **Vento Sussurrado** (básica): 12 dano + drena 1 essência aleatória do oponente. Custo 1 Mente. CD 0.
- **Pluma Sagrada** (secundária): 20 dano AOE; cada alvo perde 1 essência aleatória. Custo 2 Mente. CD 3.
- **Sopro do Mythos** (ultimate): no próximo turno, oponente não recebe nenhuma essência. Custo 2 Mente + 2 Genérica. CD 6.

### 12. Anansi — Stun AOE
HP 90.
- **Fio da Aranha** (básica): 12 dano + alvo recebe -1 essência aleatória no próximo turno. Custo 1 Mente. CD 0.
- **Armadilha** (secundária): 1 inimigo atordoado por 1 turno. Custo 2 Mente. CD 3.
- **Teia de Mentiras** (ultimate): todos os inimigos atordoados por 1 turno. Custo 3 Mente + 2 Genérica. CD 6.

### 13. Inanna — Híbrido
HP 95.
- **Lança da Aurora** (básica): 18 dano sagrado + cura 5 HP num aliado. Custo 1 Espírito. CD 0.
- **Descida ao Submundo** (secundária): Inanna recebe 15 dano fixo, mas equipe ganha +1 essência Espírito e regeneração 10/turno por 2 turnos. Custo 1 Sangue. CD 3.
- **Subida da Rainha** (ultimate): cura 30 HP em 1 aliado + 25 dano em 1 inimigo. Custo 2 Espírito + 1 Sangue. CD 5.

### 14. Joana d'Arc — Tank
HP 120.
- **Espada Sagrada** (básica): 18 dano físico. Custo 1 Vigor. CD 0.
- **Estandarte Erguido** (secundária): Joana e 1 aliado recebem 15 redução de dano por 2 turnos. Custo 1 Vigor + 1 Genérica. CD 3.
- **Voto de Orléans** (ultimate): por 1 turno, todo dano em qualquer aliado é redirecionado a Joana, com -50% (Joana ainda recebe). Custo 2 Vigor + 2 Genérica. CD 6.

### 15. Cleópatra — Controle
HP 90.
- **Decreto Real** (básica): 15 dano mental + alvo não pode usar habilidade básica no próximo turno. Custo 1 Mente. CD 0.
- **Charme** (secundária): no próximo turno, próximo ataque do alvo é redirecionado para um aliado dele (escolhido por Cleópatra). Custo 1 Mente + 1 Genérica. CD 3.
- **Rainha do Nilo** (ultimate): por 1 turno, controle total de 1 inimigo — no turno do oponente, ele usa habilidade básica num aliado dele à sua escolha. Custo 3 Mente + 1 Genérica. CD 7.

### 16. Rei Arthur — Leader
HP 110.
- **Excalibur** (básica): 22 dano físico. Custo 1 Vigor + 1 Genérica. CD 0.
- **Inspirar Cavaleiros** (secundária): equipe ganha +10 dano em ataques físicos por 2 turnos. Custo 1 Vigor + 1 Genérica. CD 3.
- **Mesa Redonda** (ultimate): aliados de menor HP que Arthur ganham 25 HP de defesa destrutível; Arthur ganha +1 turno de cooldown reduzido em todas as habilidades de aliados. Custo 2 Vigor + 2 Genérica. CD 6.

---

## Princípios para criar novos personagens (após MVP)

1. **Fidelidade ao mito** acima de "balanceamento perfeito" — character first.
2. Cada personagem deve ter **1 fraqueza clara** (Aquiles → calcanhar; Sun Wukong → vulnerável fora da transformação; Inanna → custo em HP próprio).
3. Toda nova habilidade deve poder ser explicada em **1 frase**.
4. **Não** adicionar mecânicas novas só para 1 personagem. Reusar o vocabulário existente em [`07-glossario.md`](07-glossario.md).
5. **Spread cultural**: cada wave de 4 personagens novos deve cobrir ≥ 3 mitologias diferentes.
6. Consultar fontes primárias da mitologia. Evitar versões pop-culture recentes (que podem estar protegidas).
