"""Build a clean USDA Foundation Foods nutrition table.

Nutrient values in FoodData Central Foundation Foods are generally reported
per 100 g. This script keeps that basis explicit and avoids randomly joining
food nutrients to synthetic user calorie records.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "datasets" / "raw" / "FoodData_Central_foundation_food_csv_2026-04-30"
FOOD_PATH = RAW / "food.csv"
FOOD_NUTRIENT_PATH = RAW / "food_nutrient.csv"
OUTPUT_PATH = ROOT / "Cleaned_data" / "usda_food_nutrition_per_100g.csv"

# USDA nutrient IDs: Energy (kcal), Protein, Carbohydrate, Total fat, Dietary fibre.
NUTRIENTS = {
    1008: "calories",
    1003: "protein",
    1005: "carbs",
    1004: "fat",
    1079: "fiber",
}


def main():
    foods = pd.read_csv(FOOD_PATH, usecols=["fdc_id", "description"])
    foods = foods.rename(columns={"description": "food"})
    food_nutrients = pd.read_csv(
        FOOD_NUTRIENT_PATH,
        usecols=["fdc_id", "nutrient_id", "amount"],
    )
    food_nutrients = food_nutrients[
        food_nutrients["nutrient_id"].isin(NUTRIENTS)
    ]
    pivot = food_nutrients.pivot_table(
        index="fdc_id", columns="nutrient_id", values="amount", aggfunc="mean"
    ).rename(columns=NUTRIENTS).reset_index()
    result = foods.merge(pivot, on="fdc_id", how="inner")
    nutrient_columns = list(NUTRIENTS.values())
    for column in nutrient_columns:
        if column not in result:
            result[column] = pd.NA
        result[column] = pd.to_numeric(result[column], errors="coerce")
    # Missing values remain missing. Zero is a real value and is not used as a
    # substitute for missing nutrient measurements.
    result = result.dropna(subset=["calories"])
    result = result[result["calories"] > 0]
    result = result.drop_duplicates(subset=["fdc_id"])
    result = result[["fdc_id", "food", *nutrient_columns]]
    result["nutrition_basis"] = "per 100 g"
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved {len(result):,} foods to {OUTPUT_PATH}")
    print("Nutrition values are reported per 100 g; missing nutrients remain blank.")


if __name__ == "__main__":
    main()
