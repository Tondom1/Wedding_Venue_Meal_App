# CLAUDE.md — Standing instructions for the Wedding Venue Meal App

Read this file at the start of every session in this folder. It records what the owner wants, what is already built, and the rules that came from `PLAN.md`. If this file and a request ever conflict, ask the owner before acting.

---

## 1. Who this is for and why

- The owner runs a **wedding/event venue** and plans the food for events.
- They keep their own recipe database. **They type in all meal data themselves**: names, ingredients, amounts and recipes. Never invent, import or "fill in" meal data.
- The app's job is to answer one question: **"For this meal and this number of guests, what do I need to buy, and how much of each thing?"**
- It runs **locally on the owner's Windows PC** for one user. There is no login and no hosting (see section 7).

## 2. Current state (as of 2026-10-08)

Everything in `PLAN.md` (Phases 1–6) **is built and working** in `app.py`, `schema.sql` and `templates/`:
- add, edit and delete meals (name, ingredients one per line, recipe, optional photo)
- a home page grid with search by meal name or ingredient
- a detail page with the ingredient bullet list and recipe
- photo upload with uuid filenames, an extension allow-list, a 5 MB limit, and cleanup on replace or delete
- 404 and 413 handling, plus flash messages

Housekeeping notes:
- The `[ ]` checkboxes in `PLAN.md` were never ticked, even though the work is done. Don't take that to mean the work is missing.
- `PLAN.md` says the folder is `meal-app/`. The real folder is `C:\Claude Projects\Wedding_Venue_Meal_App`.
- `PLAN.md` asks for Python 3.10+, but `README.md` says 3.9+ and `__pycache__` shows **Python 3.9** in use. Keep code **3.9-compatible**: no `match`, and no `X | Y` type hints.
- There is no `instance/` folder in this copy. The owner's real `meals.db` may be in a different copy of the app. Assume real data exists somewhere and treat it as precious.
- `future_plans.md` (login, CSRF, hosting) is **not started**. Don't work on it unless the owner asks.

## 3. Fixed rules carried over from PLAN.md (always follow)

**Stack, which must not change:** Python + **Flask only** (server-rendered Jinja2), the built-in `sqlite3` module, and Pico.css from the CDN. No other pip packages, no ORM, no JS framework, no build step. Small inline vanilla JS is fine only if it's truly necessary. Prefer plain HTML forms.

**Platform:** Windows. Give commands in **PowerShell** form, e.g. `.\.venv\Scripts\python -m flask --app app run`.

**Way of working:**
- Keep it simple and don't add features the owner didn't ask for.
- Work in small phases. After each phase, list the manual "Check" steps and confirm they pass.
- When a plan file has checkboxes, mark tasks `[x]` as you complete them.
- Update `README.md` (written in plain, non-technical language) whenever usage changes.

**Security rules:**
- Always use `?` placeholders in SQL. Never build SQL with f-strings or `+`.
- Never use `|safe` on text the user typed, and keep autoescaping on.
- Never use an uploaded filename as given. Always generate a uuid name.
- Accept only the allowed image extensions, and keep the 5 MB limit.
- Destructive actions must be **POST only**.

**Protecting the owner's data:**
- **Never run `init-db` against existing data.** `schema.sql` starts with `DROP TABLE` and would erase every meal.
- Make any schema change through an **additive, idempotent migration**, such as a `flask --app app migrate` CLI command that checks `PRAGMA table_info(meals)` and runs `ALTER TABLE ... ADD COLUMN` only when the column is missing. Also update `schema.sql` so fresh installs get the same shape.
- Tell the owner to back up `instance/meals.db` before running a migration.

## 4. THE CURRENT GOAL: scaling by attendees + event shopping lists

### What the owner asked for
> "I want to be able to put in the number of attendees to an event so that when they select the meal for that many people it will adjust how much of each ingredient will be needed to purchase."

Then, on 2026-10-08, the owner answered the design questions:
1. **Rounding:** show the **rounded amount as the main value**, with the **exact amount in parentheses** next to it.
2. **Buffer:** **none.** Don't add an "extra %" option.
3. **Units:** **convert to the most convenient unit**, and show the **original unit in parentheses**.
4. **Events:** **yes.** Build events: create one event, add several meals to it, and **export one big combined shopping list**.

These answers override `PLAN.md`'s "out of scope" line for *ingredient quantity/unit parsing* and *combined shopping list*. Both are now wanted.

### Display rule (applies everywhere amounts are shown)
`<rounded amount> <convenient unit> (<exact amount> <original unit>)`

- `18.75 lb` → **`19 lb (18.75 lb)`**
- `88 tsp` → 1.83 cups → **`2 cups (88 tsp)`**
- `48 tsp` → exactly 1 cup → **`1 cup (48 tsp)`**. The parentheses stay because the unit changed.
- `20 lb` → **`20 lb`**. When the rounded value equals the exact value and the unit didn't change, leave out the parentheses.
- Lines with no leading amount (`pepper to taste`) are shown as typed and marked **"not scaled"**.

**Rounding:** this is a purchase list, so always round **up**. Round to a whole number of the convenient unit. If the amount is under 1 of that unit, round up to the nearest ¼ (e.g. `0.3 tsp` → `¼ tsp`, shown as `0.25 tsp` or `¼ tsp`). Count items with no unit (`3 eggs`) round up to whole numbers. In the parentheses, show the exact value with at most 2 decimals and trailing zeros trimmed.

**Conversion:** use a small built-in table. Never convert between US and metric, and never between weight and volume.
- US volume ladder: `tsp → tbsp → cup → qt → gal` (3 tsp = 1 tbsp, 16 tbsp = 1 cup, 4 cups = 1 qt, 4 qt = 1 gal). Also recognize `fl oz` (8 fl oz = 1 cup) and `pt` (2 cups) as input units, but don't choose them as targets.
- US weight: `oz → lb` (16 oz = 1 lb). A plain `oz` means **weight**. Only `fl oz` is volume.
- Metric: `g → kg` (1000), `ml → l` (1000).
- The "most convenient unit" is the **largest unit on the ladder where the amount is ≥ 1**.
- Recognize common spellings and plurals case-insensitively: tsp/teaspoon(s)/t, tbsp/tablespoon(s)/T, cup(s)/c, oz/ounce(s), lb/lbs/pound(s), g/gram(s), kg, ml, l/liter(s)/litre(s), qt/quart(s), pt/pint(s), gal/gallon(s), fl oz. Show units in a consistent short form with correct singular or plural.
- Any unit word not in the table (`cans`, `cloves`, `bunches`) is just part of the item name. Its amount still scales and rounds up, but it never converts.

### Ingredient line format
Keep `ingredients` as plain text, one per line. A line is `<amount> [unit] <item>`:
- the amount can be a whole number `3`, a decimal `1.5`, a fraction `1/2`, or a mixed number `1 1/2`
- the unit is optional and comes from the table above
- the item is everything else, kept exactly as typed

Put the parsing, scaling, conversion, rounding and formatting into **one small module of pure functions** (e.g. `scaling.py`), shared by the meal page and the event list. Cover it with a `test_scaling.py` that uses only the built-in `unittest`.

### Phase A — Servings + safe migration
- [ ] A.1 Add `servings INTEGER NOT NULL DEFAULT 1` to `meals`. Do it in `schema.sql` for fresh installs, and through an idempotent `flask --app app migrate` command for existing databases (`PRAGMA table_info` check, then `ALTER TABLE ... ADD COLUMN`). The same command creates the event tables from Phase D with `CREATE TABLE IF NOT EXISTS`.
- [ ] A.2 Meal form: add a required "Serves (number of people)" field (`min="1"`, `step="1"`) and validate it on the server. Change the ingredients placeholder to `One per line, amount first — e.g. 2 lb chicken thighs`.
- [ ] A.3 If a meal's servings is still 1, show a gentle note on its page reminding the owner to check the servings number.

### Phase B — Scaling module
- [ ] B.1 Build `scaling.py`: `parse_line`, `scale`, `to_convenient_unit`, `round_up_for_purchase`, `format_amount`. Return structured results (amount, unit, item, scaled flag) so the event list can sum them.
- [ ] B.2 Write `test_scaling.py`, covering fractions, mixed numbers, every unit ladder, the parentheses rules, unscaled lines and count items.

### Phase C — Guests box on the meal page
- [ ] C.1 On `meal_detail.html`, add a GET form with a `guests` input → `/meals/<id>?guests=150`. Show a heading like "Shopping list for 150 guests (recipe serves 8, ×18.75)" and the scaled list using the display rule. Keep the number in the box after submitting.
- [ ] C.2 Ignore an invalid `guests` value (0, negative, text) and show a friendly message. With no `guests`, show the normal list.

### Phase D — Events
- [ ] D.1 Add the tables:
  ```sql
  CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      event_date TEXT,                    -- optional, YYYY-MM-DD
      guests INTEGER NOT NULL CHECK (guests >= 1),
      notes TEXT NOT NULL DEFAULT '',
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
  );
  CREATE TABLE IF NOT EXISTS event_meals (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
      meal_id INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
      guests INTEGER CHECK (guests IS NULL OR guests >= 1),  -- NULL = use the event's guest count
      UNIQUE (event_id, meal_id)
  );
  ```
  Turn on `PRAGMA foreign_keys = ON` in `get_db()`.
- [ ] D.2 Routes, all server-rendered:
  | Method | URL | Purpose |
  |---|---|---|
  | GET | `/events` | list events (newest date first) |
  | GET, POST | `/events/new` | create event |
  | GET | `/events/<id>` | event page: details, its meals, a form to add a meal (dropdown of all meals + optional headcount) |
  | GET, POST | `/events/<id>/edit` | edit event |
  | POST | `/events/<id>/delete` | delete event (with a confirm prompt). Its meals are **not** deleted. |
  | POST | `/events/<id>/meals` | add a meal to the event |
  | POST | `/events/<id>/meals/<event_meal_id>/delete` | remove a meal from the event |
  | GET | `/events/<id>/shopping-list` | combined list |
  | GET | `/events/<id>/shopping-list.csv` | CSV export |
- [ ] D.3 The per-meal headcount is optional. It covers cases like "80 chicken, 40 fish" at the same wedding, and when left empty the event's guest count is used.
- [ ] D.4 Add "Events" to the nav in `base.html`. Deleting a meal that's used in events should warn that it will be removed from those events.

### Phase E — Combined shopping list + export
- [ ] E.1 For each meal in the event, scale its lines by `headcount / servings`.
- [ ] E.2 **Merge** lines that are the same item: match on the item name after lowercasing and trimming spaces, within the same kind of unit (US volume, US weight, metric weight, metric volume, or count/other). Sum them in the smallest unit of that kind **before** converting and rounding, so rounding happens once per item rather than per meal. Items that can't be merged (different kinds of unit) appear as separate rows.
- [ ] E.3 Each row shows the item, the amount (by the display rule) and a small "used in: Meal A, Meal B" note. Sort alphabetically by item. List "not scaled" lines in their own section, with the meal each one came from.
- [ ] E.4 Export:
  - **CSV download**, built with Python's `csv` module (no new packages), with the columns Item, Amount, Unit, Exact amount, Original unit, Used in. Send it with `Content-Disposition: attachment; filename="<event-name>-shopping-list.csv"` and a UTF-8 BOM so Excel opens it cleanly.
  - **Print / Save as PDF:** add a `@media print` stylesheet that hides the nav and buttons, plus a "Print" link.
- [ ] E.5 Tell the owner in the README that items only merge if they're spelled the same way in every meal ("chicken thighs" ≠ "chicken thigh").

### Phase F — README
- [ ] F.1 Explain: running `migrate` once (back up first), the amount-first ingredient format with examples, the guests box, events, and exporting the list.

### Check steps
- Run the migration on a **copy** of an existing database: existing meals survive, and `servings` = 1 for each. Running it twice is harmless.
- A fresh `init-db` creates every column and table.
- Meal "serves 4" with `2 cups rice`, `1 1/2 lb chicken`, `1/2 tsp salt`, `pepper to taste`, at 100 guests, shows `13 qt (50 cups)`, `38 lb (37.5 lb)`, `5 tbsp (12.5 tsp)` and `pepper to taste` (not scaled).
- Bad `guests` values show a friendly message, with no crash.
- Event: 120 guests, two meals that both use `rice` (one in cups, one in tbsp) produce **one** merged rice row. Removing a meal from the event updates the list. Deleting the event leaves its meals intact.
- The CSV opens in Excel with correct columns, and the print view hides the nav and buttons.
- `python -m unittest test_scaling` passes, and all earlier `PLAN.md` acceptance checks still pass.

## 5. Out of scope unless the owner asks
User accounts or login, hosting or deployment (all in `future_plans.md`), a REST API, JS frameworks, ORMs, extra pip packages, a meal calendar, pricing or cost estimates, inventory tracking, a waste/extra-% buffer (owner declined), and US↔metric or weight↔volume conversion.

## 6. How to talk to the owner
The owner isn't necessarily a developer. Explain in plain language, give copy-paste PowerShell commands, and say clearly when a step affects their saved meals.
