"""Tests for scaling.py. Run with:  .\\.venv\\Scripts\\python -m unittest test_scaling"""
import unittest
from fractions import Fraction as F

from scaling import (combined_list, format_amount, line_from_parts, parse_line, parse_quantity,
                     scale, scaled_rows, split_line)


def scaled_text(line_text, factor):
    return format_amount(scale(parse_line(line_text), factor))


class ParseTests(unittest.TestCase):
    def test_amount_forms(self):
        self.assertEqual(parse_line("3 eggs").amount, 3)
        self.assertEqual(parse_line("1.5 cups milk").amount, F(3, 2))
        self.assertEqual(parse_line("1/2 tsp salt").amount, F(1, 2))
        self.assertEqual(parse_line("1 1/2 lb chicken").amount, F(3, 2))
        self.assertEqual(parse_line("½ cup sugar").amount, F(1, 2))
        self.assertEqual(parse_line("1½ cups flour").amount, F(3, 2))
        self.assertEqual(parse_line("2lb beef").unit, "lb")

    def test_units_and_item(self):
        line = parse_line("1 1/2 lb chicken thighs")
        self.assertEqual((line.unit, line.item), ("lb", "chicken thighs"))
        self.assertEqual(parse_line("2 Tablespoons butter").unit, "tbsp")
        self.assertEqual(parse_line("2 T butter").unit, "tbsp")
        self.assertEqual(parse_line("2 t salt").unit, "tsp")
        self.assertEqual(parse_line("8 fl oz cream").unit, "fl oz")
        self.assertEqual(parse_line("8 oz cheese").unit, "oz")
        self.assertEqual(parse_line("2 Liters water").unit, "l")
        self.assertEqual(parse_line("3 tsp. vanilla").unit, "tsp")

    def test_unknown_unit_is_part_of_item(self):
        line = parse_line("2 cans tomatoes")
        self.assertEqual((line.amount, line.unit, line.item), (2, None, "cans tomatoes"))
        line = parse_line("3 garlic cloves")
        self.assertEqual((line.unit, line.item), (None, "garlic cloves"))

    def test_not_scaled(self):
        for text in ["pepper to taste", "salt", "2-3 sprigs thyme", "a pinch of salt"]:
            self.assertFalse(parse_line(text).scaled, text)
        self.assertIsNone(format_amount(parse_line("pepper to taste")))


class DisplayRuleTests(unittest.TestCase):
    def test_examples_from_plan(self):
        self.assertEqual(scaled_text("18.75 lb beef", 1), "19 lb (18.75 lb)")
        self.assertEqual(scaled_text("88 tsp salt", 1), "2 cups (88 tsp)")
        self.assertEqual(scaled_text("48 tsp salt", 1), "1 cup (48 tsp)")
        self.assertEqual(scaled_text("20 lb beef", 1), "20 lb")

    def test_check_steps_serves_4_for_100(self):
        factor = F(100, 4)
        self.assertEqual(scaled_text("2 cups rice", factor), "13 qt (50 cups)")
        self.assertEqual(scaled_text("1 1/2 lb chicken", factor), "38 lb (37.5 lb)")
        self.assertEqual(scaled_text("1/2 tsp salt", factor), "5 tbsp (12.5 tsp)")

    def test_small_amounts_round_up_to_quarters(self):
        self.assertEqual(scaled_text("0.3 tsp salt", 1), "½ tsp (0.3 tsp)")
        self.assertEqual(scaled_text("1 tsp salt", F(1, 4)), "¼ tsp")
        self.assertEqual(scaled_text("1 cup milk", 1), "1 cup")

    def test_count_items_round_up_whole(self):
        self.assertEqual(scaled_text("3 eggs", F(3, 2)), "5 (4.5)")
        self.assertEqual(scaled_text("1 egg", F(1, 3)), "1 (0.33)")
        self.assertEqual(scaled_text("2 cans tomatoes", 10), "20")

    def test_ladders(self):
        self.assertEqual(scaled_text("6 tsp oil", 1), "2 tbsp (6 tsp)")
        self.assertEqual(scaled_text("16 cups stock", 1), "1 gal (16 cups)")
        self.assertEqual(scaled_text("8 fl oz cream", 1), "1 cup (8 fl oz)")
        self.assertEqual(scaled_text("3 pt cream", 1), "6 cups (3 pt)")  # 2 qt would be +33%
        self.assertEqual(scaled_text("40 oz cheese", 1), "3 lb (40 oz)")
        self.assertEqual(scaled_text("1500 g flour", 1), "1500 g")  # 2 kg would be +33%
        self.assertEqual(scaled_text("1800 g flour", 1), "2 kg (1800 g)")
        self.assertEqual(scaled_text("250 ml milk", 1), "250 ml")
        self.assertEqual(scaled_text("2500 ml milk", 1), "3 l (2500 ml)")

    def test_big_unit_skipped_when_rounding_wastes_too_much(self):
        self.assertEqual(scaled_text("50 cups rice", 1), "13 qt (50 cups)")  # not 4 gal
        self.assertEqual(scaled_text("64 cups stock", 1), "4 gal (64 cups)")
        self.assertEqual(scaled_text("1.1 cups milk", 1), "18 tbsp (1.1 cups)")

    def test_no_cross_system_conversion(self):
        self.assertEqual(scaled_text("1000 g sugar", 1), "1 kg (1000 g)")
        self.assertTrue(scaled_text("32 oz sugar", 1).startswith("2 lb"))


class ListTests(unittest.TestCase):
    def test_scaled_rows_keep_order_and_not_scaled(self):
        rows = scaled_rows("2 cups rice\npepper to taste\n\n1 egg", 2)
        self.assertEqual([r.item for r in rows], ["rice", "pepper to taste", "egg"])
        self.assertIsNone(rows[1].amount)
        self.assertEqual(rows[0].amount.text, "1 qt (4 cups)")

    def test_combined_merges_same_item_across_units(self):
        rows, not_scaled = combined_list([
            ("Meal A", "2 cups Rice\nsalt to taste", 10),   # 20 cups
            ("Meal B", "8 tbsp rice\n1 lb chicken", 2),    # 1 cup
        ])
        rice = [r for r in rows if r.item.lower() == "rice"]
        self.assertEqual(len(rice), 1)
        self.assertEqual(rice[0].amount.text, "6 qt (5.25 qt)")  # 21 cups; mixed original units -> exact in qt
        self.assertEqual(rice[0].used_in, ["Meal A", "Meal B"])
        self.assertEqual([r.item for r in rows], ["chicken", "Rice"])
        self.assertEqual([(r.text, r.used_in) for r in not_scaled], [("salt to taste", ["Meal A"])])

    def test_combined_rounds_once_per_item(self):
        rows, _ = combined_list([("A", "0.4 lb butter", 1), ("B", "0.4 lb butter", 1)])
        self.assertEqual(rows[0].amount.text, "13 oz (0.8 lb)")  # 12.8 oz, rounded once

    def test_combined_keeps_different_kinds_apart(self):
        rows, _ = combined_list([("A", "1 lb sugar", 1), ("B", "1 cup sugar", 1)])
        self.assertEqual(len(rows), 2)



class TableRowTests(unittest.TestCase):
    def test_parse_quantity(self):
        self.assertEqual(parse_quantity("1 1/2"), F(3, 2))
        self.assertEqual(parse_quantity(" 2 "), 2)
        self.assertEqual(parse_quantity("½"), F(1, 2))
        self.assertIsNone(parse_quantity(""))
        for bad in ["abc", "2 cups", "1/0", "2-3"]:
            with self.assertRaises(ValueError):
                parse_quantity(bad)

    def test_line_from_parts(self):
        line = line_from_parts("1 1/2", "lb", "chicken thighs")
        self.assertEqual((line.amount, line.unit, line.item), (F(3, 2), "lb", "chicken thighs"))
        line = line_from_parts("2", "Tablespoons", "butter")
        self.assertEqual(line.unit, "tbsp")
        line = line_from_parts("2", "cans", "crushed tomatoes")      # unit we don't convert
        self.assertEqual((line.unit, line.item), (None, "cans crushed tomatoes"))
        line = line_from_parts("3", "", "eggs")
        self.assertEqual((line.amount, line.unit, line.item), (3, None, "eggs"))
        line = line_from_parts("", "", "pepper to taste")
        self.assertFalse(line.scaled)
        self.assertEqual(line.text, "pepper to taste")
        # a name that looks like a unit must not be mistaken for one
        line = line_from_parts("2", "", "T-bone steaks")
        self.assertEqual(line.item, "T-bone steaks")

    def test_rows_scale_like_text(self):
        lines = [line_from_parts("2", "cups", "rice"), line_from_parts("1/2", "tsp", "salt")]
        rows = scaled_rows(lines, 25)
        self.assertEqual([r.amount.text for r in rows], ["13 qt (50 cups)", "5 tbsp (12.5 tsp)"])

    def test_split_old_lines(self):
        self.assertEqual(split_line("1 1/2 lb chicken thighs"), ("1 1/2", "lb", "chicken thighs"))
        self.assertEqual(split_line("2 Tablespoons butter"), ("2", "Tablespoons", "butter"))
        self.assertEqual(split_line("8 fl oz cream"), ("8", "fl oz", "cream"))
        self.assertEqual(split_line("3 eggs"), ("3", "", "eggs"))
        self.assertEqual(split_line("2 cans tomatoes"), ("2", "", "cans tomatoes"))
        self.assertEqual(split_line("½ cup sugar"), ("1/2", "cup", "sugar"))
        self.assertEqual(split_line("pepper to taste"), ("", "", "pepper to taste"))
        self.assertEqual(split_line("2 cups"), ("2", "cups", ""))


if __name__ == "__main__":
    unittest.main()
