# Meal Keeper

A simple app that runs on your own computer for saving your meals. For each meal you can store:
- a name
- a list of ingredients
- the recipe
- a photo (optional)

You can search your meals by name or by ingredient, which makes it easy to see what you need to buy. You can edit or delete a meal at any time.

Everything stays on your computer. There's no account, no login and nothing is sent over the internet.

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

After upgrading, every existing meal is set to **"Serves 1"**. Open each meal, click **Edit** and enter how many people it really serves.

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

- **Add a meal:** click **Add Meal**. Type the name, enter how many people the recipe **serves**, list the ingredients (**one per line, amount first**, for example `2 lb chicken thighs`), add the recipe, and optionally choose a photo. Then click **Save**.
- **Find a meal:** use the search box on the home page. You can search by meal name or by an ingredient (for example `chicken`).
- **See what to buy:** click a meal to see its ingredient list and recipe.
- **Scale a meal for your guests:** open a meal, type the number of guests in the box and click **Scale**. Each amount is **rounded up** for buying and changed to the handiest unit, with the exact amount in brackets. For example, `13 qt (50 cups)`.
- **Change a meal:** open the meal and click **Edit**. You can also replace or remove its photo there.
- **Delete a meal:** open the meal and click **Delete**.

Photos can be PNG, JPG, GIF or WEBP, up to 5 MB.

### Typing ingredients so they scale

Put the **amount first**, then the unit (optional), then the ingredient, one per line:

```
2 cups rice
1 1/2 lb chicken thighs
1/2 tsp salt
3 eggs
2 cans crushed tomatoes
pepper to taste
```

- Amounts can be whole numbers (`3`), decimals (`1.5`), fractions (`1/2`) or mixed numbers (`1 1/2`).
- Units the app understands and converts: **tsp, tbsp, cup, fl oz, pt, qt, gal, oz, lb, g, kg, ml, l** (full names like "tablespoons" or "pounds" work too). `oz` means weight; write `fl oz` for liquid ounces.
- Other words, like `cans` or `cloves`, still scale but aren't converted.
- A line with no amount at the start, such as "pepper to taste", isn't scaled. It's listed separately so you remember to check it.
- US and metric units are never mixed, and weight is never turned into volume.

### Events and shopping lists

1. Click **Events**, then **New Event**. Enter a name, the date (optional) and the number of guests.
2. Add each meal being served. Leave **"Making it for"** empty to use the event's guest count, or enter a number when only some guests get that dish (for example, 80 chicken and 40 fish).
3. Click **View shopping list** to see everything you need, combined into one list.
4. Click **Download for Excel (CSV)** to save the list as a spreadsheet, or **Print / Save as PDF**.

Ingredients only combine when they're **spelled the same way** in every meal. "chicken thighs" and "chicken thigh" will show up as two separate lines. Capital letters don't matter. Deleting an event never deletes your meals.

---

## Where your data is stored

- Meals and events are saved in `instance/meals.db`.
- Photos are saved in `static/uploads/`.

To **back up** your meals, copy those two folders somewhere safe.

---

## Sharing this app with someone else

Before you send the folder, **delete these folders from the copy you send**:
- `.venv/`: it only works on the computer it was created on. The other person creates their own in step 2.
- `instance/`: this holds **your** meals. Leave it out so they start with an empty list.
- Any photos in `static/uploads/` (keep the `.gitkeep` file).

They can then follow this README from step 1.

---

## Troubleshooting

- **`python` is not recognized:** Python isn't installed or wasn't added to PATH. Reinstall it and tick "Add python.exe to PATH". On Mac, try `python3`.
- **`no such table: meals`:** you skipped the `init-db` step in section 2.
- **Port 5000 is already in use:** start the app on another port with `... -m flask --app app run --port 5001`, then go to http://127.0.0.1:5001
- **The page won't load:** make sure the terminal running the app is still open.
