"""Smoke tests for the recipe-based meal planner. Run from project root:
python python/test_recipe_meal_planner.py
"""

from recipe_engine import load_recipe_database
from recipe_meal_planner import generate_recipe_meal_plan


def main():
    database = load_recipe_database()
    recipes = database["recipes"].copy()
    links = database["recipe_ingredients"].merge(
        database["ingredients"][["ingredient_id", "ingredient_name"]],
        on="ingredient_id",
        how="left",
    )
    names = links.groupby("recipe_id")["ingredient_name"].apply(
        lambda values: " | ".join(sorted(set(values.dropna().astype(str))))
    )
    recipes["ingredient_names"] = recipes["recipe_id"].map(names).fillna("")

    standard = generate_recipe_meal_plan(recipes, 2000, meals_per_day=3, days=7)
    assert len(standard) == 21
    assert standard["Planned servings"].between(0.5, 2.5).all()
    assert standard["Recipe"].notna().all()
    # A day should not repeat the same recipe across its meal slots.
    assert not standard.duplicated(subset=["Day", "Recipe ID"]).any()
    # The same breakfast/lunch/dinner should not be repeated on adjacent days
    # when the filtered recipe pool has enough alternatives.
    for meal_name, group in standard.groupby("Meal"):
        ids = group.sort_values("Day")["Recipe ID"].tolist()
        assert all(ids[i] != ids[i - 1] for i in range(1, len(ids))), meal_name

    vegan = generate_recipe_meal_plan(
        recipes, 1800, meals_per_day=3, days=7, diet_preference="Vegan"
    )
    assert not vegan.empty
    assert vegan["Diet"].str.casefold().eq("vegan").all()

    nonveg = generate_recipe_meal_plan(
        recipes, 2000, meals_per_day=3, days=7, diet_preference="Non-vegetarian"
    )
    assert not nonveg.empty
    assert nonveg[nonveg["Meal"].isin(["Lunch", "Dinner"])]["Diet"].eq("Non-vegetarian").all()

    andhra = generate_recipe_meal_plan(
        recipes, 1800, meals_per_day=3, days=7, cuisine="Andhra"
    )
    assert not andhra.empty
    assert andhra["Cuisine"].eq("Andhra").all()

    peanut_free = generate_recipe_meal_plan(
        recipes, 1800, meals_per_day=3, days=7, excluded_ingredients=["Peanuts"]
    )
    selected_names = peanut_free["Recipe ID"].map(
        recipes.set_index("recipe_id")["ingredient_names"]
    )
    assert not selected_names.str.contains("Peanuts", case=False).any()

    print("PASS: 7-day plan, portion scaling, vegan/non-vegetarian filters, cuisine filter and ingredient exclusion.")


if __name__ == "__main__":
    main()
