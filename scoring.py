"""
Balatro-inspired scoring engine for Jankenpon-Rogue (per 3-round set).

SetScore = BaseScore * TotalMultiplier
BaseScore uses win/tie counts, move diversity, round/heat scaling.
TotalMultiplier combines base_mult, plus_mult, x_mult from items, sodas, synergies, and streak.
"""

from items import ITEMS

HEAT_MULTS = [0.8, 1.0, 1.25]

# Synergy definitions: pair of item ids -> bonus x_mult
SYNERGIES = {
    ("st_sharp_pencil", "st_beefy_eraser"): 1.2,
}


def calculate_set_score(summary, game_state):
    """
    Compute score for a 3-round set.

    summary: {
      "results": ["win","lose","tie"],
      "moves": ["rock","paper","scissors"],
      "round": int,
      "heat": int,
      "set_streak": int
    }
    """
    results = summary["results"]
    moves = summary["moves"]
    round_idx = summary.get("round", 0)
    heat_idx = summary.get("heat", 0)
    set_streak = summary.get("set_streak", 0)

    W = results.count("win")
    T = results.count("tie")
    RawBase = 10 * W + 4 * T

    unique_moves = len(set(moves))
    if unique_moves == 3:
        diversity_bonus = 10
    elif unique_moves == 2:
        diversity_bonus = 5
    else:
        diversity_bonus = 0

    base_no_round = RawBase + diversity_bonus
    round_mult = 1.0 + 0.15 * round_idx
    heat_mult = HEAT_MULTS[heat_idx] if heat_idx < len(HEAT_MULTS) else HEAT_MULTS[-1]
    base_score = base_no_round * round_mult * heat_mult

    base_mult = 1.0
    plus_mult = 0.0
    x_mult = 1.0
    synergy_mult = 1.0
    soda_used = []

    # Rings: passive jokers
    for rid in game_state["player"]["rings"]:
        itm = ITEMS.get(rid, {})
        eff = itm.get("effect", {})
        plus_mult += eff.get("plus_mult", 0.0)
        x_mult *= eff.get("x_mult", 1.0)
        # example conditional: 3-win sweep
        if eff.get("plus_on_sweep") and W == 3:
            plus_mult += eff["plus_on_sweep"]

    # Stationary: conditional +mult
    for sid in game_state["player"]["stationary"]:
        itm = ITEMS.get(sid, {})
        eff = itm.get("effect", {})
        vs = eff.get("plus_per_win_vs", {})
        for mv, bonus in vs.items():
            # count wins where move beats mv
            plus_mult += bonus * count_wins_vs(results, moves, mv)

    # Synergies
    owned = set(game_state["player"]["owned"])
    triggered = []
    for (a, b), bonus in SYNERGIES.items():
        if a in owned and b in owned:
            synergy_mult *= bonus
            triggered.append(f"{a}+{b}")

    # Sodas: temporary per set
    for sid in list(game_state["player"]["sodas"]):
        itm = ITEMS.get(sid, {})
        eff = itm.get("effect", {})
        x_mult *= eff.get("x_mult_temp", 1.0)
        plus_mult += eff.get("plus_mult_temp", 0.0)
        soda_used.append(sid)
        if eff.get("consume", True):
            game_state["player"]["sodas"].remove(sid)

    # Streak bonus (set streak where W>=2)
    if set_streak >= 1:
        plus_mult += min(0.5 * set_streak, 3.0)

    total_mult = (base_mult + plus_mult) * x_mult * synergy_mult
    total = int(round(base_score * total_mult))

    return {
        "base_score": int(round(base_score)),
        "raw_base": RawBase,
        "diversity_bonus": diversity_bonus,
        "round_mult": round_mult,
        "heat_mult": heat_mult,
        "plus_mult": plus_mult,
        "x_mult": x_mult,
        "synergy_mult": synergy_mult,
        "synergy_list": triggered,
        "soda_used": soda_used,
        "total_mult": total_mult,
        "total": total,
    }


def count_wins_vs(results, moves, target_move):
    """Count wins where player beat the specific target move."""
    count = 0
    for res, mv in zip(results, moves):
        if res == "win":
            if beats(mv, target_move):
                count += 1
    return count


def beats(player_move, enemy_move):
    """Return True if player_move beats enemy_move."""
    return (player_move == "rock" and enemy_move == "scissors") or \
           (player_move == "paper" and enemy_move == "rock") or \
           (player_move == "scissors" and enemy_move == "paper")
