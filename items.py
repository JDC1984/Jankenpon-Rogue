"""
Item registry for Step 1.
Uses a dictionary-of-dictionaries instead of classes to match notebook style.
"""

def create_items():
    """Return a dictionary of item definitions used for rendering/demo."""

    items = {}

    items["soda_jolt_cola"] = {
        "id": "soda_jolt_cola",
        "name": "Jolt Cola",
        "type": "soda",
        "family": None,
        "sprite_index": 0,   # first tile in the sheet
        "cost": 10,
        "description": "Double score on next win. (placeholder)",
    }

    items["ring_flow_state"] = {
        "id": "ring_flow_state",
        "name": "Ring of Flow State",
        "type": "ring",
        "family": None,
        "sprite_index": 20,  # first ring tile (row 2, col 0 if 10 cols)
        "cost": 20,
        "description": "Score decay 30% slower. (placeholder)",
    }

    items["st_sharp_pencil"] = {
        "id": "st_sharp_pencil",
        "name": "Sharp Pencil",
        "type": "stationary",
        "family": "scissors",
        "sprite_index": 40,  # first stationary tile (row 4, col 0)
        "cost": 6,
        "description": "+20% score beating paper. (placeholder)",
    }

    return items


# Build the registry once on import so other modules can pull from ITEMS.
ITEMS = create_items()
