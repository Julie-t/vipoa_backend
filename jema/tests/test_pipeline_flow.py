#!/usr/bin/env python3
"""
Pipeline Flow Tests for Jema ProfileContext

Verifies the ProfileContext data flow contract:
- filter_csv() removes forbidden ingredients before recipe selection
- personalisation block reaches the LLM system prompt
- scan_response() catches dietary violations
- All profile constraints are properly isolated and applied

Run with:
    python jema/tests/test_pipeline_flow.py

No Django required. Tests run in isolation with mock DataFrames.
"""

import os
import sys
import logging
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# LOAD .ENV FIRST — before any package imports
# ──────────────────────────────────────────────────────────────────────────────
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=env_path)
    except ImportError:
        # dotenv not installed, continue without it
        pass

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
from unittest.mock import MagicMock, patch, call
from jema.services.profile_context import ProfileContext, ProfileMissingError

# ──────────────────────────────────────────────────────────────────────────────
# LOGGING SETUP
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.DEBUG, format="%(message)s")

# ──────────────────────────────────────────────────────────────────────────────
# TEST HARNESS
# ──────────────────────────────────────────────────────────────────────────────
failures = []
passed = 0

def test(name, condition, detail=""):
    """Record test result."""
    global passed, failures
    if condition:
        print(f"  PASS  {name}")
        passed += 1
    else:
        print(f"  FAIL  {name}{' — ' + detail if detail else ''}")
        failures.append(name)


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 1: ProfileContext Isolation Tests
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("SECTION 1: ProfileContext Isolation Tests")
print("="*70)

# TEST 1.1 — ProfileMissingError on None
print("\nTEST 1.1 — None profile raises ProfileMissingError")
try:
    ProfileContext(None)
    test("1.1 None profile raises ProfileMissingError", False, "No exception raised")
except ProfileMissingError:
    test("1.1 None profile raises ProfileMissingError", True)

# TEST 1.2 — Vegan profile forbidden set completeness
print("\nTEST 1.2 — Vegan profile forbidden set completeness")
p = ProfileContext({
    "diet": "vegan",
    "religion": "",
    "allergies": [],
    "dislikes": [],
    "medical_conditions": [],
    "goal": "maintain",
    "cooking_level": "novice",
    "calorie_target": 2000
})
required = ["chicken", "beef", "lamb", "pork", "fish", "egg", "eggs", "milk", "cheese", "butter", "honey"]
for token in required:
    test(f"1.2 vegan forbidden includes '{token}'", token in p.forbidden)

# TEST 1.3 — Muslim profile forbidden set
print("\nTEST 1.3 — Muslim profile forbidden set")
p = ProfileContext({
    "diet": "balanced",
    "religion": "muslim",
    "allergies": [],
    "dislikes": [],
    "medical_conditions": [],
    "goal": "maintain",
    "cooking_level": "intermediate",
    "calorie_target": 2000
})
for token in ["pork", "bacon", "alcohol", "wine", "beer", "lard"]:
    test(f"1.3 muslim forbidden includes '{token}'", token in p.forbidden)

# TEST 1.4 — Nut allergy forbidden set
print("\nTEST 1.4 — Nut allergy forbidden set")
p = ProfileContext({
    "diet": "balanced",
    "religion": "",
    "allergies": ["nuts"],
    "dislikes": [],
    "medical_conditions": [],
    "goal": "maintain",
    "cooking_level": "novice",
    "calorie_target": 2000
})
for token in ["almond", "almonds", "cashew", "cashews", "peanut", "peanut butter", "walnut", "nuts"]:
    test(f"1.4 nut allergy forbidden includes '{token}'", token in p.forbidden)

# TEST 1.5 — Dislikes added to forbidden
print("\nTEST 1.5 — Dislikes added to forbidden")
p = ProfileContext({
    "diet": "balanced",
    "religion": "",
    "allergies": [],
    "dislikes": ["fish", "lamb"],
    "medical_conditions": [],
    "goal": "maintain",
    "cooking_level": "novice",
    "calorie_target": 2000
})
test("1.5 dislike 'fish' in forbidden", "fish" in p.forbidden)
test("1.5 dislike 'lamb' in forbidden", "lamb" in p.forbidden)


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 2: filter_csv() Data Flow Tests
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("SECTION 2: filter_csv() Data Flow Tests")
print("="*70)

# TEST 2.1 — filter_csv removes lamb from vegan profile
print("\nTEST 2.1 — filter_csv removes lamb from vegan profile")
p = ProfileContext({
    "diet": "vegan",
    "religion": "",
    "allergies": [],
    "dislikes": [],
    "medical_conditions": [],
    "goal": "maintain",
    "cooking_level": "novice",
    "calorie_target": 2000
})
test_df = pd.DataFrame([
    {"meal_name": "Lentil Soup", "core_ingredients": "lentils, onion, tomato, oil", "cook_time_minutes": 30},
    {"meal_name": "Lamb Stew", "core_ingredients": "lamb, onion, potato, carrot", "cook_time_minutes": 60},
    {"meal_name": "Jollof Rice", "core_ingredients": "rice, tomato, pepper, onion", "cook_time_minutes": 45},
])
result = p.filter_csv(test_df)
names = list(result["meal_name"])
test("2.1 Lamb Stew removed from vegan filter", "Lamb Stew" not in names)
test("2.1 Lentil Soup kept in vegan filter", "Lentil Soup" in names)
test("2.1 Jollof Rice kept in vegan filter", "Jollof Rice" in names)

# TEST 2.2 — filter_csv removes nut-containing recipes
print("\nTEST 2.2 — filter_csv removes nut-containing recipes")
p = ProfileContext({
    "diet": "balanced",
    "religion": "",
    "allergies": ["nuts"],
    "dislikes": [],
    "medical_conditions": [],
    "goal": "maintain",
    "cooking_level": "novice",
    "calorie_target": 2000
})
test_df = pd.DataFrame([
    {"meal_name": "Groundnut Soup", "core_ingredients": "groundnuts, chicken, pepper", "cook_time_minutes": 60},
    {"meal_name": "Tomato Stew", "core_ingredients": "tomato, onion, oil, pepper", "cook_time_minutes": 25},
])
result = p.filter_csv(test_df)
names = list(result["meal_name"])
test("2.2 Groundnut Soup removed for nut allergy", "Groundnut Soup" not in names)
test("2.2 Tomato Stew kept for nut allergy profile", "Tomato Stew" in names)

# TEST 2.3 — filter_csv never returns empty DataFrame
print("\nTEST 2.3 — filter_csv never returns empty DataFrame")
p = ProfileContext({
    "diet": "vegan",
    "religion": "muslim",
    "allergies": ["nuts", "gluten", "dairy"],
    "dislikes": ["rice", "tomato"],
    "medical_conditions": ["diabetes"],
    "goal": "lose weight",
    "cooking_level": "novice",
    "calorie_target": 1200
})
tiny_df = pd.DataFrame([
    {"meal_name": "Only Option", "core_ingredients": "water, salt", "cook_time_minutes": 5}
])
result = p.filter_csv(tiny_df)
test("2.3 filter_csv never returns empty DataFrame", len(result) > 0)

# TEST 2.4 — filter_csv output is a strict subset of input
print("\nTEST 2.4 — filter_csv output is a strict subset of input")
p = ProfileContext({
    "diet": "vegan",
    "religion": "",
    "allergies": [],
    "dislikes": [],
    "medical_conditions": [],
    "goal": "maintain",
    "cooking_level": "novice",
    "calorie_target": 2000
})
test_df = pd.DataFrame([
    {"meal_name": "Vegan Dish", "core_ingredients": "tofu, rice, vegetables", "cook_time_minutes": 30},
    {"meal_name": "Meat Dish", "core_ingredients": "beef, onion, pepper", "cook_time_minutes": 45},
])
result = p.filter_csv(test_df)
test("2.4 filter result rows <= input rows", len(result) <= len(test_df))
test("2.4 filter result is subset of input", all(r in test_df["meal_name"].values for r in result["meal_name"].values))


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 3: build_personalisation_block() Tests
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("SECTION 3: build_personalisation_block() Tests")
print("="*70)

# TEST 3.1 — Block is always non-empty
print("\nTEST 3.1 — Block is always non-empty")
p = ProfileContext({
    "diet": "balanced",
    "religion": "",
    "allergies": [],
    "dislikes": [],
    "medical_conditions": [],
    "goal": "maintain",
    "cooking_level": "novice",
    "calorie_target": 2000
})
block = p.build_personalisation_block()
test("3.1 personalisation block non-empty", len(block.strip()) > 0)

# TEST 3.2 — Block contains required headers and sections
print("\nTEST 3.2 — Block contains required headers and sections")
p = ProfileContext({
    "diet": "vegan",
    "religion": "muslim",
    "allergies": ["nuts"],
    "dislikes": [],
    "medical_conditions": [],
    "goal": "lose weight",
    "cooking_level": "novice",
    "calorie_target": 1500
})
block = p.build_personalisation_block()
test("3.2 block contains ABSOLUTE header", "ABSOLUTE" in block)
test("3.2 block contains HALAL section", "HALAL" in block)
test("3.2 block contains WEIGHT LOSS section", "WEIGHT LOSS" in block or "LOSS" in block)
test("3.2 block contains NOVICE section", "NOVICE" in block)
test("3.2 block contains STOCK CUBE rule", "STOCK CUBE" in block)

# TEST 3.3 — Diabetes tip requirement present
print("\nTEST 3.3 — Diabetes tip requirement present")
p = ProfileContext({
    "diet": "balanced",
    "religion": "",
    "allergies": [],
    "dislikes": [],
    "medical_conditions": ["diabetes"],
    "goal": "eat healthier",
    "cooking_level": "basic",
    "calorie_target": 1800
})
block = p.build_personalisation_block()
test("3.3 block contains DIABETES section", "DIABETES" in block)
test("3.3 block requires blood sugar tip", "blood sugar" in block.lower() or "blood glucose" in block.lower())


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 4: scan_response() Tests
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("SECTION 4: scan_response() Tests")
print("="*70)

# TEST 4.1 — Clean response not flagged
print("\nTEST 4.1 — Clean response not flagged")
p = ProfileContext({
    "diet": "vegan",
    "religion": "",
    "allergies": ["nuts"],
    "dislikes": [],
    "medical_conditions": [],
    "goal": "maintain",
    "cooking_level": "novice",
    "calorie_target": 2000
})
result = p.scan_response("Here is a recipe with tomatoes, lentils, and spinach.")
test("4.1 clean response unchanged", "[Dietary note" not in result)

# TEST 4.2 — Nut violation flagged
print("\nTEST 4.2 — Nut violation flagged")
p = ProfileContext({
    "diet": "balanced",
    "religion": "",
    "allergies": ["nuts"],
    "dislikes": [],
    "medical_conditions": [],
    "goal": "maintain",
    "cooking_level": "novice",
    "calorie_target": 2000
})
result = p.scan_response("This dish uses almonds for extra crunch and cashew cream.")
test("4.2 nut violation flagged in response", "[Dietary note" in result)

# TEST 4.3 — Pork violation flagged for Muslim
print("\nTEST 4.3 — Pork violation flagged for Muslim")
p = ProfileContext({
    "diet": "balanced",
    "religion": "muslim",
    "allergies": [],
    "dislikes": [],
    "medical_conditions": [],
    "goal": "maintain",
    "cooking_level": "intermediate",
    "calorie_target": 2000
})
result = p.scan_response("You could add some bacon bits for extra flavour.")
test("4.3 pork violation flagged for Muslim profile", "[Dietary note" in result)


# ──────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"\nPipeline Flow Tests: {passed} passed, {len(failures)} failed")

if failures:
    print("\nFailed tests:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("\n✓ ALL PIPELINE FLOW TESTS PASSED")
    sys.exit(0)
