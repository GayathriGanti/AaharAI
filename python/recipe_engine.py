"""Recipe database access and filtering helpers.

This module is deliberately independent of Streamlit so it can be tested
before being connected to the existing app.
"""
from pathlib import Path
import re
import pandas as pd

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "datasets" / "recipes"


def load_recipe_database(data_dir=DEFAULT_DATA_DIR):
    """Load the normalized recipe tables and validate their relationships."""
    data_dir = Path(data_dir)
    required = {
        "recipes": data_dir / "recipes.csv",
        "ingredients": data_dir / "ingredients.csv",
        "recipe_ingredients": data_dir / "recipe_ingredients.csv",
        "recipe_tags": data_dir / "recipe_tags.csv",
    }
    missing = [str(path) for path in required.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing recipe database file(s): " + ", ".join(missing))

    tables = {name: pd.read_csv(path) for name, path in required.items()}
    recipes = tables["recipes"]
    ingredients = tables["ingredients"]
    links = tables["recipe_ingredients"]

    if recipes["recipe_id"].duplicated().any():
        raise ValueError("recipes.csv contains duplicate recipe_id values.")
    if not set(links["recipe_id"]).issubset(set(recipes["recipe_id"])):
        raise ValueError("recipe_ingredients.csv references an unknown recipe_id.")
    if not set(links["ingredient_id"]).issubset(set(ingredients["ingredient_id"])):
        raise ValueError("recipe_ingredients.csv references an unknown ingredient_id.")

    return tables


def get_recipe_details(recipe_id, database=None):
    """Return one recipe plus its ingredient names and quantities."""
    database = database or load_recipe_database()
    matches = database["recipes"].loc[database["recipes"]["recipe_id"] == recipe_id]
    if matches.empty:
        return None
    recipe = matches.iloc[0].to_dict()
    links = database["recipe_ingredients"].loc[
        database["recipe_ingredients"]["recipe_id"] == recipe_id
    ].merge(database["ingredients"], on="ingredient_id", how="left")
    recipe["ingredients"] = links[
        ["ingredient_name", "quantity_g", "ingredient_state_note"]
    ].to_dict("records")
    return recipe


def recommend_recipes(
    meal_type=None,
    diet_type=None,
    cuisine=None,
    excluded_ingredients=None,
    max_prep_time=None,
    min_protein_g=None,
    max_kcal=None,
    limit=20,
    database=None,
):
    """Filter recipes by explicit preferences; never infer goals from BMI."""
    database = database or load_recipe_database()
    results = database["recipes"].copy()

    if meal_type:
        results = results[results["meal_type"].str.casefold() == meal_type.casefold()]
    if diet_type:
        results = results[results["diet_type"].str.casefold() == diet_type.casefold()]
    if cuisine:
        results = results[results["cuisine"].str.casefold() == cuisine.casefold()]
    if max_prep_time is not None:
        results = results[
            (results["prep_time_min"] + results["cook_time_min"]) <= max_prep_time
        ]
    if min_protein_g is not None:
        results = results[results["protein_g"] >= min_protein_g]
    if max_kcal is not None:
        results = results[results["kcal"] <= max_kcal]

    excluded = {str(item).strip().casefold() for item in (excluded_ingredients or [])}
    if excluded and not results.empty:
        links = database["recipe_ingredients"].merge(
            database["ingredients"][["ingredient_id", "ingredient_name"]],
            on="ingredient_id",
            how="left",
        )
        bad_ids = links.loc[
            links["ingredient_name"].str.casefold().isin(excluded), "recipe_id"
        ].unique()
        results = results[~results["recipe_id"].isin(bad_ids)]

    return results.sort_values(["protein_g", "kcal"], ascending=[False, True]).head(limit).reset_index(drop=True)


def search_recipes(query, database=None, limit=60):
    """Search recipe names, linked ingredients and cuisine; never raw USDA rows."""
    database = database or load_recipe_database()
    query = str(query or "").strip()
    recipes = database["recipes"].copy()
    if not query: return recipes.head(0)
    links = database["recipe_ingredients"].merge(database["ingredients"][["ingredient_id","ingredient_name"]],on="ingredient_id",how="left")
    names = links.groupby("recipe_id")["ingredient_name"].apply(lambda s:" | ".join(s.dropna().astype(str)))
    recipes["ingredient_names"] = recipes["recipe_id"].map(names).fillna("")
    mask = (recipes["recipe_name"].fillna("").str.contains(query,case=False,regex=False)
            | recipes["ingredient_names"].str.contains(query,case=False,regex=False)
            | recipes["cuisine"].fillna("").str.contains(query,case=False,regex=False))
    return recipes.loc[mask].drop_duplicates("recipe_id").head(limit).reset_index(drop=True)


def search_recipes_by_ingredients(selected_ingredients, match_mode="all", database=None, limit=100):
    """Find recipes by a user's pantry list. 'all' requires every selected item; 'any' matches at least one."""
    database = database or load_recipe_database()
    selected = parse_ingredient_input(selected_ingredients)
    if not selected:
        return database["recipes"].head(0).copy()
    links = database["recipe_ingredients"].merge(
        database["ingredients"][["ingredient_id", "ingredient_name"]],
        on="ingredient_id", how="left"
    )
    grouped = links.groupby("recipe_id")["ingredient_name"].apply(
        lambda values: [str(v).strip() for v in values.dropna()]
    )
    matched_terms = grouped.apply(
        lambda available: [term for term in selected
                           if any(_ingredient_matches_query(name, term) for name in available)]
    )
    counts = matched_terms.apply(len)
    if str(match_mode).casefold() == "all":
        matching_ids = counts[counts == len(selected)].index
    else:
        matching_ids = counts[counts > 0].index
    results = database["recipes"][database["recipes"]["recipe_id"].isin(matching_ids)].copy()
    results["matched_ingredients"] = results["recipe_id"].map(counts).fillna(0).astype(int)
    results["matched_ingredient_names"] = results["recipe_id"].map(
        matched_terms.apply(lambda terms: ", ".join(terms))
    ).fillna("")
    results["selected_ingredient_count"] = len(selected)
    results["match_percent"] = (100 * results["matched_ingredients"] / len(selected)).round().astype(int)
    return results.sort_values(
        ["matched_ingredients", "protein_g", "kcal"],
        ascending=[False, False, True]
    ).head(limit).reset_index(drop=True)


# Common names users may type instead of the database's ingredient wording.
INGREDIENT_ALIASES = {
    "aloo": "potato", "urulai": "potato", "urulaikizhangu": "potato",
    "gobi": "cauliflower", "phool gobi": "cauliflower",
    "baingan": "brinjal", "eggplant": "brinjal", "aubergine": "brinjal",
    "bhindi": "okra", "ladies finger": "okra",
    "dahi": "curd", "yogurt": "curd", "yoghurt": "curd",
    "chana": "chickpeas", "kabuli chana": "chickpeas",
    "rajma": "kidney beans", "moong": "moong dal",
    "toor dal": "toor dal", "arhar dal": "toor dal",
    "atta": "whole wheat flour", "gehu atta": "whole wheat flour",
    "shimla mirch": "capsicum", "bell pepper": "capsicum",
    "hara dhania": "coriander leaves", "coriander": "coriander leaves",
    "dhania patta": "coriander leaves", "hara pyaz": "spring onion",
    "matar": "green peas", "peas": "green peas",
    "makka": "corn", "sweet corn": "corn",
    "anda": "egg", "eggs": "egg", "murgh": "chicken",
    "machli": "fish", "prawn": "prawns",
}

def parse_ingredient_input(value):
    """Parse user-entered ingredients separated by commas, semicolons or new lines."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = re.split(r"[,;\n]+", str(value))
    cleaned = []
    seen = set()
    for item in raw_items:
        item = re.sub(r"\s+", " ", str(item)).strip(" \t-•")
        key = item.casefold()
        if item and key not in seen:
            cleaned.append(item)
            seen.add(key)
    return cleaned

def _ingredient_matches_query(ingredient_name, query):
    name = str(ingredient_name or "").casefold().strip()
    query = str(query or "").casefold().strip()
    if not name or not query:
        return False
    alias = INGREDIENT_ALIASES.get(query, query)
    # Match natural user terms against ingredient names, e.g. "chicken" against
    # "Chicken breast, skinless" and "potato" against "Potato".
    return alias in name or name in alias or query in name


def ingredient_matches_query(ingredient_name, query):
    """Public wrapper used by the pantry UI to explain alias-based matches."""
    return _ingredient_matches_query(ingredient_name, query)
