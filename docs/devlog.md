# Devlog

## 2025-11-10
- Scaffolded Step 1 minimal PyGame project per notebook-friendly plan.
- Added Pomodoro timer, dictionary-based game state, and three sample items.
- Built PyGame main loop that renders sample items and demo timer prompt.
- Added requirements.txt and placeholder asset note for items_sheet.png.
- Added rock-paper-scissors battle hook (press B, then R/P/S; Enter/Space to exit battle).
- Improved item label layout and ensured placeholder tiles render when the sprite sheet is missing.
- Added adjustable work timer (UP/DOWN to add minutes, +5% reward per extra minute), auto-start on boot, and simple shop/round progression with earned gold/score.
- Centered item labels with bounding boxes to prevent overlaps between adjacent items.
- HUD shows phase, round/heat, gold/score, work settings; centered item row with boxed labels; controls hint always visible.
