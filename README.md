# Jankenpon-Rogue
Team: Jadyn D'Cruz

## Big Idea / Goal
Jankenpon-Rogue is a Rock–Paper–Scissors roguelike Pomodoro game. You play short RPS battles in sets of rounds, earn gold and score, and spend that gold in a shop on Sodas (temporary buffs), Rings (passive bonuses), and Stationary (synergy items)—all gated by work sessions. The full run is framed as 8 rounds with 3 heats each and rising score requirements, inspired by Balatro, Slay the Spire, Hades, and Dead Cells. Audience: students/procrastinators/productivity nerds who like roguelikes and want to “gamify” focused work.

Screenshots to add:
- Menu/HUD with round/heat, log, and required score.
- RPS battle in progress with scoring breakdown.
- Shop with items + inventory bar + tooltips.
- Work timer screen/reward summary.

## User Instructions
- Requirements: Python 3.11+; `pip install -r requirements.txt`.
- Setup:
  - `python -m venv .venv`
  - Windows: `.venv\Scripts\activate` | macOS/Linux: `source .venv/bin/activate`
  - `pip install -r requirements.txt`
- Run: `python main.py`
- Assets: ensure `assets/items_sheet.png` exists (or placeholders will be used).
- Controls:
  - Main menu: Up/Down + Enter/Space or mouse; ESC quits.
  - Menu phase: SPACE start work; UP/DOWN adjust ±1 “minute” (30s chunk); B start battle; ESC pause; Toggle Mode button switches 30s base ↔ 25m Pomodoro base.
  - Battle: R/P/S keys or click buttons; auto-shop after 3 rounds.
  - Shop: 1/2/3 select; Y/Enter confirm; N cancel; S sell hovered owned item; hover for description; Enter/Space leave; ESC pause.
  - Work: timer runs; ESC pause.
  - PIN pad for dev mode: numeric keys or mouse; ESC back.

## Implementation Information
- North star (also used in-help): Rock–Paper–Scissors roguelike Pomodoro game with Sodas/Rings/Stationary, 8 rounds × 3 heats, inspired by Balatro/StS/Hades/Dead Cells.
- Architecture:
  - `main.py` – phase routing (main menu, dev PIN, menu, battle, shop, work, pause, game_over), rendering, input.
  - `timer.py` – PomodoroTimer (start, tick, finished).
  - `game_state.py` – state factory, heat/score requirements, settings load/save.
  - `items.py` – item registry (20 sodas, 20 rings, 20 stationary) with effects metadata.
  - `rps.py` – moves, enemy choice, resolve round.
  - `scoring.py` – Balatro-inspired scoring (base/add/x-mult, synergies, sodas).
- Flow and gating: Work → Battle (3 rounds) → Shop, repeat; work gate after 9 RPS rounds; score requirement per heat (Balatro-like scaling) must be met or game over.
- Items and synergies:
  - Sodas: one-time gold/score boosts (e.g., Jolt Cola double next win score, Focus Shot +50% score, Power Tonic +2g).
  - Rings: passive score/gold (Flow State +20% score, Lucky Band +1g/round).
  - Stationary: conditional boosts vs specific moves (Sharp Pencil vs paper, Beefy Eraser vs rock) with family slots and overall slot limits.
  - Synergy examples: Sharp Pencil + Beefy Eraser → bonus multiplier; families (pencil/paper/scissors) interact with targeted move boosts.
- Influences: Balatro (score/ante scaling, modular “joker-like” items), Slay the Spire (synergy-driven loadouts), Hades/Dead Cells (heat-like progression).
- Assets to create/use (suggested): simple 10×6 item sheet (placeholder colors OK), icons for Sodas/Rings/Stationary, background panel/box sprites, small font (e.g., Consolas or similar), optional RPS hand icons for battle buttons.

## Game Mechanics: Scoring Details
- Round/heat scaling: base score scales by round and heat (Balatro “ante”-like), plus a streak bonus.
- Multipliers: +Mult (additive) and XMult (multiplicative) applied in Balatro order: (base + add) × XMult.
- Synergies: defined pairs (e.g., Sharp Pencil + Beefy Eraser) grant extra XMult; families stack targeted bonuses.
- Consumables (Sodas): one-use effects (double score, +50% score, +2 gold, temporary XMult spikes); consumed after triggering.
- Score gating: each heat has a required score; fail → game over; endless mode shows RPS as X/∞.
- Scoring breakdown shown in HUD: Base / +Mult / XMult / Synergy / Total.

## Results
- Current MVP loop: Work timer (30s base + adjustable chunks or Pomodoro base) grants gold/score; RPS battles grant gold/score with item effects; every 3 rounds → shop; score gate per heat; inventory bar and hover tooltips; RPS log (last 5) top-right.
- Visual evidence (to capture):
  - Battle HUD with round/heat, log, required score line, scoring breakdown.
  - Shop with 3 offers, confirmations, sell option, inventory bar.
  - Work timer screen and rewards.
- Playthrough summary: Start work → run 3 RPS rounds → shop → repeat; after 9 rounds, work required; meet score requirement to advance heats/rounds; fail = game over; RPS shows X/∞ for endless mode.

## Project Evolution
- Step 1: Minimal PyGame loop, timer, three sample items, placeholder sprites.
- Step 2: Added RPS logic, auto-shop, item families, gating, hover tooltips, inventory bar, log.
- Step 3: Roguelike polish—score gates, expanded item set (20/20/20), selling/replacing, endless RPS display, PIN pad with beeps, layout fixes, Balatro-style scoring engine.
- Challenges: UI overlap/positioning; phase transitions; balancing gold/score vs gating; enforcing item limits; integrating Balatro-like scoring without breaking flow.
- Lessons: State-driven architecture; simple data-first (dict) design; incremental refactor improves stability; isolating UI regions prevents overlap.

## Attribution
- Libraries: PyGame.
- Art: `assets/items_sheet.png` (placeholder/custom; replace with licensed sprites for distribution).
- Inspirations/Research: Balatro (score scaling/modular items), Slay the Spire (synergies/loadouts), Hades/Dead Cells (heat/progression).
- Tools: ChatGPT-assisted design/coding; all code reviewed and understood by author.
- People: Course staff/peers for feedback.
