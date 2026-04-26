---
description: Simulate matches for balance feedback
argument-hint: "[--runs N] [--seed N]"
---

Run the bot-vs-bot match simulator to inspect balance.

Default: `agora-sim --runs 100 --quiet` and report the win-rate split.

If the user passes args (e.g. `/sim --seed 7`), forward them to `agora-sim` and show the verbose match log.

If win rates are skewed (>60% to either side) call it out and suggest probable causes (initiative bias, missing counter, dominant skill).
