# Recipe database

This folder contains a normalized recipe database used by the diet recommendation project.

## Files
- `recipes.csv`: recipe metadata, preparation instructions, servings, and calculated nutrition per serving.
- `ingredients.csv`: ingredient reference nutrition per 100 g.
- `recipe_ingredients.csv`: ingredient quantities for each whole recipe.
- `recipe_tags.csv`: dietary, meal-type, cuisine, and nutrition-oriented tags.

## Nutrition method
For each recipe, the reference nutrient value of each ingredient is multiplied by its gram quantity / 100. Ingredient contributions are summed for the full recipe and divided by the recipe serving count.

**Important:** these are reference estimates, not laboratory measurements or medical nutrition prescriptions. Actual values vary by brand, ingredient variety, edible yield, water absorption, cooking method, and discarded cooking liquid. Validate ingredient values against one consistent food-composition database and product labels before production use. Sodium and micronutrients are not currently calculated.

## Quantity conventions
- Ingredient quantities represent the whole recipe.
- Dry weights are used for dry grains and pulses.
- Recipe nutrition fields are per serving.
- Water, salt, and some spices may be omitted where their energy contribution is negligible. This means sodium tracking is not supported yet.

## Current coverage
- 100 starter recipes
- 63 ingredient records
- 710 recipe-to-ingredient links
- South Indian, Andhra, North Indian, other Indian, and international-inspired dishes
- Vegetarian and vegan metadata
- Breakfast, lunch, dinner, snack, side, drink, and dessert meal labels

The current expansion includes curated base recipes and controlled ingredient variations. Review cooking instructions and nutrition estimates before presenting any recipe as a precise or clinically appropriate recommendation.
