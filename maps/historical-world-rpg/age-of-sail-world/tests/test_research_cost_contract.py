"""Compare executed live literals with an independent rational oracle and headless costs."""
from datetime import date
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
import re
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared'))
from engine.technology_institutions import TechnologyInstitutionRuntime


def precision28(value):
    """Independent integer implementation of significant-digit ties-to-even."""
    scale = 0
    while 10**scale % value.denominator:
        scale += 1
    coefficient = value.numerator * (10**scale // value.denominator)
    excess = len(str(coefficient)) - 28
    if excess <= 0:
        return value
    divisor = 10**excess
    whole, remainder = divmod(coefficient, divisor)
    if 2 * remainder > divisor or 2 * remainder == divisor and whole % 2:
        whole += 1
    return Fraction(whole) * Fraction(10)**(excess - scale)


class ResearchCostContractTests(unittest.TestCase):
    def test_live_fixtures_match_rational_arithmetic_and_headless_contract(self):
        source = (PROJECT / 'wurst/ResearchCostTests.wurst').read_text()
        fixtures = re.findall(r'assertCost\("([^"]+)","([^"]+)","([^"]+)",(-?\d+),(\d+),"(\d+)",(-?\d+)\)', source)
        self.assertGreaterEqual(len(fixtures), 20)
        for base, ahead, annual, preferred, year, units, gold in fixtures:
            with self.subTest(base=base, preferred=preferred, year=year):
                years = max(0, int(preferred) - int(year))
                multiplier = precision28(Fraction(ahead) + precision28(Fraction(annual) * years)) if years else 1
                exact = precision28(Fraction(base) * multiplier)
                scaled = exact * 1_000_000
                rational_units = (2 * scaled.numerator + scaled.denominator) // (2 * scaled.denominator)
                self.assertEqual(int(units), rational_units)
                cost = dict(preferredYear=int(preferred), baseCost=Decimal(base),
                            aheadOfTimeCostMultiplier=Decimal(ahead), additionalMultiplierPerYearAhead=Decimal(annual))
                runtime = TechnologyInstitutionRuntime(dict(polities=[], provinces=[], institutions=[], technologies=[
                    dict(id='fixture', prerequisiteIds=[], unlocks=[], timeCost=cost)]), '1450-01-01')
                self.assertEqual(int(units), runtime.cost_units('fixture', date(int(year), 1, 1).isoformat()))
                charge = (rational_units + 999_999) // 1_000_000
                self.assertEqual(int(gold), charge if 1 <= charge <= 2**31 - 1 else -1)
