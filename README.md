# Event Shopping List

A simple app that runs on your own computer for saving your meals. For each meal you can store:
- a name
- a list of ingredients
- the recipe
- a photo (optional)

You can search your meals by name or by ingredient, which makes it easy to see what you need to buy. You can edit or delete a meal at any time.

Everything stays on your computer. There's no account, no login and nothing is sent over the internet.

---

## The Event Shopping List application (the normal way to use it)

Event Shopping List is a regular Windows application. It opens in its own window, with no web browser and no typing of commands.

- **Start it:** double-click **`Event Shopping List.exe`** in the `dist` folder. It takes a few seconds to open.
- **Put it on your desktop:** right-click `Event Shopping List.exe`, choose **Show more options → Send to → Desktop (create shortcut)**.
- **Close it:** close the window like any other program.

The first time you start it, Windows may show a blue "Windows protected your PC" box, because the app isn't from a big software company. Click **More info**, then **Run anyway**.

The app sets itself up. A brand-new copy starts with an empty meal list, and an older database is upgraded automatically (a backup copy is saved first).

The computer needs an internet connection for the app to look right, because the page styling is loaded from the internet. Your meals are never sent anywhere.

### Giving the application to another computer

Copy `Event Shopping List.exe` to the other Windows computer. Nothing else needs to be installed. It starts with an empty meal list there; to bring your meals along, also copy the data folder described in "Where your data is stored".

### Rebuilding the application after a change

The `.exe` is a snapshot. If the app's code is changed, build a new one. This needs Python (sections 1 and 2 below). In PowerShell, inside the app folder:

```powershell
.\.venv\Scripts\python -m pip install -r requirements-desktop.txt
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean --onefile --windowed --name "Event Shopping List" --add-data "templates;templates" --add-data "schema.sql;." desktop.py
```

Close Event Shopping List before building. The new `Event Shopping List.exe` replaces the old one in `dist`. **Your saved meals are not touched**, because they're kept in a separate folder.

---

> **Sections 1 to 3 below are the older way**, running the app from this folder and viewing it in a web browser. You only need them to rebuild the application or to try out a change before building.

---

## 1. Install Python (one time)

You need **Python 3.9 or newer**.

- **Windows:** download it from https://www.python.org/downloads/. During install, **tick "Add python.exe to PATH"**.
- **Mac:** download it from https://www.python.org/downloads/ (or run `brew install python` if you use Homebrew).

To check that it worked, open a terminal (on Windows use **PowerShell**, on Mac use **Terminal**) and run:

```
python --version
```

(On Mac, you may need to type `python3` instead of `python` in all the commands below.)

---

## 2. Set up the app (one time)

Open a terminal **inside the `meal-app` folder**, then run the commands for your system.

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m flask --app app init-db
```

**Mac / Linux:**
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m flask --app app init-db
```

You should see `Initialized the database.`

> **Warning:** only run `init-db` once. Running it again **erases all your saved meals**.

---

## Upgrading from an older version (one time)

If you already have saved meals from an earlier version, the app will show an **"upgrade needed"** page. Stop the app (**Ctrl + C**) and run this once in the app folder:

**Windows:**
```powershell
.\.venv\Scripts\python -m flask --app app migrate
```

**Mac / Linux:**
```bash
.venv/bin/python -m flask --app app migrate
```

This **keeps all your meals**. It saves a backup copy first, named `instance/meals-backup-<date>.db`. It's safe to run more than once.

The upgrade also moves each meal's old ingredient list into the new **ingredients table**, splitting every line into quantity, unit and name. It's worth opening each meal once to check the split looks right.

After upgrading, any meal that didn't have a "Serves" number yet is set to **"Serves 1"**. Open each meal, click **Edit** and enter how many people it really serves.

---

## 3. Start the app (every time you want to use it)

In a terminal inside the `meal-app` folder:

**Windows:**
```powershell
.\.venv\Scripts\python -m flask --app app run
```

**Mac / Linux:**
```bash
.venv/bin/python -m flask --app app run
```

Then open your web browser and go to **http://127.0.0.1:5000**

When you're finished, go back to the terminal and press **Ctrl + C** to stop the app.

---

## How to use it

- **Add a meal:** click **Add Meal**. Type the name, enter how many people the recipe **serves**, fill in the ingredients table (see below), add the recipe, and optionally choose a photo. Then click **Save**.
- **Find a meal:** use the search box on the home page. You can search by meal name or by an ingredient (for example `chicken`).
- **See what to buy:** click a meal to see its ingredient list and recipe.
- **Scale a meal for your guests:** open a meal, type the number of guests in the box and click **Scale**. Each amount is **rounded up** for buying and changed to the handiest unit, with the exact amount in brackets. For example, `13 qt (50 cups)`.
- **Change a meal:** open the meal and click **Edit**. You can also replace or remove its photo there.
- **Delete a meal:** open the meal and click **Delete**.

Photos can be PNG, JPG, GIF or WEBP, up to 5 MB.

### Entering ingredients

The meal form has an **ingredients table** with one row per ingredient and three boxes:

| Quantity | Unit | Ingredient |
|---|---|---|
| 1 1/2 | lb | chicken thighs |
| 2 | cups | rice |
| 3 | | eggs |
| 2 | can | crushed tomatoes |
| | | salt to taste |

- **Quantity** can be a whole number (`3`), a decimal (`1.5`), a fraction (`1/2`) or a mixed number (`1 1/2`). Leave it **empty** for things like "salt to taste". Those aren't scaled; they're listed separately so you remember to check them.
- **Unit:** click the box to pick from the suggestions. These units are converted to the handiest size when scaling: **tsp, tbsp, cup, fl oz, pt, qt, gal, oz, lb, g, kg, ml, l**. You can also type your own, like `can` or `clove`. Those still scale but aren't converted. `oz` means weight; use `fl oz` for liquid ounces.
- Click **+ Add ingredient** for more rows, and **✕** to remove one. Empty rows are ignored when you save.
- US and metric units are never mixed, and weight is never turned into volume.

### Events and shopping lists

1. Click **Events**, then **New Event**. Enter a name, the date (optional) and the number of guests.
2. Add each meal being served. Leave **"Making it for"** empty to use the event's guest count, or enter a number when only some guests get that dish (for example, 80 chicken and 40 fish).
3. Click **View shopping list** to see everything you need, combined into one list.
4. Click **Download for Excel (CSV)** to save the list as a spreadsheet, or **Print / Save as PDF**.

Ingredients only combine when they're **spelled the same way** in every meal. "chicken thighs" and "chicken thigh" will show up as two separate lines. Capital letters don't matter. Deleting an event never deletes your meals.

---

## Where your data is stored

**The Event Shopping List application** keeps everything in one folder:

```
%LOCALAPPDATA%\MealKeeper
```

To open it, paste that line into the address bar at the top of File Explorer and press Enter. Meals and events are in `meals.db`, and photos are in `uploads`. To **back up** your meals, close Event Shopping List and copy the whole `MealKeeper` folder somewhere safe.

**The older browser way** (sections 1 to 3) keeps its own, separate copy in this app folder: `instance/meals.db` and photos in `static/uploads/`. A meal added in one does **not** appear in the other.

---

## Sharing this app's folder with someone else

To share just the finished application, see "Giving the application to another computer" near the top. To send the whole folder instead, **delete these folders from the copy you send**:
- `.venv/`: it only works on the computer it was created on. The other person creates their own in step 2.
- `instance/`: this holds **your** meals. Leave it out so they start with an empty list.
- Any photos in `static/uploads/` (keep the `.gitkeep` file).

They can then follow this README from step 1.

---

## Troubleshooting

- **Event Shopping List opens but looks plain and unstyled:** the computer is offline. Your meals are fine; connect to the internet and reopen it.
- **Event Shopping List opens with no meals:** it is reading `%LOCALAPPDATA%\MealKeeper`. Check that your `meals.db` is in that folder.

- **`python` is not recognized:** Python isn't installed or wasn't added to PATH. Reinstall it and tick "Add python.exe to PATH". On Mac, try `python3`.
- **`no such table: meals`:** you skipped the `init-db` step in section 2.
- **Port 5000 is already in use:** start the app on another port with `... -m flask --app app run --port 5001`, then go to http://127.0.0.1:5001
- **The page won't load:** make sure the terminal running the app is still open.
