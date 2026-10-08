# future_plans.md — Making Meal Keeper Hostable

## Why
Right now the app is built to run only on your own computer. Anyone who can reach it can view, edit or delete every meal. Before putting it on the internet it needs:
- a login
- protection against cross-site request forgery (CSRF)
- a real secret key
- a production web server
- somewhere to store the database and photos that doesn't get wiped

## Instructions for the AI implementing this plan
- Do the phases **in order**. Test after each phase.
- Keep it simple. Add only these dependencies: `Flask-WTF` (for CSRF), `waitress` (production server on Windows) or `gunicorn` (on Linux).
- Never hard-code passwords or secret keys in the code. Read them from environment variables.
- Always use `?` placeholders in SQL queries. Never use `|safe` on text a user typed.
- Mark tasks `[x]` as you complete them.

---

## Decision to make first
- [ ] **Option A: one password for the whole app.** Each person hosts their own copy. This is the simplest and is recommended to start with. Do Phases 1–5.
- [ ] **Option B: one shared site with separate user accounts.** You and your friend share one site, but each person sees only their own meals. Do Phases 1–5 and then Phase 6.

---

## Phase 1 — Secret key and secure cookies
- [ ] 1.1 In `app.py`, if the app is not in debug mode and `SECRET_KEY` is missing or still `dev-change-me`, stop at startup with a clear error message.
- [ ] 1.2 Add config settings: `SESSION_COOKIE_HTTPONLY=True` and `SESSION_COOKIE_SAMESITE="Lax"`. Set `SESSION_COOKIE_SECURE=True` when the environment variable `HTTPS=1` is set.
- [ ] 1.3 Add the command for generating a key to the README: `python -c "import secrets; print(secrets.token_hex(32))"`.

**Check:** the app refuses to start in production without a proper `SECRET_KEY`.

## Phase 2 — CSRF protection
- [ ] 2.1 `pip install Flask-WTF` and add it to `requirements.txt`.
- [ ] 2.2 In `app.py`, add `from flask_wtf.csrf import CSRFProtect` and `CSRFProtect(app)`.
- [ ] 2.3 Add `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` to **every** POST form: `meal_form.html`, the delete form in `meal_detail.html`, and the new login form.
- [ ] 2.4 In the existing smoke test, set `app.config["WTF_CSRF_ENABLED"] = False` so it keeps working.

**Check:** submitting a form without the token returns a 400 error. Normal use in the browser still works.

## Phase 3 — Login (Option A: one password)
- [ ] 3.1 The password is stored as a hash in the environment variable `APP_PASSWORD_HASH`. Add a CLI command `flask --app app hash-password` that asks for a password and prints `werkzeug.security.generate_password_hash(pw)`.
- [ ] 3.2 Add routes:
  - `GET/POST /login`: checks the password with `check_password_hash`. On success, call `session.clear()`, set `session["logged_in"] = True`, then redirect to `/`.
  - `POST /logout`: calls `session.clear()` and redirects to `/login`.
- [ ] 3.3 Add a `@app.before_request` guard: unless the request is for `login` or `static`, redirect to `/login` when the user isn't logged in.
- [ ] 3.4 Add a `login.html` template with a password field and the CSRF token. Add a Logout button to the nav in `base.html`.
- [ ] 3.5 Basic brute-force protection: after each failed login, wait 1 second (`time.sleep(1)`) before responding. Keep this simple; no extra libraries.

**Check:** you can't reach any page without logging in. A wrong password is rejected, the right one works, and logging out works.

## Phase 4 — Protect photos
Photos in `static/uploads/` can currently be viewed by anyone who has the link, even without logging in.
- [ ] 4.1 Change `UPLOAD_FOLDER` to `os.path.join(app.instance_path, "uploads")`.
- [ ] 4.2 Add a route `GET /photos/<filename>` that is covered by the login guard and returns `send_from_directory(UPLOAD_FOLDER, filename)`.
- [ ] 4.3 In the templates, replace `url_for('static', filename='uploads/' ~ ...)` with `url_for('photo', filename=...)`.
- [ ] 4.4 Add a one-time step for moving existing photos from `static/uploads/` to `instance/uploads/`.

**Check:** opening a photo URL while logged out redirects to the login page.

## Phase 5 — Production server and hosting
- [ ] 5.1 Add `waitress` (Windows) or `gunicorn` (Linux) to `requirements.txt`.
  - Windows: `waitress-serve --listen=0.0.0.0:8000 app:app`
  - Linux: `gunicorn -w 2 -b 0.0.0.0:8000 app:app`
- [ ] 5.2 Never run with `--debug` in production.
- [ ] 5.3 Pick a host:
  - **PythonAnywhere (recommended):** has a free tier, supports Flask directly, and keeps files between restarts, so SQLite and the photos work as they are. Upload the folder, create a virtualenv, `pip install -r requirements.txt`, run `init-db` once, point the web app's WSGI file at `from app import app as application`, and set `SECRET_KEY`, `APP_PASSWORD_HASH` and `HTTPS=1` in the WSGI file or `.env`.
  - **Render / Railway / Fly.io:** you **must** attach a paid persistent disk and put `instance/` on it. Otherwise all meals and photos are wiped on every restart.
  - **VPS (e.g. DigitalOcean):** use gunicorn with nginx in front, and get an HTTPS certificate with Let's Encrypt (certbot).
- [ ] 5.4 Make sure the site uses **HTTPS** (most hosts do this automatically).
- [ ] 5.5 Backups: regularly download `instance/meals.db` and `instance/uploads/`.
- [ ] 5.6 Update `README.md` with a "Hosting" section describing the steps above.

**Check:** the site loads over `https://` and asks for a login. Meals and photos are still there after the host restarts the app.

## Phase 6 — Multiple user accounts (Option B only)
- [ ] 6.1 Add a `users` table: `id`, `username` (unique, NOCASE), `password_hash`, `created_at`.
- [ ] 6.2 Add `user_id INTEGER NOT NULL REFERENCES users(id)` to `meals`. Change the name uniqueness to `UNIQUE(user_id, name)`, so each person can have their own meal with the same name.
- [ ] 6.3 Write a migration script for existing data: create the first user and give all existing meals to them.
- [ ] 6.4 Replace the single password with username/password login, and store `session["user_id"]`.
- [ ] 6.5 Add a CLI command `flask --app app create-user` for adding accounts. Don't add public sign-up unless it's really needed.
- [ ] 6.6 **Every** meal query must filter by `user_id = ?`, including list, search, detail, edit, delete **and** the photo route. A request for a meal belonging to another user returns 404.
- [ ] 6.7 Test: user A can't see, edit, delete or open the photos of user B's meals, even by typing the URLs directly.

---

## Not needed for hosting (possible later extras)
- A combined shopping list from several meals
- Ingredient quantities and units
- Moving from SQLite to PostgreSQL. Only worth it if many people will use the site at once.
- A local-network-only option instead of hosting: `flask --app app run --host=0.0.0.0` lets devices on your trusted home Wi-Fi reach the app. It still needs Phase 3 if others share that network.
