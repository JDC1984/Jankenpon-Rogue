"""
Item registry for Jankenpon-Rogue.
Each item is a dictionary of simple fields.

To keep the file compact while providing 20 items per family, we generate
items programmatically with simple, readable effects:
- Sodas: one-time consumables that boost gold or score on the next round.
- Rings: passive bonuses to gold or score every round.
- Stationary: conditional score boosts when beating a specific move.
"""

def create_items():
    """Build and return the item dictionary keyed by id."""
    items = {}

    # Helper to build effect descriptions
    def soda_desc(score_pct=None, gold_bonus=None):
        parts = []
        if score_pct:
            parts.append(f"+{int(score_pct*100-100)}% score on next win/tie")
        if gold_bonus:
            parts.append(f"+{gold_bonus} gold next round")
        return ", ".join(parts) + ", then consumed."

    def ring_desc(score_pct=None, gold_bonus=None):
        parts = []
        if score_pct:
            parts.append(f"+{int(score_pct*100-100)}% score passive")
        if gold_bonus:
            parts.append(f"+{gold_bonus} gold each round")
        return " & ".join(parts)

    def st_desc(target, pct):
        return f"+{int(pct*100-100)}% score when you beat {target}."

    # Generate 20 sodas, rings, stationary
    soda_cost_base = 10
    ring_cost_base = 14
    st_cost_base = 8

    # Sodas: alternate score and gold boosts
    for i in range(20):
        sid = f"soda_boost_{i+1}"
        score_mult = 1.2 + (i % 4) * 0.05  # 20% to 35%
        gold_bonus = 2 + (i % 3)           # 2–4
        items[sid] = {
            "id": sid,
            "name": f"Soda Boost {i+1}",
            "type": "soda",
            "family": None,
            "sprite_index": i,  # 0-19
            "cost": soda_cost_base + (i // 2),
            "description": soda_desc(score_mult, gold_bonus),
            "effect": {
                "x_mult_temp": 1.2 + 0.1 * (i % 3),
                "plus_mult_temp": 0.5 if (i % 2 == 0) else 0.0,
                "consume": True,
            },
        }

    # Rings: passive score and gold
    for i in range(20):
        rid = f"ring_bonus_{i+1}"
        score_mult = 1.05 + (i % 5) * 0.05   # 5% to 25%
        gold_bonus = 1 + (i % 2)             # 1 or 2
        items[rid] = {
            "id": rid,
            "name": f"Ring Bonus {i+1}",
            "type": "ring",
            "family": None,
            "sprite_index": 20 + i,  # 20-39
            "cost": ring_cost_base + (i // 2),
            "description": ring_desc(score_mult, gold_bonus),
            "effect": {
                "plus_mult": score_mult - 1.0,
                "x_mult": 1.0 + 0.02 * (i % 3),
                "plus_on_sweep": 0.5 if (i % 4 == 0) else 0.0,
                "gold_add_per_round": gold_bonus,
            },
        }

    # Stationary: rotate target move rock/paper/scissors
    targets = ["rock", "paper", "scissors"]
    for i in range(20):
        tid = f"st_edge_{i+1}"
        target = targets[i % 3]
        pct = 1.15 + (i % 4) * 0.05  # 15% to 30%
        items[tid] = {
            "id": tid,
            "name": f"{target.title()} Edge {i+1}",
            "type": "stationary",
            "family": target,
            "sprite_index": 40 + i,  # 40-59
            "cost": st_cost_base + (i // 2),
            "description": st_desc(target, pct),
            "effect": {
                "plus_per_win_vs": {target: pct - 1.0},
            },
        }

    return items

ITEMS = create_items()
