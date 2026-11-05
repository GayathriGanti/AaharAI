from recipe_engine import load_recipe_database, search_recipes
db=load_recipe_database(); r=db["recipes"]
assert len(r)==300 and r["recipe_id"].is_unique and r["recipe_name"].str.casefold().is_unique
assert set(db["recipe_ingredients"]["recipe_id"]).issubset(set(r["recipe_id"]))
assert set(db["recipe_ingredients"]["ingredient_id"]).issubset(set(db["ingredients"]["ingredient_id"]))
assert not search_recipes("chicken",db).empty
assert not search_recipes("chickpeas",db).empty
assert not search_recipes("idli",db).empty
print("PASS: 300 unique recipes, valid links and recipe-only search.")
