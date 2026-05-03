#!/usr/bin/env python3
"""Crop skill spritesheets into individual icon files.

Layout per sheet: 4 rows (characters) × 4 columns (skills)
  row 0-3 = characters in batch order (top to bottom)
  col 0   = skill 1 (basic)
  col 1   = skill 2 (secondary)
  col 2   = skill 3 (ultimate)
  col 3   = character-specific defense skill

Row boundaries are NOT uniform — each sheet was measured from the actual
pixel data (dark separator bands between cards).
"""

import os
from PIL import Image

SKILLS_DIR = "web/public/skills"
os.makedirs(SKILLS_DIR, exist_ok=True)

COL_W = 418  # all sheets: 4 cols × 418px = 1672px wide

# Exact row boundaries (y_start, y_end inclusive) measured per sheet.
# Determined by scanning average row brightness and finding dark separator gaps.
SHEET_ROWS: dict[str, list[tuple[int, int]]] = {
    "data/img/skills1.png": [(0, 251), (262, 485), (495, 693), (702, 940)],
    "data/img/skills2.png": [(12, 269), (285, 505), (517, 717), (728, 928)],
    "data/img/skills3.png": [(13, 249), (265, 476), (492, 686), (702, 925)],
    "data/img/skills4.png": [(0, 270), (285, 504), (517, 717), (728, 940)],
}

# Batches: (sheet_path, [char_id row0, row1, row2, row3])
BATCHES = [
    (
        "data/img/skills1.png",
        ["anansi", "inanna", "joan_of_arc", "king_arthur"],
    ),
    (
        "data/img/skills2.png",
        ["loki", "anubis", "isis", "cleopatra"],
    ),
    (
        "data/img/skills3.png",
        ["sun_wukong", "mulan", "amaterasu", "quetzalcoatl"],
    ),
    (
        "data/img/skills4.png",
        ["achilles", "athena", "medusa", "thor"],
    ),
]

# Skill IDs per character (col order: basic, secondary, ultimate, char-defense)
SKILL_IDS: dict[str, list[str]] = {
    "achilles": ["spear", "charge", "wrath", "defense"],
    "athena": ["spear_of_wisdom", "counsel", "aegis", "defense"],
    "medusa": ["unsettling_gaze", "serpent_hiss", "petrification", "defense"],
    "thor": ["mjolnir", "side_thunder", "ragnarok", "defense"],
    "loki": ["golden_lie", "shapeshift", "asgard_deceit", "defense"],
    "anubis": ["wraps", "sentence", "heart_burden", "defense"],
    "isis": ["mothers_hands", "protective_wings", "resurgence", "defense"],
    "cleopatra": ["royal_decree", "charm", "queen_of_the_nile", "defense"],
    "sun_wukong": ["crescent_staff", "hair_clones", "monkey_king", "defense"],
    "mulan": ["hidden_sword", "disguise", "family_honor", "defense"],
    "amaterasu": ["solar_mirror", "eternal_morning", "sacred_cave", "defense"],
    "quetzalcoatl": ["whispered_wind", "sacred_plume", "sacred_breath", "defense"],
    "anansi": ["spider_thread", "trap", "web_of_lies", "defense"],
    "inanna": ["spear_of_dawn", "descent_underworld", "queen_returns", "defense"],
    "joan_of_arc": ["sacred_sword", "standard_raised", "vow_of_orleans", "defense"],
    "king_arthur": ["excalibur", "inspire_knights", "round_table", "defense"],
}

for sheet_path, chars in BATCHES:
    print(f"\n=== {sheet_path} ===")
    img = Image.open(sheet_path)
    rows = SHEET_ROWS[sheet_path]
    for char_idx, char_id in enumerate(chars):
        y0, y1 = rows[char_idx]
        for skill_col, skill_id in enumerate(SKILL_IDS[char_id]):
            x0 = skill_col * COL_W
            icon = img.crop((x0, y0, x0 + COL_W, y1 + 1))
            out_path = os.path.join(SKILLS_DIR, f"{char_id}_{skill_id}.png")
            icon.save(out_path)
            print(f"  row{char_idx} col{skill_col} → {out_path}")

total = sum(len(c) for _, c in BATCHES) * 4
print(f"\nDone. {total} icons → {SKILLS_DIR}/")
