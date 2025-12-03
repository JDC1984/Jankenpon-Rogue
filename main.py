"""
Step 1 game entrypoint.
Creates the window, loads the sprite sheet, and shows three test items plus
an optional demo Pomodoro timer. Code intentionally mirrors ThinkPython
patterns: plain functions, dictionaries, and loops.
"""

import sys
import time

try:
    import pygame  # outside info: third-party library for graphics and input
except ImportError as exc:
    # Provide a clear hint instead of a NameError when pygame is missing.
    print("PyGame is not installed. Install with `pip install -r requirements.txt`.")
    raise

from timer import PomodoroTimer
from game_state import create_game_state
from items import ITEMS

# --- sprite sheet layout constants ---
TILE_W = 64       # width of one item tile (pixels)
TILE_H = 96       # height of one item tile (pixels)
SHEET_COLS = 10   # 10 tiles per row in the sheet
SHEET_ROWS = 6    # 6 rows -> 60 tiles total
SHEET_PATH = "assets/items_sheet.png"


def load_item_sprites(path, font):
    """Load the sprite sheet and slice it into individual tiles.

    If the file is missing/unreadable, fall back to generated placeholder
    tiles so the program still runs without assets.
    """
    try:
        sheet = pygame.image.load(path).convert_alpha()
        sprites = []

        for row in range(SHEET_ROWS):
            for col in range(SHEET_COLS):
                x = col * TILE_W
                y = row * TILE_H
                rect = pygame.Rect(x, y, TILE_W, TILE_H)

                # subsurface creates a new Surface view onto the sheet pixels.
                tile = sheet.subsurface(rect)
                sprites.append(tile)

        return sprites
    except (pygame.error, FileNotFoundError) as e:
        # Gracefully continue with generated tiles instead of exiting.
        print(f"Warning: could not load {path}: {e}")
        print("Using placeholder tiles so the demo still runs.")

    # Build 60 placeholder tiles with distinct colors and an index label.
    sprites = []
    for i in range(SHEET_ROWS * SHEET_COLS):
        surf = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)

        # Simple color variation by index (modulo to stay in range).
        color = (
            60 + (i * 40) % 150,
            40 + (i * 70) % 150,
            90 + (i * 90) % 150,
        )
        surf.fill(color)

        # Label the tile with its index so ordering is visible.
        label = font.render(str(i), True, (0, 0, 0))
        label_rect = label.get_rect(center=(TILE_W // 2, TILE_H // 2))
        surf.blit(label, label_rect)
        sprites.append(surf)

    return sprites


def draw_item(surface, sprite_list, item_dict, x, y):
    """Draw one item on the given surface at (x, y)."""
    index = item_dict["sprite_index"]
    sprite = sprite_list[index]
    surface.blit(sprite, (x, y))


def main():
    # Initialize PyGame subsystems (window, input, fonts).
    pygame.init()

    # Create the main window.
    width, height = 960, 540
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("LMARENA - Step 1")

    # Choose fonts for UI and item labels (labels a bit smaller to avoid overlap).
    font = pygame.font.SysFont("consolas", 24)
    item_font = pygame.font.SysFont("consolas", 20)

    # Load/slice the sprite sheet (or fall back to placeholders if missing).
    item_sprites = load_item_sprites(SHEET_PATH, font)

    # Create initial dictionaries for the player and round progression.
    game_state = create_game_state()
    timer = PomodoroTimer()

    clock = pygame.time.Clock()
    last_time = time.time()

    running = True
    while running:
        # Compute dt, the time since the last frame (seconds, float).
        now = time.time()
        dt = now - last_time
        last_time = now

        # Limit to ~60 FPS so dt stays stable.
        clock.tick(60)

        # --- handle input/events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                if event.key == pygame.K_SPACE and game_state["phase"] == "menu":
                    # SPACE starts a short work timer demo.
                    game_state["phase"] = "work"
                    timer.start_work(demo=True)

        # --- update logic ---
        if game_state["phase"] == "work":
            timer.tick(dt)
            if timer.finished():
                # For Step 1 we bounce back to the menu when the timer ends.
                game_state["phase"] = "menu"

        # --- draw UI ---
        screen.fill((10, 10, 30))  # dark blue background

        title_surf = font.render("LMARENA - Step 1", True, (255, 255, 255))
        screen.blit(title_surf, (20, 20))

        phase_text = "Phase: " + game_state["phase"]
        phase_surf = font.render(phase_text, True, (200, 200, 200))
        screen.blit(phase_surf, (20, 60))

        if game_state["phase"] == "work":
            timer_text = f"Work timer: {int(timer.remaining)}s"
            timer_surf = font.render(timer_text, True, (200, 200, 0))
            screen.blit(timer_surf, (20, 100))
        else:
            hint_text = "Press SPACE to start demo work timer"
            hint_surf = font.render(hint_text, True, (150, 150, 150))
            screen.blit(hint_surf, (20, 100))

        # Draw three example items to confirm sprite sheet slicing.
        x = 40
        y = 220
        spacing = 80  # extra space to keep long names from overlapping

        for item_id in ["soda_jolt_cola", "ring_flow_state", "st_sharp_pencil"]:
            item = ITEMS[item_id]
            draw_item(screen, item_sprites, item, x, y)

            # Label beneath the sprite to connect ids to visuals.
            label = item_font.render(item["name"], True, (220, 220, 220))
            # Center the label under the tile so text stays readable.
            label_rect = label.get_rect(center=(x + TILE_W // 2, y + TILE_H + 18))
            screen.blit(label, label_rect.topleft)

            x += TILE_W + spacing

        # Swap buffers to display the rendered frame.
        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
