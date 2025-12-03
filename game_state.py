"""
Dictionary-based game state helpers.
Keeps the structure simple and close to ThinkPython exercises.
"""

def create_player():
    """Return a new player dictionary with base stats and inventories."""
    return {
        "stress_max": 10,
        "stress": 10,
        "gold": 0,
        "score": 0,
        "rings": [],       # list of item ids
        "stationary": [],  # list of item ids
        "sodas": []        # list of item ids
    }


def required_score(round_index, heat_index):
    """Compute score needed for a given (round, heat).

    round_index: 0-7 (eight rounds total)
    heat_index: 0-2 (three heats per round)
    Uses small arithmetic plus a lookup list; mirrors notebook patterns.
    """
    base = 15
    round_multiplier = 1.2 ** round_index
    heat_bonus_list = [0.8, 1.0, 1.3]
    heat_bonus = heat_bonus_list[heat_index]
    required = base * round_multiplier * heat_bonus
    return int(required)


def create_heat_info():
    """Precompute score requirements for all heats.

    Builds a lookup table keyed by (round, heat) tuples for quick access.
    """
    info = {}
    for r in range(8):      # rounds 0..7
        for h in range(3):  # heats 0..2
            info[(r, h)] = required_score(r, h)
    return info


def create_game_state():
    """Return the initial game state dictionary."""
    return {
        "phase": "menu",       # 'menu', 'work', 'heat', etc.
        "round": 0,
        "heat": 0,
        "heat_info": create_heat_info(),
        "player": create_player(),
    }
