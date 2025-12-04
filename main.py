import sys
import time
import random
import math

import pygame
try:
    import winsound  # for simple beeps on PIN entry (Windows)
except ImportError:
    winsound = None

from timer import PomodoroTimer
from game_state import create_game_state, save_settings, required_score
from items import ITEMS
from rps import MOVES, enemy_move, resolve_round, create_battle_state
from scoring import calculate_set_score

# ---------- Window / layout ----------
WIN_W = 1280
WIN_H = 720
FPS = 60

# Y positions chosen to avoid overlap
PADDING = 16
HUD_Y = 20
HUD_LINE = 26
LOG_X = int(WIN_W * 0.7)
LOG_Y = HUD_Y
MENU_CENTER_Y = int(WIN_H * 0.38)
BUTTON_ROW_Y = MENU_CENTER_Y + 80
INVENTORY_Y = int(WIN_H * 0.78)
INV_Y = INVENTORY_Y  # legacy name used in draw_inventory_bar
CONTROLS_Y = WIN_H - PADDING * 2
MENU_ITEMS_Y = 340
SHOP_ITEMS_Y = 360
CONTROLS_Y = WIN_H - 26

# ---------- Colors ----------
BG = (10, 10, 30)
TEXT = (230, 230, 230)
SUBTEXT = (170, 190, 210)
ACCENT = (255, 215, 0)
BAD = (230, 120, 80)
GOOD = (120, 210, 120)
PANEL = (40, 50, 80)
PANEL_DARK = (30, 35, 55)
BUTTON = (70, 80, 110)
BUTTON_HOVER = (90, 110, 150)
BUTTON_SELECT = (130, 160, 210)
# Subtle samurai-inspired trims (warm lacquer + gold outline)
PANEL_TRIM = (90, 70, 50)
PANEL_OUTLINE = (200, 170, 90)

# ---------- Game tuning ----------
BASE_WORK_SECONDS = 30          # demo work session
GOLD_PER_WORK_BLOCK = 5         # reward per base work chunk
SCORE_PER_WORK_BLOCK = 5
EXTRA_MINUTE_BONUS = 0.05       # +5% per extra minute (demo: 30s per "min")

RPS_REWARD_WIN = 3
RPS_REWARD_TIE = 1
RPS_REWARD_LOSE = 0
RPS_ROUNDS_PER_SET = 3
RPS_SET_MAX = 9
RPS_WORK_GATE = 9  # require work every 9 rounds

SHOP_SIZE = 3
RING_MAX = 2
STATIONARY_MAX = 5
FAMILY_MAX = 99  # effectively uncapped per family, limited only by slots
SODA_SLOTS = 3
MAX_EXTRA_MINUTES = 60  # allow up to 60 extra minutes (30s chunks)

# Inventory slot counts
INV_SLOTS = {
    "rings": RING_MAX,
    "stationary": STATIONARY_MAX,
    "sodas": SODA_SLOTS,
}

# Dev PIN password
DEV_PIN = "1738"
# Sellback discount (60%)
SELL_DISCOUNT = 0.6
# Base score gain per win/tie
BASE_SCORE_WIN = 5
BASE_SCORE_TIE = 1
# Endless exponential multiplier base per completed set
ENDLESS_MULT_BASE = 1.35

# ---------- Fonts ----------
pygame.init()
pygame.font.init()
TITLE_FONT = pygame.font.SysFont("consolas", 36)
HUD_FONT = pygame.font.SysFont("consolas", 24)
SMALL_FONT = pygame.font.SysFont("consolas", 20)
TINY_FONT = pygame.font.SysFont("consolas", 16)

# ---------- Sprite sheet constants ----------
TILE_W = 64
TILE_H = 96
SHEET_COLS = 10
SHEET_ROWS = 6
SHEET_PATH = "assets/items_sheet.png"


def load_item_sprites():
    """Load the sprite sheet or build placeholders if missing."""
    try:
        sheet = pygame.image.load(SHEET_PATH).convert_alpha()
        sprites = []
        for row in range(SHEET_ROWS):
            for col in range(SHEET_COLS):
                rect = pygame.Rect(col * TILE_W, row * TILE_H, TILE_W, TILE_H)
                sprites.append(sheet.subsurface(rect))
        return sprites
    except Exception:
        # Build simple solid-color placeholder tiles (no numbers)
        sprites = []
        colors = [(90, 70, 140), (140, 110, 110), (170, 150, 90), (110, 160, 120)]
        for i in range(SHEET_ROWS * SHEET_COLS):
            surf = pygame.Surface((TILE_W, TILE_H))
            surf.fill(colors[i % len(colors)])
            sprites.append(surf)
        return sprites


def draw_text(screen, text, font, color, x, y):
    """Render text at (x, y)."""
    surf = font.render(text, True, color)
    screen.blit(surf, (x, y))
    return surf.get_rect(topleft=(x, y))


def clamp_tooltip_pos(pos):
    """Clamp tooltip position to stay on-screen."""
    return (min(pos[0], WIN_W - 260), min(pos[1], WIN_H - 120))


def beep():
    """Play a short beep for PIN pad feedback."""
    if winsound:
        try:
            winsound.Beep(1200, 80)
        except Exception:
            pass


def draw_button(screen, rect, text, font, hover, selected):
    """Draw a simple rectangle button with hover/selected colors."""
    color = BUTTON
    if selected:
        color = BUTTON_SELECT
    elif hover:
        color = BUTTON_HOVER
    pygame.draw.rect(screen, color, rect)
    txt = font.render(text, True, TEXT)
    txt_rect = txt.get_rect(center=rect.center)
    screen.blit(txt, txt_rect)


def draw_panel(screen, rect, fill_color, border_color, radius=8, border_width=2):
    """Draw a softly rounded panel with a gold-ish outline."""
    pygame.draw.rect(screen, fill_color, rect, border_radius=radius)
    pygame.draw.rect(screen, border_color, rect, width=border_width, border_radius=radius)


def make_item_placeholder(color):
    """Return a simple colored surface for items when no sprite available."""
    surf = pygame.Surface((TILE_W, TILE_H))
    surf.fill(color)
    return surf


def ensure_battle_state(game_state):
    """Create a battle_state dict if not present."""
    if "battle_state" not in game_state:
        game_state["battle_state"] = {
            "rounds_played": 0,
            "rounds_since_shop": 0,
            "player_move": None,
            "enemy_move": None,
            "result": "pending",
            "message": "",
            "buttons": [],
            "results": [],
            "moves": [],
            "last_set_score": None,
        }


def choose_shop_offers():
    """Pick SHOP_SIZE random item ids from ITEMS."""
    ids = list(ITEMS.keys())
    random.shuffle(ids)
    return ids[:SHOP_SIZE]


def inventory_counts(player):
    """Return counts per family for stationary items."""
    counts = {}
    for item_id in player["stationary"]:
        family = ITEMS[item_id]["family"]
        counts[family] = counts.get(family, 0) + 1
    return counts


def can_buy(player, item):
    """Return (ok, reason) indicating whether a purchase is allowed."""
    if player["gold"] < item["cost"]:
        return False, "Not enough gold."
    if item["type"] == "ring" and len(player["rings"]) >= RING_MAX:
        return False, "Ring limit reached."
    if item["type"] == "stationary":
        if len(player["stationary"]) >= STATIONARY_MAX:
            return False, "Stationary limit reached."
        counts = inventory_counts(player)
        fam = item["family"]
        if fam is not None and counts.get(fam, 0) >= FAMILY_MAX:
            return False, "Family limit reached."
    return True, ""


def apply_purchase(player, item):
    """Subtract gold and add item to proper lists. Handles replacement when flagged."""
    player["gold"] = max(0, player["gold"] - item["cost"])
    player["owned"].append(item["id"])
    if item["type"] == "ring":
        player["rings"].append(item["id"])
    elif item["type"] == "stationary":
        player["stationary"].append(item["id"])
    elif item["type"] == "soda":
        player["sodas"].append(item["id"])


def start_work_session(game_state, timer):
    """Begin a work session unless dev mode skips it."""
    settings = game_state["work_settings"]
    base = settings.get("base_seconds", BASE_WORK_SECONDS)
    game_state["menu_message"] = ""
    if game_state["develop_mode"]:
        # In dev mode, instantly grant rewards and return to menu.
        reward_blocks = max(1, int((base + settings["extra_minutes"] * 30) / 30))
        bonus = 1.0 + settings["extra_minutes"] * EXTRA_MINUTE_BONUS
        gold_gain = int(GOLD_PER_WORK_BLOCK * reward_blocks * bonus)
        player = game_state["player"]
        player["gold"] += gold_gain
        settings["reward_multiplier"] = bonus
        game_state["phase"] = "menu"
        return
    # normal timer start
    total_seconds = base + settings["extra_minutes"] * 30
    settings["reward_multiplier"] = 1.0 + settings["extra_minutes"] * EXTRA_MINUTE_BONUS
    timer.work_seconds = total_seconds
    timer.start_work(demo=False)  # use actual configured duration
    game_state["phase"] = "work"


def finish_work(game_state):
    """Grant work rewards and return to menu."""
    settings = game_state["work_settings"]
    player = game_state["player"]
    base = settings.get("base_seconds", BASE_WORK_SECONDS)
    reward_blocks = max(1, int((base + settings["extra_minutes"] * 30) / 30))
    bonus = settings["reward_multiplier"]
    gold_gain = int(GOLD_PER_WORK_BLOCK * reward_blocks * bonus)
    player["gold"] = max(0, player["gold"] + gold_gain)
    # Reset extra minutes for next session
    settings["extra_minutes"] = 0
    settings["reward_multiplier"] = 1.0
    # Allow battles again
    game_state["rps"]["rounds_since_work"] = 0
    game_state["phase"] = "menu"


def append_log(game_state, player_move_val, enemy_move_val, result, gold_gain, score_info=None):
    """Add one RPS entry to the persistent log with scoring details."""
    rps_state = game_state["rps"]
    entry = {
        "round_number": rps_state["rounds_played"],
        "opponent_id": rps_state["opponent_id"],
        "round_idx": game_state["round"],
        "player_move": player_move_val,
        "enemy_move": enemy_move_val,
        "result": result,
        "gold_gained": gold_gain,
        "heat": game_state["heat"],
        "score_info": score_info or {},
    }
    rps_state["log"].append(entry)
# ---------- Drawing sections ----------

def draw_hud(screen, game_state):
    """Draw top-left HUD with phase/round/gold/score info."""
    phase = game_state["phase"]
    r = game_state["round"] + 1
    h = game_state["heat"] + 1
    rps = game_state["rps"]
    player = game_state["player"]
    work = game_state["work_settings"]
    need_work = (not game_state["develop_mode"] and rps["rounds_since_work"] >= RPS_WORK_GATE)
    phase_text = "Phase: " + phase
    # Show finite target (9) until endless unlocks; then show infinity.
    rps_cap = "\u221e" if game_state.get("endless") else "9"
    rps_line = f"RPS: {rps['rounds_played']}/{rps_cap}"
    line1 = f"{phase_text}   Round {r}/8   Heat {h}/3"
    line2 = f"{rps_line}  Trio: {rps['rounds_since_shop']}/{RPS_ROUNDS_PER_SET}  Gold: {player['gold']}  Score: {player['score']}  Work: {BASE_WORK_SECONDS}s + {work['extra_minutes']}m"
    line3 = f"Multiplier: x{work['reward_multiplier']:.2f}"
    req = required_score(game_state["round"], game_state["heat"])
    line4 = f"Required score this heat: {req} (you: {player['score']})"
    # Decorative panel behind the HUD for readability
    hud_rect = pygame.Rect(PADDING - 8, HUD_Y - 8, int(WIN_W * 0.6), (HUD_LINE + 6) * 5 + 8)
    draw_panel(screen, hud_rect, PANEL, PANEL_OUTLINE, radius=10, border_width=2)

    draw_text(screen, "Jankenpon-Rogue", TITLE_FONT, TEXT, PADDING, HUD_Y)
    draw_text(screen, line1, HUD_FONT, TEXT, PADDING, HUD_Y + HUD_LINE + 4)
    draw_text(screen, line2, HUD_FONT, TEXT, PADDING, HUD_Y + (HUD_LINE + 4) * 2)
    draw_text(screen, line3, HUD_FONT, TEXT, PADDING, HUD_Y + (HUD_LINE + 4) * 3)
    draw_text(screen, line4, HUD_FONT, ACCENT, PADDING, HUD_Y + (HUD_LINE + 4) * 4)
    if need_work:
        draw_text(screen, "Work required before more battles.", HUD_FONT, BAD, PADDING, HUD_Y + (HUD_LINE + 4) * 5)


def draw_inventory_bar(screen, game_state, item_sprites, inv_rects=None):
    """Draw a single horizontal band: Rings | Stationary | Sodas."""
    x = 20
    y = INV_Y
    gap_x = 90
    group_gap = 40

    # Decorative band behind the inventory rows
    band_rect = pygame.Rect(PADDING - 8, y - 36, WIN_W - 2 * PADDING + 16, 130)
    draw_panel(screen, band_rect, PANEL_DARK, PANEL_OUTLINE, radius=8, border_width=2)

    def draw_group(label, start_x, slots, owned_ids):
        draw_text(screen, label, HUD_FONT, SUBTEXT, start_x, y - 20)
        cx = start_x
        for i in range(slots):
            rect = pygame.Rect(cx, y, 80, 80)
            pygame.draw.rect(screen, PANEL, rect, border_radius=4)
            if i < len(owned_ids):
                item_id = owned_ids[i]
                item = ITEMS[item_id]
                sprite = item_sprites[item["sprite_index"]]
                thumb = pygame.transform.scale(sprite, (68, 68))
                screen.blit(thumb, (cx + 6, y + 6))
                if inv_rects is not None:
                    inv_rects.append({"item_id": item_id, "rect": rect})
            else:
                draw_text(screen, "empty", TINY_FONT, SUBTEXT, cx + 10, y + 30)
                if inv_rects is not None:
                    inv_rects.append({"item_id": None, "rect": rect})
            cx += gap_x
        return cx

    player = game_state["player"]
    cx = draw_group("Rings", x, INV_SLOTS["rings"], player["rings"])
    cx += group_gap
    cx = draw_group("Stationary", cx, INV_SLOTS["stationary"], player["stationary"])
    cx += group_gap
    draw_group("Sodas", cx, INV_SLOTS["sodas"], player["sodas"])


def draw_log(screen, game_state):
    """Draw the RPS log on the right side with its own column/panel."""
    log = game_state["rps"]["log"][-5:]
    panel_width = WIN_W - LOG_X - PADDING
    panel_height = 300  # taller to avoid overflow
    panel_rect = pygame.Rect(LOG_X - 6, LOG_Y - 6, panel_width, panel_height)
    draw_panel(screen, panel_rect, (25, 25, 45, 180), PANEL_OUTLINE, radius=10, border_width=2)
    draw_text(screen, "RPS Log (last 5):", HUD_FONT, SUBTEXT, LOG_X + PADDING, LOG_Y + 4)
    y = LOG_Y + 4 + HUD_LINE + 4
    for entry in log:
        si = entry.get("score_info", {})
        total = si.get("total", 0)
        # keep lines short to avoid overflow
        line1 = f"#{entry['round_number']} vs Opp{entry['opponent_id']} (R{entry['round_idx']+1}/H{entry['heat']+1})"
        line2 = f"{entry['result']} (+{entry['gold_gained']}g, +{total}s)"
        draw_text(screen, line1, TINY_FONT, TEXT, LOG_X + PADDING, y)
        y += 16
        draw_text(screen, line2, TINY_FONT, TEXT, LOG_X + PADDING + 12, y)
        y += 18


def draw_items_row(screen, item_ids, item_sprites, y, hover_id=None):
    """Draw a centered row of item cards with name and cost.

    hover_id: if provided, the matching item is drawn slightly larger for emphasis.
    """
    if not item_ids:
        return []
    count = len(item_ids)
    total_width = count * (TILE_W + 200) - 200
    start_x = (WIN_W - total_width) // 2
    rects = []
    x = start_x
    for item_id in item_ids:
        item = ITEMS[item_id]
        sprite = item_sprites[item["sprite_index"]]
        scale = 1.15 if hover_id == item_id else 1.0
        sw = int(TILE_W * scale)
        sh = int(TILE_H * scale)
        sprite_draw = pygame.transform.scale(sprite, (sw, sh)) if scale != 1.0 else sprite
        # center the sprite on the original slot position
        screen.blit(sprite_draw, (x + (TILE_W - sw) // 2, y + (TILE_H - sh) // 2))
        card_width = TILE_W + 180
        name_rect = pygame.Rect(x - 10, y + TILE_H + 6, card_width, 32)
        pygame.draw.rect(screen, PANEL, name_rect, border_radius=6)
        pygame.draw.rect(screen, PANEL_OUTLINE, name_rect, width=1, border_radius=6)
        clean_name = "".join([c for c in item["name"] if not c.isdigit()]).strip()
        draw_text(screen, clean_name, SMALL_FONT, TEXT, name_rect.x + 8, name_rect.y + 6)
        cost_rect = pygame.Rect(x - 10, y + TILE_H + 40, card_width, 24)
        pygame.draw.rect(screen, PANEL_DARK, cost_rect, border_radius=6)
        pygame.draw.rect(screen, PANEL_OUTLINE, cost_rect, width=1, border_radius=6)
        draw_text(screen, f"{item['cost']}g | {item['type'].title()}", SMALL_FONT, ACCENT, cost_rect.x + 8, cost_rect.y + 2)
        rects.append({"item_id": item_id, "rect": pygame.Rect(x, y, TILE_W + 40, TILE_H)})
        x += TILE_W + 200
    return rects


def draw_tooltip(screen, text, pos):
    """Draw a small tooltip near the cursor."""
    surf = SMALL_FONT.render(text, True, TEXT)
    padding = 6
    box_w = surf.get_width() + padding * 2
    box_h = surf.get_height() + padding * 2
    x = pos[0] + 16
    y = pos[1] + 16
    x = max(PADDING, min(x, WIN_W - box_w - PADDING))
    y = max(PADDING, min(y, WIN_H - box_h - PADDING))
    box = pygame.Rect(x, y, box_w, box_h)
    pygame.draw.rect(screen, PANEL, box)
    screen.blit(surf, (box.x + padding, box.y + padding))


def draw_controls(screen, line1, line2=None):
    """Draw controls text at bottom."""
    y = CONTROLS_Y
    draw_text(screen, line1, HUD_FONT, SUBTEXT, PADDING, y)
    if line2:
        draw_text(screen, line2, HUD_FONT, SUBTEXT, PADDING, y + HUD_LINE)


def draw_game_over(screen, game_state):
    """Draw game over screen with message."""
    msg = game_state.get("game_over_msg", "Run failed.")
    draw_text(screen, "Game Over", TITLE_FONT, BAD, 80, 160)
    draw_text(screen, msg, HUD_FONT, TEXT, 80, 210)
    draw_controls(screen, "Press Enter/Space to return to main menu, ESC to quit")


def draw_main_menu(screen, game_state):
    """Draw the start menu."""
    options = ["Start Game", "Settings", "Help / Controls", "Toggle Dev Mode", "Quit"]
    sel = game_state["ui"]["main_menu_index"]
    title_rect = draw_text(screen, "Jankenpon-Rogue", TITLE_FONT, TEXT, 80, 140)
    start_y = title_rect.bottom + 40
    x = 120
    # Decorative panel behind options
    panel_h = len(options) * 60 + 80
    opt_panel = pygame.Rect(x - 20, start_y - 20, 400, panel_h)
    draw_panel(screen, opt_panel, PANEL_DARK, PANEL_OUTLINE, radius=10, border_width=2)
    for idx, opt in enumerate(options):
        rect = pygame.Rect(x, start_y + idx * 60, 340, 48)
        hover = rect.collidepoint(pygame.mouse.get_pos())
        draw_button(screen, rect, opt, HUD_FONT, hover, sel == idx)
    # Split hint into two shorter lines centered under the panel to avoid overflow
    hint1 = "Up/Down: move   Enter/Space: select"
    hint2 = "ESC: quit"
    # Position hints inside the panel near the bottom to avoid overflow
    hint_x = opt_panel.x + 12
    hint_y = opt_panel.bottom - 60
    draw_text(screen, hint1, SMALL_FONT, SUBTEXT, hint_x, hint_y)
    draw_text(screen, hint2, SMALL_FONT, SUBTEXT, hint_x, hint_y + HUD_LINE)
    if game_state["ui"].get("menu_confirm_quit"):
        draw_text(screen, "Confirm quit? Y/N", HUD_FONT, BAD, 80, start_y + len(options) * 60 + 50)
    if game_state.get("menu_message"):
        draw_text(screen, game_state["menu_message"], HUD_FONT, BAD, 80, start_y + len(options) * 60 + 80)


def draw_pause_menu(screen, game_state):
    """Draw the pause menu with exit confirmation."""
    options = ["Resume", "Settings", "Exit Game"]
    sel = game_state["ui"]["pause_menu_index"]
    title_rect = draw_text(screen, "Paused", TITLE_FONT, TEXT, 520, 200)
    start_y = title_rect.bottom + 30
    x = 480
    for idx, opt in enumerate(options):
        rect = pygame.Rect(x, start_y + idx * 60, 300, 48)
        hover = rect.collidepoint(pygame.mouse.get_pos())
        draw_button(screen, rect, opt, HUD_FONT, hover, sel == idx)
    if game_state["ui"]["confirm_exit"]:
        draw_text(screen, "Confirm exit? Y/N", HUD_FONT, BAD, x, start_y + 200)


def draw_settings(screen, game_state):
    """Draw the settings menu."""
    settings = game_state["settings"]
    options = [
        ("Music Volume", f"{int(settings['music_volume']*100)}%"),
        ("SFX Volume", f"{int(settings['sfx_volume']*100)}%"),
        ("Fullscreen", "On" if settings["fullscreen"] else "Off"),
        ("Show Hints", "On" if settings["show_tutorial_hints"] else "Off"),
        ("Back", ""),
    ]
    sel = game_state["ui"]["settings_index"]
    draw_text(screen, "Settings", TITLE_FONT, TEXT, 120, 120)
    start_y = 200
    x = 140
    for i, (label, val) in enumerate(options):
        rect = pygame.Rect(x, start_y + i * 50, 500, 42)
        hover = rect.collidepoint(pygame.mouse.get_pos())
        draw_button(screen, rect, f"{label}: {val}", HUD_FONT, hover, sel == i)
    draw_controls(screen, "Up/Down select, Left/Right adjust, Enter toggle, ESC back")


def draw_help(screen):
    """Draw a simple help / pomodoro description."""
    draw_text(screen, "Help & Controls", TITLE_FONT, TEXT, 120, 80)
    lines = [
        "MENU: SPACE start work, B battle, ESC pause.",
        "BATTLE: R/P/S keys or click buttons. 3 rounds -> shop.",
        "SHOP: 1/2/3 select, Y/Enter confirm, N cancel, hover to see description.",
        "WORK: 30s demo, UP/DOWN adjust +1/-1 minute bonus before starting.",
        "POMODORO: 25m focus + 5m break. After 4, take 15-30m longer break.",
        "Stay on one task, avoid distractions, restart if interrupted.",
        "Use short breaks to move; longer breaks to reset fully.",
    ]
    y = 150
    for line in lines:
        draw_text(screen, line, HUD_FONT, SUBTEXT, 120, y)
        y += 36
    draw_controls(screen, "ESC to return")


def draw_dev_pin(screen, game_state):
    """Draw a PIN pad to enable dev mode."""
    state = game_state.get("dev_pin", {"input": "", "message": ""})
    draw_text(screen, "Enter Dev PIN", TITLE_FONT, TEXT, 120, 120)
    draw_text(screen, "Use keypad or number keys. ESC to cancel.", HUD_FONT, SUBTEXT, 120, 160)
    draw_text(screen, "PIN: " + state["input"], HUD_FONT, ACCENT, 120, 200)
    if state.get("message"):
        draw_text(screen, state["message"], HUD_FONT, BAD, 120, 230)
    # keypad layout
    nums = ["1", "2", "3", "4", "5", "6", "7", "8", "9", " ", "0", " "]
    btns = []
    start_x = 120
    start_y = 260
    w = 80
    h = 60
    idx = 0
    for row in range(4):
        for col in range(3):
            label = nums[idx]
            if label.strip() == "":
                idx += 1
                continue
            rect = pygame.Rect(start_x + col * (w + 10), start_y + row * (h + 10), w, h)
            hover = rect.collidepoint(pygame.mouse.get_pos())
            draw_button(screen, rect, label, HUD_FONT, hover, False)
            btns.append((label, rect))
            idx += 1
    game_state["dev_pin"]["buttons"] = btns


def draw_menu_phase(screen, game_state, item_sprites, item_rects, hover_id):
    """Draw the main in-game menu (not start menu)."""
    draw_hud(screen, game_state)
    draw_inventory_bar(screen, game_state, item_sprites, item_rects)
    draw_log(screen, game_state)
    base = game_state["work_settings"].get("base_seconds", BASE_WORK_SECONDS)
    mode_label = "Pomodoro" if base > BASE_WORK_SECONDS else "Free/Demo"
    center_panel_y = MENU_CENTER_Y
    prompt1 = "SPACE: start work (base {}s, mode {})".format(base, mode_label)
    prompt2 = "UP/DOWN: adjust work time (30s chunks)   B: start R/P/S battle"
    # panel background
    panel_width = WIN_W - PADDING * 2
    panel_height = 150
    menu_panel = pygame.Rect(PADDING, center_panel_y - 60, panel_width, panel_height)
    draw_panel(screen, menu_panel, (30, 35, 55, 120), PANEL_OUTLINE, radius=10, border_width=2)

    draw_text(screen, prompt1, HUD_FONT, TEXT, PADDING + 20, center_panel_y - 30)
    draw_text(screen, prompt2, HUD_FONT, TEXT, PADDING + 20, center_panel_y)
    if game_state.get("menu_message"):
        draw_text(screen, game_state["menu_message"], HUD_FONT, BAD, PADDING + 20, center_panel_y + 30)

    # Action buttons (work / battle / mode)
    btns = []
    labels = [("Start Work", "work"), ("Start Battle", "battle"), ("Toggle Mode", "mode")]
    total_w = len(labels) * 200 + (len(labels) - 1) * 30
    start_x = (WIN_W - total_w) // 2
    y_btn = center_panel_y + 70
    for i, (text_label, action) in enumerate(labels):
        rect = pygame.Rect(start_x + i * 230, y_btn, 200, 44)
        hover = rect.collidepoint(pygame.mouse.get_pos())
        draw_button(screen, rect, text_label, HUD_FONT, hover, False)
        btns.append((action, rect))
    game_state["menu_buttons"] = btns

    # No shop offerings in menu phase
    if hover_id:
        text = ITEMS[hover_id]["description"]
        draw_tooltip(screen, text, clamp_tooltip_pos(pygame.mouse.get_pos()))
    # Inventory hover
    mouse_pos = pygame.mouse.get_pos()
    for rec in item_rects:
        if rec["item_id"] and rec["rect"].collidepoint(mouse_pos):
            draw_tooltip(screen, ITEMS[rec["item_id"]]["description"], clamp_tooltip_pos(mouse_pos))
    # Controls at bottom
    draw_controls(screen, "Controls: SPACE start work | UP/DOWN adjust work | B battle | ESC pause",
                  "R/P/S pick moves | 1/2/3 buy in shop | Y/N confirm")


def draw_battle(screen, game_state, item_sprites):
    """Draw battle UI with choices and latest result."""
    draw_hud(screen, game_state)
    draw_log(screen, game_state)
    inv_rects = []
    draw_inventory_bar(screen, game_state, item_sprites, inv_rects)
    y = 240
    draw_text(screen, "Battle: press R / P / S or click a button. 3 rounds -> shop.", HUD_FONT, TEXT, 20, y)
    bs = game_state["battle_state"]
    btns = []
    bx = 150
    for move in MOVES:
        rect = pygame.Rect(bx, y + 80, 160, 60)
        hover = rect.collidepoint(pygame.mouse.get_pos())
        draw_button(screen, rect, move.upper(), HUD_FONT, hover, False)
        btns.append((move, rect))
        bx += 200
    bs["buttons"] = btns
    gain = bs.get("gold_gain", 0)
    req = required_score(game_state["round"], game_state["heat"])
    draw_text(screen, f"Required score: {req} (you: {game_state['player']['score']})", HUD_FONT, SUBTEXT, 20, y + 140)
    res_line = f"You: {bs.get('player_move', '-')}   Enemy: {bs.get('enemy_move', '-')}   Result: {bs.get('result', 'pending')}   Gold:+{gain}"
    draw_text(screen, res_line, HUD_FONT, SUBTEXT, 20, y + 170)
    # Show last set scoring breakdown
    if bs.get("last_set_score"):
        si = bs["last_set_score"]
        bx = 20
        by = y + 200
        draw_text(screen, f"Base: {si['base_score']} (raw {si['raw_base']} + diversity {si['diversity_bonus']})", TINY_FONT, SUBTEXT, bx, by)
        draw_text(screen, f"Round/Heat mult: x{si['round_mult']:.2f} / x{si['heat_mult']:.2f}", TINY_FONT, SUBTEXT, bx, by + 18)
        draw_text(screen, f"+Mult: +{si['plus_mult']:.2f}   XMult: x{si['x_mult']:.2f}   Synergy: x{si['synergy_mult']:.2f}", TINY_FONT, SUBTEXT, bx, by + 36)
        draw_text(screen, f"Total gained: {si['total']}", HUD_FONT, ACCENT, bx, by + 56)
    draw_controls(screen, "R/P/S to throw, Enter/Space to return after 3 rounds | ESC pause")


def draw_shop(screen, game_state, item_sprites, item_rects, hover_box):
    """Draw shop offers and status."""
    # Always reset confirm button rects each frame
    game_state["shop"]["confirm_rects"] = {}
    draw_hud(screen, game_state)
    inv_rects = []
    draw_inventory_bar(screen, game_state, item_sprites, inv_rects)
    draw_log(screen, game_state)
    player = game_state["player"]
    shop = game_state["shop"]
    draw_text(screen, "Shop Offerings", TITLE_FONT, TEXT, (WIN_W - 240) // 2, 200)
    if shop["pending"]:
        item = ITEMS[shop["pending"]]
        clean_name = "".join([c for c in item["name"] if not c.isdigit()]).strip()
        prompt = f"Buy {clean_name} for {item['cost']}g?"
        confirm = "(Y/Enter confirm, N cancel)"
        draw_text(screen, prompt, HUD_FONT, ACCENT, 20, 268)
        draw_text(screen, confirm, HUD_FONT, ACCENT, 20, 296)
        # Centered clickable Y/N buttons for confirmation (placed above item row)
        btn_w = 120
        btn_h = 44
        gap = 24
        total_w = btn_w * 2 + gap
        start_x = (WIN_W - total_w) // 2
        # Lift the buttons higher to avoid colliding with item sprites
        y_btn = SHOP_ITEMS_Y - 90
        y_rect = pygame.Rect(start_x, y_btn, btn_w, btn_h)
        n_rect = pygame.Rect(start_x + btn_w + gap, y_btn, btn_w, btn_h)
        draw_button(screen, y_rect, "Yes (Y)", HUD_FONT, y_rect.collidepoint(pygame.mouse.get_pos()), False)
        draw_button(screen, n_rect, "No (N)", HUD_FONT, n_rect.collidepoint(pygame.mouse.get_pos()), False)
        shop["confirm_rects"] = {"y": y_rect, "n": n_rect}
    elif shop["message"]:
        draw_text(screen, shop["message"], HUD_FONT, BAD, 20, 240)
    else:
        draw_text(screen, "Select an item with 1/2/3 or click; Enter to leave.", HUD_FONT, SUBTEXT, 20, 240)
        shop["confirm_rects"] = {}
    hover_id = hover_box[0] if hover_box else None
    rects = draw_items_row(screen, shop["offers"], item_sprites, SHOP_ITEMS_Y, hover_id=hover_id)
    item_rects[:] = rects
    if hover_id:
        pos = clamp_tooltip_pos(pygame.mouse.get_pos())
        draw_tooltip(screen, ITEMS[hover_id]["description"], pos)
    # Inventory hover tooltips + track for sell
    mouse_pos = pygame.mouse.get_pos()
    inv_hover = None
    for rec in inv_rects:
        if rec["item_id"] and rec["rect"].collidepoint(mouse_pos):
            inv_hover = rec["item_id"]
            pos = clamp_tooltip_pos(mouse_pos)
            draw_tooltip(screen, ITEMS[rec["item_id"]]["description"], pos)
    if hover_box is not None and len(hover_box) > 1:
        hover_box[1] = inv_hover
    draw_controls(screen, "Shop: 1/2/3 select/buy, Y/Enter confirm, N cancel, S sell hovered owned, Enter to leave, ESC pause")
# ---------- Event handlers ----------

def handle_main_menu_events(events, game_state, running_flag):
    """Handle input for the start menu."""
    options = ["start", "settings", "help", "dev", "quit"]
    idx = game_state["ui"]["main_menu_index"]
    for event in events:
        if event.type == pygame.QUIT:
            running_flag[0] = False
        if event.type == pygame.KEYDOWN:
            # quit confirmation flow
            if game_state["ui"].get("menu_confirm_quit"):
                if event.key in (pygame.K_y, pygame.K_RETURN, pygame.K_SPACE):
                    running_flag[0] = False
                if event.key in (pygame.K_n, pygame.K_ESCAPE):
                    game_state["ui"]["menu_confirm_quit"] = False
                    game_state["menu_message"] = ""
                continue
            if event.key == pygame.K_ESCAPE:
                running_flag[0] = False
            if event.key == pygame.K_DOWN:
                idx = (idx + 1) % len(options)
            if event.key == pygame.K_UP:
                idx = (idx - 1) % len(options)
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                choice = options[idx]
                if choice == "start":
                    game_state["phase"] = "menu"
                elif choice == "settings":
                    game_state["prev_phase"] = "main_menu"
                    game_state["phase"] = "settings"
                elif choice == "help":
                    game_state["prev_phase"] = "main_menu"
                    game_state["phase"] = "help"
                elif choice == "dev":
                    game_state["dev_pin"] = {"input": "", "message": ""}
                    game_state["phase"] = "dev_pin"
                elif choice == "quit":
                    game_state["ui"]["menu_confirm_quit"] = True
                    game_state["menu_message"] = "Confirm quit? Y/N"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            title_rect = pygame.Rect(80, 140, 400, 40)
            start_y = title_rect.bottom + 40
            for i in range(len(options)):
                rect = pygame.Rect(120, start_y + i * 60, 300, 48)
                if rect.collidepoint((mx, my)):
                    idx = i
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    game_state["ui"]["main_menu_index"] = idx


def handle_pause_menu_events(events, game_state, running_flag):
    """Handle pause menu interactions (with dev mode option)."""
    options = ["resume", "settings", "dev", "exit"]
    idx = game_state["ui"]["pause_menu_index"]
    for event in events:
        if event.type == pygame.QUIT:
            running_flag[0] = False
        if event.type == pygame.KEYDOWN:
            if game_state["ui"]["confirm_exit"]:
                if event.key in (pygame.K_y, pygame.K_RETURN, pygame.K_SPACE):
                    running_flag[0] = False
                if event.key in (pygame.K_n, pygame.K_ESCAPE):
                    game_state["ui"]["confirm_exit"] = False
                continue
            if event.key == pygame.K_ESCAPE:
                game_state["phase"] = game_state.get("prev_phase", "menu")
            if event.key == pygame.K_DOWN:
                idx = (idx + 1) % len(options)
            if event.key == pygame.K_UP:
                idx = (idx - 1) % len(options)
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                choice = options[idx]
                if choice == "resume":
                    game_state["phase"] = game_state.get("prev_phase", "menu")
                elif choice == "settings":
                    game_state["prev_phase"] = "pause_menu"
                    game_state["phase"] = "settings"
                elif choice == "dev":
                    game_state["prev_phase"] = "pause_menu"
                    game_state["phase"] = "dev_pin"
                elif choice == "exit":
                    game_state["ui"]["confirm_exit"] = True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            title_rect = pygame.Rect(520, 200, 200, 40)
            start_y = title_rect.bottom + 30
            for i in range(len(options)):
                rect = pygame.Rect(480, start_y + i * 60, 300, 48)
                if rect.collidepoint((mx, my)):
                    idx = i
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    game_state["ui"]["pause_menu_index"] = idx


def handle_settings_events(events, game_state):
    """Process settings adjustments."""
    settings = game_state["settings"]
    idx = game_state["ui"]["settings_index"]
    options = 5
    for event in events:
        if event.type == pygame.QUIT:
            return "quit"
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                game_state["phase"] = game_state.get("prev_phase", "menu")
                save_settings(settings)
            if event.key == pygame.K_DOWN:
                idx = (idx + 1) % options
            if event.key == pygame.K_UP:
                idx = (idx - 1) % options
            if event.key == pygame.K_LEFT:
                if idx == 0:
                    settings["music_volume"] = max(0, settings["music_volume"] - 0.01)
                if idx == 1:
                    settings["sfx_volume"] = max(0, settings["sfx_volume"] - 0.01)
            if event.key == pygame.K_RIGHT:
                if idx == 0:
                    settings["music_volume"] = min(1, settings["music_volume"] + 0.01)
                if idx == 1:
                    settings["sfx_volume"] = min(1, settings["sfx_volume"] + 0.01)
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if idx == 2:
                    settings["fullscreen"] = not settings["fullscreen"]
                if idx == 3:
                    settings["show_tutorial_hints"] = not settings["show_tutorial_hints"]
                if idx == 4:
                    game_state["phase"] = game_state.get("prev_phase", "menu")
                    save_settings(settings)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            x = 140
            start_y = 200
            for i in range(options):
                rect = pygame.Rect(x, start_y + i * 50, 500, 42)
                if rect.collidepoint((mx, my)):
                    idx = i
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    game_state["ui"]["settings_index"] = idx


def handle_help_events(events, game_state):
    """Handle closing the help screen."""
    for event in events:
        if event.type == pygame.QUIT:
            return "quit"
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                game_state["phase"] = game_state.get("prev_phase", "menu")
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                game_state["phase"] = game_state.get("prev_phase", "menu")


def handle_game_over_events(events, game_state, running_flag):
    """Handle game over inputs."""
    for event in events:
        if event.type == pygame.QUIT:
            running_flag[0] = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running_flag[0] = False
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                # reset minimal state, preserve dev mode flag
                dev_flag = game_state.get("develop_mode", False)
                new_state = create_game_state()
                new_state["develop_mode"] = dev_flag
                game_state.clear()
                game_state.update(new_state)
                game_state["endless"] = False


def handle_dev_pin_events(events, game_state):
    """Handle PIN entry for dev mode."""
    state = game_state.get("dev_pin", {"input": "", "message": ""})
    for event in events:
        if event.type == pygame.QUIT:
            return "quit"
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                game_state["phase"] = "main_menu"
            if event.unicode.isdigit():
                state["input"] += event.unicode
                state["input"] = state["input"][:4]
                beep()
            if event.key == pygame.K_BACKSPACE:
                state["input"] = state["input"][:-1]
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for label, rect in state.get("buttons", []):
                if rect.collidepoint((mx, my)):
                    state["input"] += label
                    state["input"] = state["input"][:4]
                    beep()
        # check length
        if len(state["input"]) == 4:
            if state["input"] == DEV_PIN:
                game_state["develop_mode"] = True
                game_state["menu_message"] = "Dev mode enabled."
                state["message"] = "Success."
                state["input"] = ""
                game_state["phase"] = "main_menu"
            else:
                state["message"] = "Incorrect PIN."
                state["input"] = ""
    game_state["dev_pin"] = state


def handle_menu_events(events, game_state, timer, item_rects, hover_id_box):
    """Handle input in the in-game menu phase."""
    ws = game_state["work_settings"]
    for event in events:
        if event.type == pygame.QUIT:
            return "quit"
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                game_state["prev_phase"] = "menu"
                game_state["phase"] = "pause_menu"
            if game_state["ui"].get("menu_confirm_quit"):
                if event.key in (pygame.K_y, pygame.K_RETURN, pygame.K_SPACE):
                    return "quit"
                if event.key in (pygame.K_n, pygame.K_ESCAPE):
                    game_state["ui"]["menu_confirm_quit"] = False
                    game_state["menu_message"] = ""
            if event.key == pygame.K_SPACE:
                start_work_session(game_state, timer)
            if event.key == pygame.K_b:
                # gate battles if too many since last work (unless dev mode)
                need_break = (not game_state["develop_mode"] and game_state["rps"]["rounds_since_work"] >= RPS_WORK_GATE)
                if need_break:
                    game_state["menu_message"] = "Do a quick work session before more battles."
                else:
                    game_state["menu_message"] = ""
                    game_state["phase"] = "battle"
            if event.key == pygame.K_UP:
                ws["extra_minutes"] = min(ws["extra_minutes"] + 1, MAX_EXTRA_MINUTES)
                ws["reward_multiplier"] = 1.0 + ws["extra_minutes"] * EXTRA_MINUTE_BONUS
            if event.key == pygame.K_DOWN:
                ws["extra_minutes"] = max(ws["extra_minutes"] - 1, 0)
                ws["reward_multiplier"] = 1.0 + ws["extra_minutes"] * EXTRA_MINUTE_BONUS
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            hover_id_box[0] = None
            for rec in item_rects:
                if rec["rect"].collidepoint((mx, my)):
                    hover_id_box[0] = rec["item_id"]
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # action buttons
            for action, rect in game_state.get("menu_buttons", []):
                if rect.collidepoint((mx, my)):
                    if action == "work":
                        start_work_session(game_state, timer)
                    elif action == "battle":
                        need_break = (not game_state["develop_mode"] and game_state["rps"]["rounds_since_work"] >= RPS_WORK_GATE)
                        if need_break:
                            game_state["menu_message"] = "Do a quick work session before more battles."
                        else:
                            game_state["menu_message"] = ""
                            game_state["phase"] = "battle"
                    elif action == "mode":
                        # toggle base_seconds between demo and pomodoro (25 min)
                        if ws.get("base_seconds", BASE_WORK_SECONDS) > BASE_WORK_SECONDS:
                            ws["base_seconds"] = BASE_WORK_SECONDS
                            game_state["menu_message"] = "Mode set to Free/Demo (30s base)."
                        else:
                            ws["base_seconds"] = 1500
                            game_state["menu_message"] = "Mode set to Pomodoro (25 min base)."


def handle_battle_events(events, game_state):
    """Handle RPS battle choices."""
    bs = game_state["battle_state"]
    for event in events:
        if event.type == pygame.QUIT:
            return "quit"
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                game_state["prev_phase"] = "battle"
                game_state["phase"] = "pause_menu"
            move = None
            if event.key == pygame.K_r:
                move = "rock"
            if event.key == pygame.K_p:
                move = "paper"
            if event.key == pygame.K_s:
                move = "scissors"
            if move:
                resolve_battle_round(game_state, move)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for move, rect in bs.get("buttons", []):
                if rect.collidepoint((mx, my)):
                    resolve_battle_round(game_state, move)


def resolve_battle_round(game_state, player_move_val):
    """Compute a single RPS round and update log/state."""
    bs = game_state["battle_state"]
    rps_state = game_state["rps"]
    enemy_val = enemy_move()
    result = resolve_round(player_move_val, enemy_val)
    gold_gain = RPS_REWARD_LOSE
    if result == "win":
        gold_gain = RPS_REWARD_WIN
    elif result == "tie":
        gold_gain = RPS_REWARD_TIE
    game_state["player"]["gold"] = max(0, game_state["player"]["gold"] + gold_gain)

    # If tie, log it but do NOT count it toward the 3-hand set; replay until win/lose.
    if result == "tie":
        append_log(game_state, player_move_val, enemy_val, result, gold_gain, None)
        bs["player_move"] = player_move_val
        bs["enemy_move"] = enemy_val
        bs["result"] = result
        bs["gold_gain"] = gold_gain
        bs["message"] = "Tie: replay this hand."
        return

    # track set (only wins/losses count toward the 3-hand set)
    bs.setdefault("results", []).append(result)
    bs.setdefault("moves", []).append(player_move_val)

    rps_state["rounds_played"] += 1
    rps_state["rounds_since_shop"] += 1
    rps_state["rounds_since_work"] += 1
    rps_state["opponent_id"] += 1

    append_log(game_state, player_move_val, enemy_val, result, gold_gain, None)

    if len(bs["results"]) >= RPS_ROUNDS_PER_SET:
        # reset score each set; only RPS hands contribute
        game_state["player"]["score"] = 0
        set_summary = {
            "results": bs["results"],
            "moves": bs["moves"],
            "round": game_state["round"],
            "heat": game_state["heat"],
            "set_streak": rps_state.get("set_streak", 0),
        }
        score_info = calculate_set_score(set_summary, game_state)
        # Reset score per set to enforce per-hand clear
        game_state["player"]["score"] = 0
        # Exponential bump in endless mode based on sets completed
        total_sets = max(1, rps_state["rounds_played"] // RPS_ROUNDS_PER_SET)
        total_apply = score_info["total"]
        if game_state.get("endless"):
            total_apply = int(total_apply * (ENDLESS_MULT_BASE ** total_sets))
            score_info["total"] = total_apply
        game_state["player"]["score"] += total_apply
        append_log(game_state, "-", "-", "set_total", 0, score_info)
        bs["last_set_score"] = score_info
        # Gate immediately after the set is scored (before shop)
        required = required_score(game_state["round"], game_state["heat"])
        if game_state["player"]["score"] < required and not game_state.get("endless"):
            game_state["game_over_msg"] = f"Required score {required}, you had {game_state['player']['score']}."
            bs["results"] = []
            bs["moves"] = []
            game_state["phase"] = "game_over"
            return
        # streak update (W>=2)
        if bs["results"].count("win") >= 2:
            rps_state["set_streak"] = rps_state.get("set_streak", 0) + 1
        else:
            rps_state["set_streak"] = 0
        # reset set data
        bs["results"] = []
        bs["moves"] = []
        rps_state["rounds_since_shop"] = 0
        game_state["shop"]["offers"] = choose_shop_offers()
        game_state["shop"]["pending"] = None
        game_state["shop"]["message"] = ""
        game_state["phase"] = "shop"

    bs["player_move"] = player_move_val
    bs["enemy_move"] = enemy_val
    bs["result"] = result
    bs["gold_gain"] = gold_gain
    if (not game_state.get("endless")) and rps_state["rounds_played"] >= RPS_SET_MAX:
        game_state["endless"] = True
        game_state["menu_message"] = "Endless mode unlocked."


def handle_shop_events(events, game_state, item_rects, hover_id_box):
    """Keyboard and mouse interactions in the shop."""
    shop = game_state["shop"]
    player = game_state["player"]
    inv_hover = hover_id_box[1] if len(hover_id_box) > 1 else None
    for event in events:
        if event.type == pygame.QUIT:
            return "quit"
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                game_state["prev_phase"] = "shop"
                game_state["phase"] = "pause_menu"
            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                idx = int(event.unicode) - 1
                if idx < len(shop["offers"]):
                    shop["pending"] = shop["offers"][idx]
                    shop["message"] = ""
            if shop["pending"]:
                if event.key in (pygame.K_y, pygame.K_RETURN, pygame.K_SPACE):
                    item = ITEMS[shop["pending"]]
                    ok, reason = can_buy(player, item)
                    if ok:
                        apply_purchase(player, item)
                        shop["message"] = f"Purchased {item['name']}."
                        shop["pending"] = None
                    else:
                        # allow override: replace oldest of that type
                        if item["type"] == "ring" and player["rings"]:
                            old = player["rings"].pop(0)
                            if old in player["owned"]:
                                player["owned"].remove(old)
                            shop["message"] = f"Replaced {old} with {item['name']}."
                            apply_purchase(player, item)
                            shop["pending"] = None
                        elif item["type"] == "stationary" and player["stationary"]:
                            old = player["stationary"].pop(0)
                            if old in player["owned"]:
                                player["owned"].remove(old)
                            shop["message"] = f"Replaced {old} with {item['name']}."
                            apply_purchase(player, item)
                            shop["pending"] = None
                        else:
                            shop["message"] = "Cannot buy: " + reason
                if event.key == pygame.K_n:
                    shop["pending"] = None
            else:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    # advance heat/round
                    game_state["heat"] += 1
                    if game_state["heat"] >= 3:
                        game_state["heat"] = 0
                        game_state["round"] = min(game_state["round"] + 1, 7)
                    game_state["phase"] = "menu"
            if event.key == pygame.K_s and inv_hover:
                itm = ITEMS[inv_hover]
                sell_price = max(1, int(itm["cost"] * SELL_DISCOUNT))
                player["gold"] += sell_price
                shop["message"] = f"Sold {itm['name']} for {sell_price}g."
                # remove from inventories
                if itm["id"] in player["rings"]:
                    player["rings"].remove(itm["id"])
                if itm["id"] in player["stationary"]:
                    player["stationary"].remove(itm["id"])
                if itm["id"] in player["sodas"]:
                    player["sodas"].remove(itm["id"])
                if itm["id"] in player["owned"]:
                    player["owned"].remove(itm["id"])
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            hover_id_box[0] = None
            for rec in item_rects:
                if rec["rect"].collidepoint((mx, my)):
                    hover_id_box[0] = rec["item_id"]
            # inventory hover captured elsewhere; keep in box[1]
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # clickable confirmation buttons when pending
            if shop["pending"] and shop.get("confirm_rects"):
                if shop["confirm_rects"].get("y") and shop["confirm_rects"]["y"].collidepoint((mx, my)):
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_y))
                if shop["confirm_rects"].get("n") and shop["confirm_rects"]["n"].collidepoint((mx, my)):
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n))
            for rec in item_rects:
                if rec["rect"].collidepoint((mx, my)):
                    shop["pending"] = rec["item_id"]
                    shop["message"] = ""


def handle_work_update(game_state, timer, dt):
    """Advance timer; on finish, grant rewards."""
    timer.tick(dt)
    if timer.finished():
        finish_work(game_state)


# ---------- Main loop ----------

def main():
    """Entry point: initialize PyGame, state, and run loop."""
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Jankenpon-Rogue")

    clock = pygame.time.Clock()
    item_sprites = load_item_sprites()
    timer = PomodoroTimer(work_seconds=BASE_WORK_SECONDS, break_seconds=10)
    game_state = create_game_state()
    game_state["endless"] = False
    ensure_battle_state(game_state)
    running = [True]

    shop_item_rects = []
    hover_id_box = [None, None]  # [offer_hover, inventory_hover]
    menu_item_rects = []
    menu_hover_box = [None]

    while running[0]:
        dt = clock.tick(FPS) / 1_000.0
        events = pygame.event.get()

        if game_state["phase"] == "main_menu":
            handle_main_menu_events(events, game_state, running)
        elif game_state["phase"] == "dev_pin":
            res = handle_dev_pin_events(events, game_state)
            if res == "quit":
                running[0] = False
        elif game_state["phase"] == "pause_menu":
            handle_pause_menu_events(events, game_state, running)
        elif game_state["phase"] == "settings":
            res = handle_settings_events(events, game_state)
            if res == "quit":
                running[0] = False
        elif game_state["phase"] == "help":
            res = handle_help_events(events, game_state)
            if res == "quit":
                running[0] = False
        elif game_state["phase"] == "game_over":
            handle_game_over_events(events, game_state, running)
        elif game_state["phase"] == "menu":
            res = handle_menu_events(events, game_state, timer, menu_item_rects, menu_hover_box)
            if res == "quit":
                running[0] = False
        elif game_state["phase"] == "battle":
            res = handle_battle_events(events, game_state)
            if res == "quit":
                running[0] = False
        elif game_state["phase"] == "shop":
            res = handle_shop_events(events, game_state, shop_item_rects, hover_id_box)
            if res == "quit":
                running[0] = False
        elif game_state["phase"] == "work":
            for event in events:
                if event.type == pygame.QUIT:
                    running[0] = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    game_state["prev_phase"] = "work"
                    game_state["phase"] = "pause_menu"
            handle_work_update(game_state, timer, dt)

        screen.fill(BG)
        if game_state["phase"] == "main_menu":
            draw_main_menu(screen, game_state)
        elif game_state["phase"] == "dev_pin":
            draw_dev_pin(screen, game_state)
        elif game_state["phase"] == "pause_menu":
            draw_pause_menu(screen, game_state)
        elif game_state["phase"] == "settings":
            draw_settings(screen, game_state)
        elif game_state["phase"] == "help":
            draw_help(screen)
        elif game_state["phase"] == "game_over":
            draw_game_over(screen, game_state)
        elif game_state["phase"] == "menu":
            menu_item_rects.clear()
            draw_menu_phase(screen, game_state, item_sprites, menu_item_rects, menu_hover_box[0])
        elif game_state["phase"] == "battle":
            draw_battle(screen, game_state, item_sprites)
        elif game_state["phase"] == "shop":
            shop_item_rects.clear()
            draw_shop(screen, game_state, item_sprites, shop_item_rects, hover_id_box)
        elif game_state["phase"] == "work":
            # Work screen: center timer and minimal overlap
            draw_hud(screen, game_state)
            remaining = max(0, int(timer.remaining))
            mins = remaining // 60
            secs = remaining % 60
            time_str = f"{mins:02d}:{secs:02d}"
            time_surf = TITLE_FONT.render(time_str, True, ACCENT)
            time_rect = time_surf.get_rect(center=(WIN_W // 2, WIN_H // 2 - 40))
            screen.blit(time_surf, time_rect)
            draw_controls(screen, "Timer running. ESC pause.")

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
