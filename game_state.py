"""
Game state helpers for Jankenpon-Rogue.
All structures are plain dictionaries and lists to match ThinkPython style.
"""

import json
import os
import random

SETTINGS_FILE = "settings.json"


def create_player():
    """Return a new player dictionary with base stats, gold, and empty inventories."""
    return {
        "stress_max": 10,
        "stress": 10,
        "gold": 20,          # starting seed gold
        "score": 0,
        "rings": [],         # equipped rings (max 2)
        "stationary": [],    # stationary items (max 5, family max 2)
        "sodas": [],         # temporary sodas (UI slots show a few)
        "owned": [],         # all purchased item ids
    }


def required_score(round_index, heat_index):
    """Compute score requirement for a given round/heat using simple arithmetic."""
    base = 15
    round_multiplier = 1.2 ** round_index
    heat_bonus_list = [0.8, 1.0, 1.3]
    heat_bonus = heat_bonus_list[heat_index]
    # Halved requirement per user request
    return int(0.5 * base * round_multiplier * heat_bonus)


def create_heat_info():
    """Build a lookup table mapping (round, heat) to required score."""
    info = {}
    for r in range(8):
        for h in range(3):
            info[(r, h)] = required_score(r, h)
    return info


def create_settings():
    """Return default settings dictionary."""
    return {
        "music_volume": 0.5,
        "sfx_volume": 0.5,
        "fullscreen": False,
        "show_tutorial_hints": True,
    }


def create_ui_state():
    """Return UI state for menus/settings/help selections."""
    return {
        "main_menu_index": 0,
        "pause_menu_index": 0,
        "settings_index": 0,
        "help_index": 0,
        "confirm_exit": False,
        "menu_confirm_quit": False,
    }


def load_settings():
    """Load settings from JSON file or return defaults on failure."""
    if not os.path.exists(SETTINGS_FILE):
        return create_settings()
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
        defaults = create_settings()
        defaults.update({k: data.get(k, defaults[k]) for k in defaults})
        return defaults
    except Exception:
        return create_settings()


def save_settings(settings):
    """Save settings to JSON file, ignoring errors quietly."""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass


def create_game_state():
    """Return the initial global game state dictionary."""
    return {
        "phase": "main_menu",     # main_menu, menu, battle, shop, work, settings, help, pause_menu
        "round": 0,
        "heat": 0,
        "heat_info": create_heat_info(),
        "player": create_player(),
        "work_settings": {
            "base_seconds": 30,   # demo-friendly duration
            "extra_minutes": 0,   # adjustable before starting work
            "reward_multiplier": 1.0,
        },
        "rps": {
            "rounds_played": 0,       # total RPS rounds this run
            "rounds_since_shop": 0,   # rounds in current set (0-3)
            "rounds_since_work": 0,   # rounds since last work break
            "opponent_id": 1,         # increments each round
            "log": [],                # list of round dicts
            "target": 9,              # total allowed in a run before reset
        },
        "shop": {
            "offers": [],     # list of item ids currently offered
            "pending": None,  # selected item id awaiting confirmation
            "message": "",
        },
        "develop_mode": False,    # if True, skip timers/gates for faster testing
        "settings": load_settings(),
        "ui": create_ui_state(),
        "prev_phase": "menu",  # to return from pause/settings/help
        "game_over_msg": "",
        "develop_mode": False,    # persistent dev flag
    }
