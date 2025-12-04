"""
Rock-Paper-Scissors helpers.
Plain functions and dictionaries only.
"""

import random

MOVES = ["rock", "paper", "scissors"]

def enemy_move():
    """Return a random enemy move."""
    return random.choice(MOVES)

def resolve_round(player_move, enemy_move):
    """Return 'win', 'lose', or 'tie' for a single RPS round."""
    if player_move == enemy_move:
        return "tie"
    if (player_move == "rock" and enemy_move == "scissors") or \
       (player_move == "paper" and enemy_move == "rock") or \
       (player_move == "scissors" and enemy_move == "paper"):
        return "win"
    return "lose"

def create_battle_state():
    """Return a fresh battle state dictionary for an RPS set."""
    return {
        "rounds_played": 0,       # total rounds in current set (0-9)
        "rounds_since_shop": 0,   # rounds in current trio (0-3)
    }
