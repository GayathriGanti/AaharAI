
from recipe_engine import load_recipe_database, search_recipes_by_ingredients, parse_ingredient_input
from recipe_meal_planner import find_meal_replacements, generate_recipe_meal_plan

db = load_recipe_database()
recipes = db["recipes"].copy()
links = db["recipe_ingredients"].merge(
    db["ingredients"][["ingredient_id", "ingredient_name"]], on="ingredient_id", how="left"
)
recipes["ingredient_names"] = recipes["recipe_id"].map(
    links.groupby("recipe_id")["ingredient_name"].apply(lambda x: " | ".join(x.astype(str)))
).fillna("")

assert parse_ingredient_input("aloo, gobi\npaneer; onion") == ["aloo", "gobi", "paneer", "onion"]
all_matches = search_recipes_by_ingredients(["aloo", "gobi"], "all", db, 100)
assert not all_matches.empty, "Alias-based all-ingredient search should return matches."
chicken_matches = search_recipes_by_ingredients(["chicken"], "any", db, 100)
assert not chicken_matches.empty, "Broad chicken search should match named chicken ingredients."

plan = generate_recipe_meal_plan(recipes, 2000, 3, 7)
assert not plan.empty
sample = plan.iloc[0]
alternatives = find_meal_replacements(
    recipes, sample["Recipe ID"], sample["Meal"],
    sample["Calories (kcal)"], sample["Protein (g)"], limit=12
)
assert sample["Recipe ID"] not in set(alternatives["recipe_id"])
print(f"PASS: free-text parsing, aliases, chicken ingredient search and meal replacement ({len(alternatives)} alternatives).")
