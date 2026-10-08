-- Creates a fresh, EMPTY database. Running this erases all saved meals and events.
-- To upgrade an existing database, use `flask --app app migrate` instead.
DROP TABLE IF EXISTS event_meals;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS meals;

CREATE TABLE meals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    ingredients TEXT NOT NULL,
    recipe TEXT NOT NULL DEFAULT '',
    photo_filename TEXT,
    servings INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    event_date TEXT,
    guests INTEGER NOT NULL CHECK (guests >= 1),
    notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE event_meals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    meal_id INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
    guests INTEGER CHECK (guests IS NULL OR guests >= 1),
    UNIQUE (event_id, meal_id)
);
