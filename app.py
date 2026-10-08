import os
import shutil
import sqlite3
import uuid
from datetime import datetime

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename

app = Flask(__name__, instance_relative_config=True)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
    DATABASE=os.path.join(app.instance_path, "meals.db"),
    UPLOAD_FOLDER=os.path.join(app.root_path, "static", "uploads"),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
)
os.makedirs(app.instance_path, exist_ok=True)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


# ---------- Database ----------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))


@app.cli.command("init-db")
def init_db_command():
    init_db()
    print("Initialized the database.")


# ---------- Migration (upgrade an existing database without losing data) ----------

EVENT_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    event_date TEXT,
    guests INTEGER NOT NULL CHECK (guests >= 1),
    notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS event_meals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    meal_id INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
    guests INTEGER CHECK (guests IS NULL OR guests >= 1),
    UNIQUE (event_id, meal_id)
);
"""


def table_exists(db, name):
    row = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def meal_columns(db):
    return {row["name"] for row in db.execute("PRAGMA table_info(meals)")}


def needs_migration(db):
    if not table_exists(db, "meals"):
        return False
    return (
        "servings" not in meal_columns(db)
        or not table_exists(db, "events")
        or not table_exists(db, "event_meals")
    )


def backup_database():
    src = app.config["DATABASE"]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(app.instance_path, f"meals-backup-{stamp}.db")
    shutil.copy2(src, dest)
    return dest


@app.cli.command("migrate")
def migrate_command():
    """Safely upgrade an existing database. Never deletes data; safe to run more than once."""
    if not os.path.exists(app.config["DATABASE"]):
        print("No database found. For a brand-new install run: flask --app app init-db")
        return
    db = get_db()
    if not table_exists(db, "meals"):
        print("The database has no meals table. For a brand-new install run: flask --app app init-db")
        return
    if not needs_migration(db):
        print("Database is already up to date. Nothing to do.")
        return

    backup = backup_database()
    print(f"Backup saved to {backup}")

    if "servings" not in meal_columns(db):
        db.execute("ALTER TABLE meals ADD COLUMN servings INTEGER NOT NULL DEFAULT 1")
        print("Added 'servings' to meals (existing meals set to 1 - please edit each meal to set the real number).")
    db.executescript(EVENT_TABLES_SQL)
    db.commit()
    print("Database upgraded.")


@app.before_request
def check_database_upgraded():
    if request.endpoint == "static" or app.config.get("DB_CHECKED"):
        return None
    if os.path.exists(app.config["DATABASE"]) and needs_migration(get_db()):
        return render_template("needs_migration.html"), 503
    app.config["DB_CHECKED"] = True
    return None


def get_meal_or_404(meal_id):
    meal = get_db().execute("SELECT * FROM meals WHERE id = ?", (meal_id,)).fetchone()
    if meal is None:
        abort(404)
    return meal


# ---------- Photos ----------

def save_photo(file_storage):
    if file_storage is None or not file_storage.filename:
        return None
    safe_name = secure_filename(file_storage.filename)
    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported image type")
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    return filename


def delete_photo(filename):
    if not filename:
        return
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.isfile(path):
        os.remove(path)


# ---------- Helpers ----------

def read_form():
    return {
        "name": request.form.get("name", "").strip(),
        "ingredients": request.form.get("ingredients", "").strip(),
        "recipe": request.form.get("recipe", "").strip(),
        "servings": request.form.get("servings", "").strip(),
    }


def parse_servings(text):
    """Return a whole number >= 1, or None if the text isn't one."""
    try:
        value = int(text)
    except (TypeError, ValueError):
        return None
    return value if value >= 1 else None


def validate_form(form):
    """Return an error message, or None if the form is fine."""
    if not form["name"] or not form["ingredients"]:
        return "Name and ingredients are required."
    if parse_servings(form["servings"]) is None:
        return "Serves must be a whole number of 1 or more."
    return None


@app.template_filter("lines")
def lines_filter(text):
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


# ---------- Routes ----------

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    db = get_db()
    if q:
        like = f"%{q}%"
        meals = db.execute(
            "SELECT id, name, photo_filename FROM meals "
            "WHERE name LIKE ? OR ingredients LIKE ? ORDER BY name",
            (like, like),
        ).fetchall()
    else:
        meals = db.execute(
            "SELECT id, name, photo_filename FROM meals ORDER BY name"
        ).fetchall()
    return render_template("index.html", meals=meals, q=q)


@app.route("/meals/new", methods=["GET", "POST"])
def new_meal():
    if request.method == "GET":
        return render_template("meal_form.html", meal=None, form={}, title="Add Meal")

    form = read_form()
    error = validate_form(form)
    if error:
        flash(error, "error")
        return render_template("meal_form.html", meal=None, form=form, title="Add Meal")

    try:
        photo = save_photo(request.files.get("photo"))
    except ValueError as e:
        flash(str(e), "error")
        return render_template("meal_form.html", meal=None, form=form, title="Add Meal")

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO meals (name, ingredients, recipe, photo_filename, servings) "
            "VALUES (?, ?, ?, ?, ?)",
            (form["name"], form["ingredients"], form["recipe"], photo,
             parse_servings(form["servings"])),
        )
        db.commit()
    except sqlite3.IntegrityError:
        delete_photo(photo)
        flash("A meal with that name already exists.", "error")
        return render_template("meal_form.html", meal=None, form=form, title="Add Meal")

    flash("Meal saved.", "success")
    return redirect(url_for("meal_detail", meal_id=cur.lastrowid))


@app.route("/meals/<int:meal_id>")
def meal_detail(meal_id):
    return render_template("meal_detail.html", meal=get_meal_or_404(meal_id))


@app.route("/meals/<int:meal_id>/edit", methods=["GET", "POST"])
def edit_meal(meal_id):
    meal = get_meal_or_404(meal_id)
    if request.method == "GET":
        return render_template("meal_form.html", meal=meal, form=dict(meal), title="Edit Meal")

    form = read_form()
    error = validate_form(form)
    if error:
        flash(error, "error")
        return render_template("meal_form.html", meal=meal, form=form, title="Edit Meal")

    try:
        new_photo = save_photo(request.files.get("photo"))
    except ValueError as e:
        flash(str(e), "error")
        return render_template("meal_form.html", meal=meal, form=form, title="Edit Meal")

    old_photo = meal["photo_filename"]
    if new_photo:
        photo = new_photo
    elif request.form.get("remove_photo"):
        photo = None
    else:
        photo = old_photo

    db = get_db()
    try:
        db.execute(
            "UPDATE meals SET name = ?, ingredients = ?, recipe = ?, photo_filename = ?, "
            "servings = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (form["name"], form["ingredients"], form["recipe"], photo,
             parse_servings(form["servings"]), meal_id),
        )
        db.commit()
    except sqlite3.IntegrityError:
        delete_photo(new_photo)
        flash("A meal with that name already exists.", "error")
        return render_template("meal_form.html", meal=meal, form=form, title="Edit Meal")

    if old_photo and photo != old_photo:
        delete_photo(old_photo)

    flash("Meal updated.", "success")
    return redirect(url_for("meal_detail", meal_id=meal_id))


@app.route("/meals/<int:meal_id>/delete", methods=["POST"])
def delete_meal(meal_id):
    meal = get_meal_or_404(meal_id)
    db = get_db()
    db.execute("DELETE FROM meals WHERE id = ?", (meal_id,))
    db.commit()
    delete_photo(meal["photo_filename"])
    flash("Meal deleted.", "success")
    return redirect(url_for("index"))


# ---------- Errors ----------

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_large(e):
    flash("Photo too large (max 5 MB).", "error")
    return redirect(request.url)
