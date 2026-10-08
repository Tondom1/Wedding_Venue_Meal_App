# PLAN.md — Meal & Ingredients Web App

## Instructions for the AI implementing this plan
- Follow the phases **in order**. Do not skip ahead.
- After each phase, run the "Check" steps before continuing.
- Keep it simple: **do not** add features, libraries, authentication, JavaScript frameworks, or ORMs not listed here.
- Only dependency allowed: `Flask`. Use Python's built-in `sqlite3` module for the database.
- Target OS: **Windows** (use PowerShell commands).
- Mark tasks `[x]` in this file as you complete them.

## Goal
A local, single-user web app where I can:
1. Add a meal: name, list of ingredients, recipe, optional photo.
2. Browse and search meals by name or ingredient.
3. View a meal's ingredient list (to know what to buy) and recipe.
4. Edit or delete any meal at any time.

## Tech stack (fixed — do not change)
- Python 3.10+
- Flask (server-rendered Jinja2 templates)
- SQLite via built-in `sqlite3`
- Pico.css from CDN for styling: `<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">`
- No login, runs locally only

## Final folder structure
```
meal-app/
├── app.py
├── schema.sql
├── requirements.txt
├── .gitignore
├── PLAN.md
├── instance/            (auto-created; holds meals.db)
├── static/
│   └── uploads/         (meal photos)
└── templates/
    ├── base.html
    ├── index.html
    ├── meal_detail.html
    ├── meal_form.html
    └── 404.html
```

## Database schema (`schema.sql`) — use exactly this
```sql
DROP TABLE IF EXISTS meals;

CREATE TABLE meals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    ingredients TEXT NOT NULL,
    recipe TEXT NOT NULL DEFAULT '',
    photo_filename TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```
- `ingredients` is stored as plain text, **one ingredient per line**.
- To display, split on newlines and drop blank lines.

## Routes (all in `app.py`)
| Method | URL | Purpose | Template |
|---|---|---|---|
| GET | `/` | List all meals sorted by name; supports `?q=` search | index.html |
| GET, POST | `/meals/new` | Show form / create meal | meal_form.html |
| GET | `/meals/<int:meal_id>` | Show meal detail | meal_detail.html |
| GET, POST | `/meals/<int:meal_id>/edit` | Show prefilled form / update meal | meal_form.html |
| POST | `/meals/<int:meal_id>/delete` | Delete meal and its photo, redirect to `/` | — |

---

## Phase 1 — Project setup
- [ ] 1.1 In the `meal-app` folder, run:
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install flask
  pip freeze > requirements.txt
  ```
- [ ] 1.2 Create `.gitignore` containing: `.venv/`, `__pycache__/`, `instance/`, `static/uploads/*` and `!static/uploads/.gitkeep`.
- [ ] 1.3 Create empty file `static/uploads/.gitkeep`.
- [ ] 1.4 Create `schema.sql` exactly as shown above.
- [ ] 1.5 In `app.py`:
  - Create the Flask app with `instance_relative_config=True`.
  - Config: `SECRET_KEY` read from env var `SECRET_KEY`, falling back to `"dev-change-me"`; `DATABASE = os.path.join(app.instance_path, "meals.db")`; `UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")`; `MAX_CONTENT_LENGTH = 5 * 1024 * 1024`.
  - `os.makedirs(app.instance_path, exist_ok=True)` and the same for `UPLOAD_FOLDER`.
  - `get_db()`: store the connection on `flask.g`, set `row_factory = sqlite3.Row`.
  - `close_db()`: registered with `@app.teardown_appcontext`.
  - `init_db()`: executes `schema.sql`.
  - CLI command `init-db` via `@app.cli.command("init-db")` that calls `init_db()` and prints "Initialized the database."

**Check:** `flask --app app init-db` prints the message and creates `instance/meals.db`.

## Phase 2 — Templates and layout
- [ ] 2.1 `base.html`: HTML5 page with Pico.css link, `<main class="container">`, a nav with links "Meals" (`/`) and "Add Meal" (`/meals/new`), a block to show flashed messages (`get_flashed_messages(with_categories=true)`), and `{% block content %}{% endblock %}`.
- [ ] 2.2 `404.html`: extends base, says "Meal not found" with a link home. Register `@app.errorhandler(404)` to render it with status 404.

## Phase 3 — Create and list meals
- [ ] 3.1 `meal_form.html` (used for both new and edit):
  - `<form method="post" enctype="multipart/form-data">`
  - Fields: `name` (text, required), `ingredients` (textarea, required, placeholder "One ingredient per line"), `recipe` (textarea), `photo` (file input, `accept="image/*"`).
  - When editing and a photo exists: show a thumbnail and a checkbox `remove_photo`.
  - Prefill values from a `meal` variable (or from submitted form data after a validation error).
  - Submit button text: "Save".
- [ ] 3.2 `GET/POST /meals/new`:
  - On POST: strip `name`, `ingredients`, `recipe`. If `name` or `ingredients` is empty, flash an error and re-render the form with entered values.
  - Handle the photo (see Phase 5; for now the photo can be ignored until Phase 5).
  - `INSERT` using `?` placeholders. Catch `sqlite3.IntegrityError`, flash "A meal with that name already exists." and re-render.
  - On success: flash "Meal saved." and redirect to the detail page.
- [ ] 3.3 `GET /`:
  - Query `SELECT id, name, photo_filename FROM meals ORDER BY name`.
  - `index.html`: search form at top (GET, input name `q`), then a list/grid of meals showing a thumbnail (if any) and name linking to the detail page. If no meals, show "No meals yet — add one!"

**Check:** Run `flask --app app run --debug`, open http://127.0.0.1:5000, add a meal, and confirm it appears on the home page.

## Phase 4 — Detail, edit, delete
- [ ] 4.1 `GET /meals/<id>`: fetch the meal; `abort(404)` if missing. `meal_detail.html` shows:
  - Photo (if any) at the top, max width 100%.
  - Name as `<h1>`.
  - "Ingredients" heading + `<ul>` of ingredient lines (split on newlines, skip blanks).
  - "Recipe" heading + recipe text with line breaks preserved (use CSS `white-space: pre-wrap`; **do not** use `|safe`).
  - "Edit" link and a Delete form (`method="post"` to the delete URL) whose button uses `onclick="return confirm('Delete this meal?')"`.
- [ ] 4.2 `GET/POST /meals/<id>/edit`: same validation as create; `UPDATE meals SET name=?, ingredients=?, recipe=?, photo_filename=?, updated_at=CURRENT_TIMESTAMP WHERE id=?`. Handle the duplicate-name `IntegrityError`. Flash "Meal updated." and redirect to the detail page.
- [ ] 4.3 `POST /meals/<id>/delete`: fetch the meal (404 if missing), delete its photo file if present, delete the row, flash "Meal deleted.", redirect to `/`.

**Check:** Edit a meal, restart the server, and confirm the changes persisted. Delete a meal and confirm it's gone.

## Phase 5 — Photos
- [ ] 5.1 `ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}`.
- [ ] 5.2 Helper `save_photo(file_storage)`:
  - Return `None` if no file or the filename is empty.
  - Get the extension from `werkzeug.utils.secure_filename(file.filename)`, lowercase; if it's not allowed, raise `ValueError("Unsupported image type")`.
  - New filename = `uuid.uuid4().hex + "." + ext`; save to `UPLOAD_FOLDER`; return the filename.
- [ ] 5.3 Helper `delete_photo(filename)`: if `filename` is set and the file exists in `UPLOAD_FOLDER`, remove it.
- [ ] 5.4 Create route: call `save_photo`; on `ValueError`, flash the message and re-render the form.
- [ ] 5.5 Edit route: if a new photo is uploaded → save the new one, then delete the old one. Else if `remove_photo` is checked → delete the old one and set `photo_filename` to `None`. Otherwise keep the existing one.
- [ ] 5.6 Register `@app.errorhandler(413)`: flash "Photo too large (max 5 MB)." and redirect to `request.url`.
- [ ] 5.7 Display photos with `url_for('static', filename='uploads/' ~ meal.photo_filename)`.

**Check:** Upload a jpg (works), a .txt (rejected), a >5 MB image (rejected), replace a photo (old file removed from `static/uploads`), and remove a photo.

## Phase 6 — Search
- [ ] 6.1 In `GET /`: read `q = request.args.get("q", "").strip()`. If `q` is set:
  `SELECT id, name, photo_filename FROM meals WHERE name LIKE ? OR ingredients LIKE ? ORDER BY name` with params `(f"%{q}%", f"%{q}%")`.
- [ ] 6.2 Keep the search text in the input box; show "No meals match "{q}"" when there are no results, plus a "Clear search" link.

**Check:** Search by part of a meal name and by an ingredient (e.g. "garlic"); both return the right meals.

## Security rules (must follow)
- **Always** use `?` placeholders in SQL. Never build SQL with f-strings or `+`.
- Never use `|safe` on user-entered text (Jinja autoescaping must stay on).
- Never use the uploaded filename directly; always generate a uuid filename.
- Only accept the allowed image extensions; enforce the 5 MB limit.
- Deleting must be POST only (never GET).

## Final acceptance checklist
- [ ] `flask --app app init-db` then `flask --app app run --debug` starts the app with no errors.
- [ ] Can add a meal with and without a photo.
- [ ] Home page lists meals alphabetically with thumbnails.
- [ ] Search works by meal name and by ingredient.
- [ ] Detail page shows ingredients as a bullet list and the recipe with line breaks.
- [ ] Editing changes persist after a server restart.
- [ ] Duplicate meal names show a friendly error (no crash).
- [ ] Deleting a meal also removes its photo file.
- [ ] Invalid or oversized uploads show a friendly error.
- [ ] Visiting `/meals/9999` shows the 404 page.

## Out of scope (do NOT build)
User accounts/login, deployment, REST API, JavaScript frameworks, ORMs, ingredient quantity/unit parsing, meal calendar, combined shopping list.