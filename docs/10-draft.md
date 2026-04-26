# 10 — Ranked Draft (Ban-Pick)

> Pre-match phase exclusive to **ranked**. Players ban one character each and then take turns picking, knowing the chosen arena. Adds a meta-game layer of counter-picking and adapting to terrain.

---

## 1. Goals

- Reward strategic depth: knowing the meta and the arena should matter.
- Reduce comp staleness: no two ranked matches start with identical roster windows.
- Keep duration tight: total draft ≤ 90 seconds at the slowest.
- Be cancellable: a disconnect or timeout never blocks the queue.

Casual and PvE matches **skip** the draft — players bring a pre-built team. Draft is a ranked-only ritual.

---

## 2. Phase order

```
Match found
   │
   ▼
[1] Arena reveal           server picks arena (random / curated rotation)
[2] Lock-in window (10s)   players see the arena and locked roster
[3] Ban phase              both players ban 1 character (simultaneous, reveal together)
[4] Pick phase             snake order: A1 - B1 - B2 - A2 - A3 - B3
[5] Confirm window (5s)    last sanity check, then start_match runs
   │
   ▼
Match begins
```

Total worst-case timeline: 10s + 30s + (6 × 25s) + 5s = **3 min 15 s** if everyone hits the timer. Realistic median: under 60s.

---

## 3. Why snake order on picks

Pure alternation `A B A B A B` gives the first picker a real edge in 3v3 because they get the first AND third selection at moments where the pool is freshest.

Snake `A1 B1 B2 A2 A3 B3` gives B back-to-back picks at positions 2–3 — a counter-balance the genre converged on (LoL, Dota 2 Captain's Mode all use snake-style for parity).

If telemetry shows first-pick win rate drifting outside 47–53% we revisit; until then, snake stands.

---

## 4. Bans

- **1 ban each per side.** (For 16 characters this removes 12.5% of the pool, which is enough pressure.)
- Bans are **simultaneous**, revealed together — neither player knows what the other will ban while choosing.
- A banned character cannot be picked by either side this match.
- If a player times out, the ban is auto-rolled to a **random character not in their starter set** (so timeouts can't grief by banning a weak character on purpose).

---

## 5. Picks

- Snake order: `A1 → B1 → B2 → A2 → A3 → B3`.
- 25-second timer per pick.
- On timeout, the system picks the highest-rated character (by global pick rate) in the player's unlocked pool that is not yet picked or banned. Predictable, never random.
- A player can only pick from their own **unlocked** roster (see `docs/09-missions.md`). If their starter pool is too small to fill 3 slots after bans, the system pads with random unlocked characters — practically impossible since starters always cover all archetypes.

---

## 6. Arena reveal timing — design choice

We reveal the arena **before** bans so that bans/picks can be tactical against the arena modifier. Alternative was revealing after picks (forces neutral comps), but that throws away the most interesting strategic dimension. We pick the more interesting design.

---

## 7. Data model

```python
# domain/draft.py
class DraftPhase(StrEnum):
    ARENA_REVEAL = "arena_reveal"
    BAN = "ban"
    PICK = "pick"
    CONFIRM = "confirm"
    DONE = "done"
    CANCELLED = "cancelled"

class DraftState(BaseModel):
    draft_id: str
    arena_id: str
    side_a_player_id: str
    side_b_player_id: str
    phase: DraftPhase
    bans: dict[Side, str | None] = {Side.A: None, Side.B: None}  # one each
    picks: dict[Side, list[str]] = {Side.A: [], Side.B: []}
    pick_order: list[Side]   # [A, B, B, A, A, B]
    pick_index: int = 0
    timer_deadline: datetime | None = None
```

Snake order is precomputed at `arena_reveal` and stored, so reconnects can resume cleanly.

---

## 8. Use cases

- `start_draft(matchmaker_pair, arena_id)` — creates DraftState, kicks off arena reveal timer.
- `submit_ban(draft_id, side, character_id)` — validates it's the ban phase + character is in the pool, stores ban. When both submitted (or timer hits), phase advances to PICK.
- `submit_pick(draft_id, side, character_id)` — validates it's that side's turn + character not banned/picked + in player's unlocked pool. Advances pick_index.
- `cancel_draft(draft_id, reason)` — disconnects, idle abandonment. Players returned to queue.
- `finalize_draft(draft_id)` — when phase == DONE, calls `start_match` with the assembled teams + arena.

All draft state is held in **Redis** with a 10-minute TTL — durable enough for reconnects, ephemeral enough to be safe.

---

## 9. UI sketch

```
┌─────────────────────────────────────────────────────────┐
│  ARENA: Mount Olympus       ⏱ 24s                       │
│  "Greek-mythology characters get +5 base HP."           │
├─────────────────────────────────────────────────────────┤
│  YOU                                  OPPONENT          │
│  Bans: Loki                           Bans: Anubis      │
│  Picks: Athena, Achilles, ?           Picks: Thor, Isis │
│                                                         │
│  Pool:                                                  │
│  [Aquiles] [Athena] [Thor] [BANNED] [Anubis BANNED]...  │
│  [Click a character to lock in your last pick]          │
└─────────────────────────────────────────────────────────┘
```

Highlights:
- Banned characters greyed with strikethrough.
- Already-picked characters greyed with team color.
- Arena modifier text is always visible and tappable for full description.
- Big timer pulses red below 5s.

---

## 10. Integration points

| Concern | Where it lives |
|---|---|
| State machine | `application/use_cases/draft.py` |
| Validation rules | `application/use_cases/draft.py` |
| Redis adapter | `infrastructure/redis_draft_repository.py` |
| WebSocket frames | `interfaces/api/draft_ws.py` |
| Frontend state | `web/src/stores/draftStore.ts` |
| Frontend UI | `web/src/pages/draft.tsx` |

---

## 11. Open decisions

- [ ] Do we let players queue in pre-made duos or only solo for now? (MVP: solo only — simpler matchmaking.)
- [ ] Arena pick: pure random vs. weighted rotation vs. player-vetoed? (MVP: server-random from active pool.)
- [ ] Show opponent's pick history mid-draft, or only after match? (MVP: hidden — keeps psychological pressure neutral.)
