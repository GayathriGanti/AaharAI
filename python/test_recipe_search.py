from recipe_engine import load_recipe_database, search_recipes_by_ingredients

db = load_recipe_database()
# Search should return recipes containing both ingredients when ALL is selected.
all_matches = search_recipes_by_ingredients(["Potato", "Cauliflower"], "all", db, 100)
assert not all_matches.empty
assert (all_matches["matched_ingredients"] == 2).all()
# ANY mode should include recipes containing either ingredient and rank by match count.
any_matches = search_recipes_by_ingredients(["Potato", "Cauliflower"], "any", db, 100)
assert len(any_matches) >= len(all_matches)
assert any_matches["matched_ingredients"].max() == 2
assert search_recipes_by_ingredients([], "all", db).empty
print(f"PASS: multi-ingredient search; all={len(all_matches)}, any={len(any_matches)}")
