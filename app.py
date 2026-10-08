import os
import sqlite3
import uuid

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
    }


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
    if not form["name"] or not form["ingredients"]:
        flash("Name and ingredients are required.", "error")
        return render_template("meal_form.html", meal=None, form=form, title="Add Meal")

    try:
        photo = save_photo(request.files.get("photo"))
    except ValueError as e:
        flash(str(e), "error")
        return render_template("meal_form.html", meal=None, form=form, title="Add Meal")

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO meals (name, ingredients, recipe, photo_filename) VALUES (?, ?, ?, ?)",
            (form["name"], form["ingredients"], form["recipe"], photo),
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
    if not form["name"] or not form["ingredients"]:
        flash("Name and ingredients are required.", "error")
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
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (form["name"], form["ingredients"], form["recipe"], photo, meal_id),
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
