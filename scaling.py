"""Ingredient scaling: read an ingredient line, scale it for a headcount,
convert it to the most convenient unit and round it up for purchasing.

Plain functions only (no Flask), so they are easy to test: see test_scaling.py.

An ingredient line looks like  "<amount> [unit] <item>", for example:
    2 cups rice          1 1/2 lb chicken thighs        3 eggs
    1/2 tsp salt         0.75 kg flour                  pepper to taste   (no amount: not scaled)
"""
import math
import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import List, Optional

# ---------- Units ----------

# canonical unit -> (kind, size measured in the smallest unit of that kind)
UNITS = {
    "tsp": ("us_volume", 1),
    "tbsp": ("us_volume", 3),
    "fl oz": ("us_volume", 6),
    "cup": ("us_volume", 48),
    "pt": ("us_volume", 96),
    "qt": ("us_volume", 192),
    "gal": ("us_volume", 768),
    "oz": ("us_weight", 1),
    "lb": ("us_weight", 16),
    "g": ("metric_weight", 1),
    "kg": ("metric_weight", 1000),
    "ml": ("metric_volume", 1),
    "l": ("metric_volume", 1000),
}

# Units we convert *to*, smallest first. fl oz and pt are understood but never chosen.
LADDERS = {
    "us_volume": ["tsp", "tbsp", "cup", "qt", "gal"],
    "us_weight": ["oz", "lb"],
    "metric_weight": ["g", "kg"],
    "metric_volume": ["ml", "l"],
}

COUNT = "count"  # kind for lines with no recognised unit (3 eggs, 2 cans tomatoes)

_ALIASES = {
    "tsp": ["tsp", "tsps", "teaspoon", "teaspoons"],
    "tbsp": ["tbsp", "tbsps", "tbs", "tablespoon", "tablespoons"],
    "cup": ["cup", "cups", "c"],
    "fl oz": ["floz"],
    "pt": ["pt", "pts", "pint", "pints"],
    "qt": ["qt", "qts", "quart", "quarts"],
    "gal": ["gal", "gals", "gallon", "gallons"],
    "oz": ["oz", "ozs", "ounce", "ounces"],
    "lb": ["lb", "lbs", "pound", "pounds"],
    "g": ["g", "gram", "grams", "gr"],
    "kg": ["kg", "kgs", "kilogram", "kilograms"],
    "ml": ["ml", "milliliter", "milliliters", "millilitre", "millilitres"],
    "l": ["l", "liter", "liters", "litre", "litres"],
}
UNIT_ALIASES = {alias: unit for unit, names in _ALIASES.items() for alias in names}

_UNICODE_FRACTIONS = {"½": "1/2", "¼": "1/4", "¾": "3/4", "⅓": "1/3", "⅔": "2/3", "⅛": "1/8"}

_AMOUNT_RE = re.compile(
    r"^(?:(?P<whole>\d+)\s+(?P<num>\d+)\s*/\s*(?P<den>\d+)"  # 1 1/2
    r"|(?P<fnum>\d+)\s*/\s*(?P<fden>\d+)"                     # 1/2
    r"|(?P<dec>\d+(?:\.\d+)?|\.\d+))"                         # 3, 1.5, .5
    r"(?=\s|$|[^\W\d_])"                                      # followed by space, end or a letter
)
_FLUID_OUNCE_RE = re.compile(r"^(?:fl\.?\s*oz\.?|fluid\s+ounces?)(?=\s|$)", re.IGNORECASE)


@dataclass
class Line:
    """One ingredient line. amount is None for lines that can't be scaled."""
    text: str                      # the line exactly as typed
    amount: Optional[Fraction]     # e.g. Fraction(3, 2)
    unit: Optional[str]            # canonical unit, e.g. "cup"; None for counts
    item: str                      # the rest, e.g. "chicken thighs"

    @property
    def scaled(self):
        return self.amount is not None

    @property
    def kind(self):
        return UNITS[self.unit][0] if self.unit else COUNT


def parse_amount(text):
    """Return (Fraction, rest_of_text) or (None, text) if the text doesn't start with an amount."""
    m = _AMOUNT_RE.match(text)
    if not m:
        return None, text
    if m.group("whole"):
        den = int(m.group("den"))
        if den == 0:
            return None, text
        value = int(m.group("whole")) + Fraction(int(m.group("num")), den)
    elif m.group("fnum"):
        den = int(m.group("fden"))
        if den == 0:
            return None, text
        value = Fraction(int(m.group("fnum")), den)
    else:
        value = Fraction(m.group("dec"))
    return value, text[m.end():].strip()


def parse_unit(text):
    """Return (canonical_unit, rest_of_text) or (None, text) if no known unit comes first."""
    m = _FLUID_OUNCE_RE.match(text)
    if m:
        return "fl oz", text[m.end():].strip()
    first, _, rest = text.partition(" ")
    word = first.rstrip(".")
    if word == "T":
        return "tbsp", rest.strip()
    if word == "t":
        return "tsp", rest.strip()
    unit = UNIT_ALIASES.get(word.lower())
    if unit:
        return unit, rest.strip()
    return None, text


def parse_line(text):
    """Turn one typed ingredient line into a Line."""
    text = text.strip()
    work = text
    for symbol, frac in _UNICODE_FRACTIONS.items():
        work = re.sub(r"(\d)" + symbol, r"\1 " + frac, work)  # 1½ -> 1 1/2
        work = work.replace(symbol, frac)
    amount, rest = parse_amount(work)
    if amount is None:
        return Line(text=text, amount=None, unit=None, item=text)
    unit, item = parse_unit(rest)
    return Line(text=text, amount=amount, unit=unit, item=item)


def parse_ingredients(text):
    """Parse a whole ingredients box: one Line per non-blank line."""
    return [parse_line(line) for line in (text or "").splitlines() if line.strip()]


# ---------- Scaling, converting, rounding ----------

def scale(line, factor):
    """Return a copy of the line with its amount multiplied by factor (unscaled lines unchanged)."""
    if not line.scaled:
        return line
    return Line(text=line.text, amount=line.amount * Fraction(factor), unit=line.unit, item=line.item)


def to_base(amount, unit):
    """Express an amount in the smallest unit of its kind. Returns (kind, amount)."""
    if unit is None:
        return COUNT, amount
    kind, size = UNITS[unit]
    return kind, amount * size


# When rounding up in a big unit would buy more than this much extra, use a smaller unit instead
# (e.g. 3.1 gal would round to 4 gal = +28%, so show 13 qt instead).
MAX_ROUNDING_EXTRA = Fraction(1, 4)


def to_convenient_unit(base_amount, kind):
    """Pick the largest unit on the ladder where the amount is at least 1 and rounding up
    adds no more than 25%. Falls back to the smallest unit.
    Returns (amount_in_that_unit, unit). Counts stay as they are (unit None)."""
    if kind == COUNT:
        return base_amount, None
    ladder = LADDERS[kind]
    for unit in reversed(ladder):
        amount = base_amount / UNITS[unit][1]
        if amount >= 1 and round_up_for_purchase(amount, unit) <= amount * (1 + MAX_ROUNDING_EXTRA):
            return amount, unit
    return base_amount / UNITS[ladder[0]][1], ladder[0]


def round_up_for_purchase(amount, unit):
    """Round up: to a whole number, or to the nearest quarter when under 1 of a measured unit.
    Counted items (no unit) always round up to a whole number."""
    if amount <= 0:
        return Fraction(0)
    if unit is None or amount >= 1:
        return Fraction(math.ceil(amount))
    return Fraction(math.ceil(amount * 4), 4)


# ---------- Formatting ----------

_QUARTERS = {Fraction(1, 4): "¼", Fraction(1, 2): "½", Fraction(3, 4): "¾"}


def format_rounded(value):
    """Rounded purchase amounts: whole numbers, or ¼ ½ ¾ under 1."""
    if value in _QUARTERS:
        return _QUARTERS[value]
    return str(int(value)) if value == int(value) else format_exact(value)


def format_exact(value):
    """Exact amounts: at most 2 decimals, trailing zeros trimmed."""
    text = "{:.2f}".format(float(value)).rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def unit_label(unit, value):
    """Short unit name, with 'cups' plural. Other short forms don't change."""
    if unit is None:
        return ""
    if unit == "cup" and value > 1:
        return "cups"
    return unit


def _with_unit(number_text, unit, value):
    label = unit_label(unit, value)
    return "{} {}".format(number_text, label) if label else number_text


@dataclass
class Amount:
    """A ready-to-show purchase amount, built by describe()."""
    rounded: Fraction
    unit: Optional[str]            # convenient unit (None for counts)
    exact: Fraction                # exact amount, in exact_unit
    exact_unit: Optional[str]      # the original unit (or the convenient unit if originals were mixed)
    show_exact: bool               # False when the parentheses would just repeat the main amount

    @property
    def main_text(self):
        return _with_unit(format_rounded(self.rounded), self.unit, self.rounded)

    @property
    def exact_text(self):
        return _with_unit(format_exact(self.exact), self.exact_unit, self.exact)

    @property
    def text(self):
        if self.show_exact:
            return "{} ({})".format(self.main_text, self.exact_text)
        return self.main_text


def describe(base_amount, kind, original_units):
    """Build the display amount for a quantity held in base units.
    original_units: the set of units the owner typed (one unit for a single line)."""
    amount, unit = to_convenient_unit(base_amount, kind)
    rounded = round_up_for_purchase(amount, unit)
    originals = {u for u in original_units}
    if len(originals) == 1:
        exact_unit = next(iter(originals))
        exact = base_amount if kind == COUNT else base_amount / UNITS[exact_unit][1]
    else:
        exact_unit, exact = unit, amount
    show_exact = not (rounded == amount and exact_unit == unit)
    return Amount(rounded=rounded, unit=unit, exact=exact, exact_unit=exact_unit, show_exact=show_exact)


def format_amount(line):
    """Display text for one (already scaled) line's amount, e.g. '13 qt (50 cups)'.
    Returns None for lines that can't be scaled."""
    if not line.scaled:
        return None
    kind, base = to_base(line.amount, line.unit)
    return describe(base, kind, {line.unit}).text


# ---------- Whole lists ----------

@dataclass
class ListRow:
    """One row of a shopping list."""
    item: str
    amount: Optional[Amount]       # None for 'not scaled' rows
    text: str = ""                 # original line (for not scaled rows)
    used_in: List[str] = field(default_factory=list)


def scaled_rows(ingredients_text, factor):
    """Rows for one meal scaled by factor, in the order typed (no merging)."""
    rows = []
    for line in parse_ingredients(ingredients_text):
        if not line.scaled:
            rows.append(ListRow(item=line.item, amount=None, text=line.text))
            continue
        line = scale(line, factor)
        kind, base = to_base(line.amount, line.unit)
        rows.append(ListRow(item=line.item, amount=describe(base, kind, {line.unit}), text=line.text))
    return rows


def _merge_key(item):
    return " ".join(item.lower().split())


def combined_list(meals):
    """Merge several meals into one shopping list.

    meals: iterable of (meal_name, ingredients_text, factor).
    Same item (ignoring case and extra spaces) with the same kind of unit is added
    together before converting and rounding, so rounding happens once per item.
    Returns (rows sorted by item, not_scaled_rows in meal order)."""
    totals = {}       # (key, kind) -> dict
    not_scaled = []
    for meal_name, ingredients_text, factor in meals:
        for line in parse_ingredients(ingredients_text):
            if not line.scaled:
                not_scaled.append(ListRow(item=line.item, amount=None, text=line.text, used_in=[meal_name]))
                continue
            line = scale(line, factor)
            kind, base = to_base(line.amount, line.unit)
            key = (_merge_key(line.item), kind)
            entry = totals.setdefault(key, {"item": line.item, "base": Fraction(0),
                                            "units": set(), "meals": []})
            entry["base"] += base
            entry["units"].add(line.unit)
            if meal_name not in entry["meals"]:
                entry["meals"].append(meal_name)
    rows = [
        ListRow(item=e["item"], amount=describe(e["base"], kind, e["units"]), used_in=e["meals"])
        for (key, kind), e in totals.items()
    ]
    rows.sort(key=lambda r: (_merge_key(r.item), r.amount.unit or ""))
    return rows, not_scaled
