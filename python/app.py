import os
import streamlit as st
import pandas as pd
import re

from pdf_generator import generate_pdf_report
from recipe_engine import load_recipe_database, get_recipe_details, search_recipes, search_recipes_by_ingredients, parse_ingredient_input, ingredient_matches_query
from recipe_meal_planner import generate_recipe_meal_plan, find_meal_replacements


# =====================================================
# BASE DIRECTORY & FILE PATHS
# =====================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(BASE_DIR, "Cleaned_data", "usda_food_nutrition_per_100g.csv")

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="AI Diet Recommendation System",
    page_icon="🥗",
    layout="wide"
)

st.markdown(
    """
    <div class="main-title-container"></div>
    """,
    unsafe_allow_html=True
)

page_bg = """
<style>
[data-testid="stAppViewContainer"] {
    background-color: #000000;
    color: white;
}

.main-title-container {
    background-image: url("https://www.eatingwell.com/thmb/YxkWBfh2AvNYrDKoHukRdmRvD5U=/750x0/filters:no_upscale():max_bytes(150000):strip_icc():format(webp)/article_291139_the-top-10-healthiest-foods-for-kids_-02-4b745e57928c4786a61b47d8ba920058.jpg");
    background-size: cover;
    background-position: center;
    height: 280px;
    border-radius: 20px;
    margin-bottom: 25px;
}

[data-testid="stSidebar"] {
    background-color: #111111;
}

h1, h2, h3, h4, h5, h6, p, label {
    color: white !important;
}

.stMetric {
    background-color: #1e1e1e;
    padding: 15px;
    border-radius: 15px;
    border: 1px solid #333333;
}

[data-testid="stDataFrame"] {
    background-color: #111111;
    border-radius: 15px;
}

.stButton>button {
    background-color: #00c853;
    color: white;
    border-radius: 10px;
    border: none;
    font-weight: bold;
}

.stDownloadButton>button {
    background-color: #ff9800;
    color: white;
    border-radius: 10px;
    border: none;
}

.stTextInput input, .stNumberInput input {
    background-color: #1e1e1e;
    color: white;
}

.stSlider {
    color: white;
}
/* SELECTBOX DROPDOWN FIX */
div[data-baseweb="popover"] * {
    color: #222222 !important;
}

div[data-baseweb="popover"] [role="option"] {
    background-color: white !important;
}

div[data-baseweb="popover"] [role="option"]:hover {
    background-color: #dddddd !important;
}
</style>
"""

st.markdown(page_bg, unsafe_allow_html=True)

# =====================================================
# LOAD DATASET
# =====================================================

df = pd.read_csv(DATASET_PATH)

try:
    RECIPE_DB = load_recipe_database()
    RECIPE_DF = RECIPE_DB["recipes"].copy()
    RECIPE_INGREDIENTS = RECIPE_DB["recipe_ingredients"].merge(
        RECIPE_DB["ingredients"][["ingredient_id", "ingredient_name"]],
        on="ingredient_id",
        how="left",
    )

    ingredient_names_by_recipe = RECIPE_INGREDIENTS.groupby("recipe_id")["ingredient_name"].apply(
        lambda values: " | ".join(sorted(set(values.dropna().astype(str))))
    )

    RECIPE_DF["ingredient_names"] = RECIPE_DF["recipe_id"].map(ingredient_names_by_recipe).fillna("")
    RECIPE_DB_ERROR = None

except Exception as exc:
    RECIPE_DB = None
    RECIPE_DF = pd.DataFrame()
    RECIPE_DB_ERROR = str(exc)


# =====================================================
# CLEANING FOOD COLUMNS
# =====================================================

def clean_food_name(food):
    food = str(food)
    food = re.sub(r"\s*\(.*?moisture.*?\)", "", food)
    food = re.sub(r",\s*[A-Z0-9\-]+$", "", food)
    food = re.sub(r",\s*\d+$", "", food)
    return food.strip()


df["food"] = df["food"].apply(clean_food_name)


def calculate_bmr(gender, weight, height, age):
    if gender == 1:
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    return round(bmr, 2)


# =====================================================
# RECOMMENDATION FUNCTION
# =====================================================

def calculate_goal_calories(tdee, selected_goal, age=None):
    if age is not None and age < 18:
        return round(tdee)

    if selected_goal == "Weight loss":
        return max(0, round(tdee * 0.90))

    if selected_goal == "Weight gain":
        return round(tdee * 1.08)

    return round(tdee)


def recommend_foods(
    gender,
    age,
    height,
    weight,
    meals_per_day,
    bmr,
    tdee,
    selected_goal,
):
    height_m = height / 100
    bmi = weight / (height_m ** 2)
    water_intake = round(weight * 0.033, 2)
    protein_need = round(weight * 1.6, 2)
    target_calories = calculate_goal_calories(tdee, selected_goal, age)

    recommendations = df.copy()

    required_columns = ["food", "calories", "protein", "carbs", "fat", "fiber"]

    recommendations = recommendations.dropna(subset=["food", "calories"])
    recommendations = recommendations[recommendations["food"].astype(str).str.len() > 3]
    recommendations = recommendations[recommendations["calories"] > 20]
    recommendations = recommendations.drop_duplicates(subset=["food"])

    for column in ["protein", "fiber", "carbs", "fat"]:
        recommendations[column] = pd.to_numeric(recommendations[column], errors="coerce")

    recommendations["protein"] = recommendations["protein"].fillna(0)
    recommendations["fiber"] = recommendations["fiber"].fillna(0)

    calorie_rank = recommendations["calories"].rank(pct=True)
    protein_rank = recommendations["protein"].rank(pct=True)
    fiber_rank = recommendations["fiber"].rank(pct=True)

    if selected_goal == "Weight loss":
        recommendations["score"] = (
            (1 - calorie_rank) * 0.45 + protein_rank * 0.35 + fiber_rank * 0.20
        )

    elif selected_goal == "Weight gain":
        recommendations["score"] = (
            calorie_rank * 0.45 + protein_rank * 0.40 + fiber_rank * 0.15
        )

    else:
        calorie_balance = 1 - (calorie_rank - 0.5).abs() * 2
        recommendations["score"] = (
            calorie_balance * 0.40 + protein_rank * 0.35 + fiber_rank * 0.25
        )

    recommendations = recommendations.sort_values("score", ascending=False)
    recommendations = recommendations.head(10)
    recommendations = recommendations[required_columns + ["nutrition_basis"]]

    return (
        selected_goal,
        round(bmi, 2),
        water_intake,
        protein_need,
        recommendations,
        target_calories,
    )


# =====================================================
# TITLE
# =====================================================

st.title("🥗 AI Personalized Diet Recommendation System")

st.markdown("""
### Get personalized food suggestions based on:
- Your selected fitness goal
- Estimated calorie needs (BMR and TDEE)
- BMI and body measurements
- Protein and other nutrient information

Your BMI is displayed as a health metric. It does not automatically select your fitness goal.
""")


# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("Enter Your Details")

gender = st.sidebar.selectbox("Gender", ["Male", "Female"])
gender_value = 1 if gender == "Male" else 0

age = st.sidebar.number_input("Age", min_value=18, max_value=100, value=24)
height = st.sidebar.number_input("Height (cm)", min_value=100, max_value=250, value=170)
weight = st.sidebar.number_input("Weight (kg)", min_value=20, max_value=250, value=70)

meals_per_day = st.sidebar.slider("Meals Per Day", 1, 10, 3)

activity_level = st.sidebar.selectbox(
    "Activity Level",
    ["Sedentary", "Lightly Active", "Moderately Active", "Very Active", "Extremely Active"]
)

selected_goal = st.sidebar.selectbox(
    "Fitness Goal",
    ["Weight loss", "Weight maintenance", "Weight gain"],
    index=1,
    help="Choose your goal. BMI is shown separately and does not automatically choose your goal."
)


def calculate_tdee(bmr, activity_level):
    activity_factors = {
        "Sedentary": 1.2,
        "Lightly Active": 1.375,
        "Moderately Active": 1.55,
        "Very Active": 1.725,
        "Extremely Active": 1.9
    }

    return round(bmr * activity_factors[activity_level], 2)


# =====================================================
# GENERATE BUTTON
# =====================================================

if st.sidebar.button("Generate Recommendation"):

    bmr = calculate_bmr(gender_value, weight, height, age)
    tdee = calculate_tdee(bmr, activity_level)

    goal, bmi, water, protein, foods, target_calories = recommend_foods(
        gender=gender_value,
        age=age,
        height=height,
        weight=weight,
        meals_per_day=meals_per_day,
        bmr=bmr,
        tdee=tdee,
        selected_goal=selected_goal,
    )

    st.session_state.goal = goal
    st.session_state.bmi = bmi
    st.session_state.water = water
    st.session_state.protein = protein
    st.session_state.foods = foods
    st.session_state.bmr = bmr
    st.session_state.tdee = tdee
    st.session_state.target_calories = target_calories
    st.session_state.generated = True


# =====================================================
# LOAD SAVED RESULTS
# =====================================================

if st.session_state.get("generated", False):

    goal = st.session_state.goal
    bmi = st.session_state.bmi
    water = st.session_state.water
    protein = st.session_state.protein
    foods = st.session_state.foods
    bmr = st.session_state.bmr
    tdee = st.session_state.tdee
    target_calories = st.session_state.get("target_calories", round(tdee))

    foods = foods[foods["food"].notna()]
    foods = foods[foods["food"].str.len() > 5]

    foods = foods[
        ~foods["food"].str.contains("raw|inedible|refuse", case=False, na=False)
    ]

    st.success(f"🎯 Your Selected Goal: {goal}")

    # =================================================
    # BMI STATUS
    # =================================================

    if age < 18:
        st.info("BMI is displayed for reference. Adult BMI categories are not used for people under 18; age- and sex-specific assessment is needed.")
    elif bmi < 18.5:
        st.warning("⚠️ You are Underweight")
    elif bmi < 25:
        st.success("✅ You are Healthy")
    elif bmi < 30:
        st.warning("⚠️ You are Overweight")
    else:
        st.error("🚨 Obesity Risk")

    # =================================================
    # METRICS
    # =================================================

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("BMI", bmi)

    with col2:
        st.metric("Daily Water Intake", f"{water} L")

    with col3:
        st.metric("Daily Protein Need", f"{protein} g")

    col4, col5 = st.columns(2)

    with col4:
        st.metric("BMR", round(bmr))

    with col5:
        st.metric("Estimated Daily Calorie Target", target_calories)

    st.caption("Calorie targets are approximate planning estimates, not medical prescriptions. The selected goal applies a 10% deficit or 8% surplus for adults; maintenance uses estimated TDEE.")

    # =================================================
    # BMI PROGRESS BAR
    # =================================================

    st.subheader("BMI Indicator")
    st.progress(min(int(bmi * 4), 100))

    # =================================================
    # RECIPE SEARCH + COOK WITH WHAT I HAVE
    # =================================================

    if RECIPE_DB_ERROR:
        st.error(f"Recipe database could not be loaded: {RECIPE_DB_ERROR}")

    else:
        search_tab, pantry_tab = st.tabs(["🔎 Search Recipes", "🥘 Cook With What I Have"])

        with search_tab:
            st.subheader("Search Recipes")
            st.caption("Search by dish name, cuisine or ingredients. Enter several ingredients separated by commas.")

            with st.form("free_text_recipe_search_form"):
                recipe_query = st.text_input(
                    "What would you like to cook?",
                    placeholder="e.g. cauliflower, potato, onion or paneer butter masala",
                    key="free_text_recipe_query"
                )

                query_match = st.radio(
                    "Ingredient matching",
                    ["Use all ingredients", "Use any ingredient"],
                    horizontal=True,
                    help="For comma-separated ingredients, choose whether every ingredient or at least one must appear."
                )

                run_recipe_search = st.form_submit_button("Search recipes")

            if run_recipe_search:
                query_items = parse_ingredient_input(recipe_query)

                if not query_items:
                    st.info("Enter a dish name or at least one ingredient.")

                elif len(query_items) == 1:
                    phrase_matches = search_recipes(recipe_query, database=RECIPE_DB, limit=100)

                    ingredient_matches = search_recipes_by_ingredients(
                        query_items, match_mode="any", database=RECIPE_DB, limit=100
                    )

                    combined = pd.concat([phrase_matches, ingredient_matches]).drop_duplicates("recipe_id")
                    matches = combined.head(100)

                else:
                    mode = "all" if query_match == "Use all ingredients" else "any"

                    matches = search_recipes_by_ingredients(
                        query_items, match_mode=mode, database=RECIPE_DB, limit=100
                    )

                st.markdown(f"**{len(matches)} matching recipe(s)**")

                if matches.empty:
                    st.info("No recipes found. Try a broader dish name or fewer ingredients.")

                for _, match in matches.iterrows():
                    recipe = get_recipe_details(match["recipe_id"], RECIPE_DB)

                    if not recipe:
                        continue

                    with st.expander(
                        f"{recipe['recipe_name']} · {float(recipe['kcal']):.0f} kcal/serving · "
                        f"{float(recipe['protein_g']):.1f} g protein"
                    ):
                        if "matched_ingredients" in match.index:
                            st.caption(
                                f"Matches {int(match['matched_ingredients'])} of "
                                f"{int(match['selected_ingredient_count'])} entered ingredients "
                                f"({int(match['match_percent'])}%). Matched: {match.get('matched_ingredient_names', '')}"
                            )

                        st.caption(
                            f"{recipe['meal_type']} · {recipe['diet_type']} · {recipe['cuisine']} · "
                            f"Prep {int(recipe['prep_time_min'])} min · Cook {int(recipe['cook_time_min'])} min"
                        )

                        st.caption(
                            f"Budget: {recipe.get('budget_category', 'Regular')} · "
                            f"Spice: {recipe.get('spice_level', 'Medium')} · "
                            f"Recipe yield: {int(recipe['servings'])} servings"
                        )

                        st.markdown("**Ingredients**")

                        rows = [
                            {
                                "Ingredient": item["ingredient_name"],
                                "Quantity": f"{float(item['quantity_g']):g} g",
                                "Preparation note": item.get("ingredient_state_note", "")
                            }
                            for item in recipe["ingredients"]
                        ]

                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                        st.markdown("**Cooking method**")

                        raw_steps = str(recipe["instructions"]).splitlines()

                        clean_steps = [
                            re.sub(r"^\s*\d+[.)]\s*", "", step).strip()
                            for step in raw_steps if step.strip()
                        ]

                        if len(clean_steps) <= 1:
                            clean_steps = [
                                part.strip() for part in re.split(
                                    r"(?<!\d)\.\s+(?=[A-Z])", str(recipe["instructions"])
                                ) if part.strip()
                            ]

                        for step_no, step in enumerate(clean_steps, 1):
                            st.markdown(f"{step_no}. {step.rstrip('.')}.")

                        if recipe.get("allergens"):
                            st.caption(f"Potential allergens: {recipe['allergens']}")

                        st.caption("Nutrition and cooking times are estimates. Check ingredient labels and food-safety guidance.")

        with pantry_tab:
            st.subheader("Cook With What I Have")

            st.caption(
                "Type the ingredients currently in your kitchen, separated by commas or new lines. "
                "We'll rank recipes by how many of them they use and show what you may still need."
            )

            with st.form("cook_with_pantry_form"):
                pantry_text = st.text_area(
                    "Ingredients available",
                    placeholder="potato, cauliflower, onion, tomato, paneer, rice",
                    height=90,
                    key="cook_with_pantry_text"
                )

                pantry_button = st.form_submit_button("Find recipes I can make")

            if pantry_button:
                pantry_items = parse_ingredient_input(pantry_text)

                if not pantry_items:
                    st.info("Enter at least one ingredient you have.")

                else:
                    pantry_matches = search_recipes_by_ingredients(
                        pantry_items, match_mode="any", database=RECIPE_DB, limit=100
                    )

                    st.markdown(f"**{len(pantry_matches)} possible recipe(s)**")

                    if pantry_matches.empty:
                        st.info("No matches yet. Try broader ingredient names or add common pantry staples.")

                    for _, match in pantry_matches.iterrows():
                        recipe = get_recipe_details(match["recipe_id"], RECIPE_DB)

                        if not recipe:
                            continue

                        recipe_ingredients = [item["ingredient_name"] for item in recipe["ingredients"]]

                        matched_names = [
                            item for item in pantry_items
                            if any(ingredient_matches_query(name, item) for name in recipe_ingredients)
                        ]

                        missing_names = [
                            name for name in recipe_ingredients
                            if not any(ingredient_matches_query(name, item) for item in pantry_items)
                        ]

                        with st.expander(
                            f"{recipe['recipe_name']} · {int(match['match_percent'])}% ingredient match"
                        ):
                            st.caption(
                                f"{recipe['kcal']:.0f} kcal/serving · {recipe['protein_g']:.1f} g protein · "
                                f"{recipe['cuisine']} · {recipe['diet_type']}"
                            )

                            st.markdown("**You already have (matched)**")
                            st.write(", ".join(matched_names) if matched_names else "No exact ingredient names matched.")

                            st.markdown("**You may still need**")
                            st.write(", ".join(missing_names) if missing_names else "You have all listed recipe ingredients.")

                            st.markdown("**Ingredients and quantities**")

                            st.dataframe(pd.DataFrame([
                                {
                                    "Ingredient": item["ingredient_name"],
                                    "Quantity": f"{float(item['quantity_g']):g} g"
                                }
                                for item in recipe["ingredients"]
                            ]), use_container_width=True, hide_index=True)

                            st.markdown("**Cooking method**")

                            steps = [
                                re.sub(r"^\s*\d+[.)]\s*", "", step).strip()
                                for step in str(recipe["instructions"]).splitlines() if step.strip()
                            ]

                            for step_no, step in enumerate(steps, 1):
                                st.markdown(f"{step_no}. {step.rstrip('.')}.")


    # =================================================
    # RECIPE-BASED PERSONALIZED MEAL PLANNER
    # =================================================

    st.subheader("📅 Personalized Recipe Meal Planner")

    st.caption(
        "Builds a 7-day plan from complete recipes. Nutrition is estimated per recipe serving; "
        "actual values vary with brands, ingredients and cooking methods."
    )

    if RECIPE_DB_ERROR:
        st.error(f"Recipe database could not be loaded: {RECIPE_DB_ERROR}")

    else:
        with st.expander("Customize your recipe preferences", expanded=True):

            pref_col1, pref_col2, pref_col3 = st.columns(3)

            with pref_col1:
                diet_preference = st.selectbox(
                    "Diet preference",
                    ["No preference", "Vegetarian", "Eggetarian", "Non-vegetarian", "Vegan"],
                    key="recipe_diet"
                )

                budget_preference = st.selectbox(
                    "Budget",
                    ["Any budget", "Budget-friendly", "Regular"],
                    key="recipe_budget"
                )

            with pref_col2:
                cuisine_options = ["All cuisines"] + sorted(RECIPE_DF["cuisine"].dropna().unique().tolist())

                cuisine_preference = st.selectbox(
                    "Cuisine", cuisine_options, key="recipe_cuisine"
                )

                spice_preference = st.selectbox(
                    "Spice level",
                    ["All spice levels", "Mild", "Medium", "Hot"],
                    key="recipe_spice"
                )

            with pref_col3:
                excluded_ingredients_text = st.text_area(
                    "Avoid ingredients",
                    placeholder="e.g. peanuts, prawns, mushrooms",
                    height=70,
                    key="recipe_exclusions_text",
                    help="Type any ingredients to exclude, separated by commas or new lines. This filter cannot guarantee protection from cross-contact."
                )

                excluded_ingredients = parse_ingredient_input(excluded_ingredients_text)

        meal_plan = generate_recipe_meal_plan(
            recipes=RECIPE_DF,
            target_calories=target_calories,
            meals_per_day=meals_per_day,
            days=7,
            diet_preference=diet_preference,
            cuisine=cuisine_preference,
            excluded_ingredients=excluded_ingredients,
            budget_preference=budget_preference,
            spice_preference=spice_preference,
        )

        if not meal_plan.empty:

            saved_replacements = st.session_state.get("meal_replacements", {})

            for row_index, planned_row in meal_plan.iterrows():

                replacement_id = saved_replacements.get(
                    f"{int(planned_row['Day'])}|{planned_row['Meal']}"
                )

                if replacement_id:
                    allowed_replacements = find_meal_replacements(
                        recipes=RECIPE_DF,
                        current_recipe_id=planned_row["Recipe ID"],
                        meal_type=planned_row["Meal"],
                        target_kcal=float(planned_row["Calories (kcal)"]),
                        target_protein_g=float(planned_row["Protein (g)"]),
                        diet_preference=diet_preference,
                        cuisine=cuisine_preference,
                        excluded_ingredients=excluded_ingredients,
                        budget_preference=budget_preference,
                        spice_preference=spice_preference,
                        limit=100,
                    )

                    replacement_recipe = allowed_replacements[
                        allowed_replacements["recipe_id"] == replacement_id
                    ]

                    if not replacement_recipe.empty:
                        replacement_recipe = replacement_recipe.iloc[0]

                        portion = round(
                            (float(planned_row["Calories (kcal)"]) / max(float(replacement_recipe["kcal"]), 1)) * 4
                        ) / 4

                        portion = min(2.5, max(0.5, portion))

                        meal_plan.loc[row_index, "Recipe"] = replacement_recipe["recipe_name"]
                        meal_plan.loc[row_index, "Recipe ID"] = replacement_recipe["recipe_id"]
                        meal_plan.loc[row_index, "Planned servings"] = portion
                        meal_plan.loc[row_index, "Calories (kcal)"] = round(float(replacement_recipe["kcal"]) * portion, 1)
                        meal_plan.loc[row_index, "Protein (g)"] = round(float(replacement_recipe["protein_g"]) * portion, 1)
                        meal_plan.loc[row_index, "Cuisine"] = replacement_recipe["cuisine"]
                        meal_plan.loc[row_index, "Diet"] = replacement_recipe["diet_type"]

        if meal_plan.empty:
            st.warning("No recipes match these preferences. Try changing the cuisine or ingredient filters.")

        else:
            daily_totals = meal_plan.groupby("Day", as_index=False).agg(
                **{
                    "Estimated calories (kcal)": ("Calories (kcal)", "sum"),
                    "Estimated protein (g)": ("Protein (g)", "sum")
                }
            )

            st.markdown("**Your 7-day menu**")
            st.caption("Each day is shown as a short menu. Expand a day or recipe only when you want more detail.")

            for day in range(1, 8):
                day_rows = meal_plan[meal_plan["Day"] == day]
                totals_row = daily_totals[daily_totals["Day"] == day].iloc[0]

                with st.expander(
                    f"Day {day}  ·  {totals_row['Estimated calories (kcal)']:.0f} kcal  ·  "
                    f"{totals_row['Estimated protein (g)']:.1f} g protein",
                    expanded=(day == 1)
                ):

                    for _, meal in day_rows.iterrows():

                        st.markdown(
                            f"**{meal['Meal']}:** {meal['Recipe']}  ·  "
                            f"{float(meal['Planned servings']):g} serving(s)"
                        )

                        st.caption(
                            f"{meal['Calories (kcal)']:.0f} kcal · {meal['Protein (g)']:.1f} g protein · "
                            f"{meal['Diet']} · {meal['Cuisine']}"
                        )

                        recipe = get_recipe_details(meal["Recipe ID"], RECIPE_DB)

                        if recipe:
                            with st.expander(f"View {meal['Recipe']} recipe", expanded=False):

                                st.caption(
                                    f"Prep {int(recipe['prep_time_min'])} min · "
                                    f"Cook {int(recipe['cook_time_min'])} min · "
                                    f"Base recipe yield {int(recipe['servings'])} serving(s)"
                                )

                                portion_multiplier = float(meal["Planned servings"]) / max(float(recipe["servings"]), 1)

                                st.markdown("**Ingredients for your planned portion**")

                                ingredient_rows = [
                                    {
                                        "Ingredient": item["ingredient_name"],
                                        "Quantity": f"{float(item['quantity_g']) * portion_multiplier:.1f} g",
                                        "Preparation note": item.get("ingredient_state_note", "")
                                    }
                                    for item in recipe["ingredients"]
                                ]

                                st.dataframe(pd.DataFrame(ingredient_rows), use_container_width=True, hide_index=True)

                                st.markdown("**Cooking method**")

                                raw_steps = str(recipe["instructions"]).splitlines()

                                steps = [
                                    re.sub(r"^\s*\d+[.)]\s*", "", step).strip()
                                    for step in raw_steps if step.strip()
                                ]

                                if len(steps) <= 1:
                                    steps = [
                                        part.strip() for part in re.split(
                                            r"(?<!\d)\.\s+(?=[A-Z])", str(recipe["instructions"])
                                        ) if part.strip()
                                    ]

                                for step_no, step in enumerate(steps, 1):
                                    st.markdown(f"{step_no}. {step.rstrip('.')}.")

                                st.caption("Cooking times and nutrition are estimates. Adjust water, seasoning and doneness to taste and food-safety guidance.")

                        replacement_candidates = find_meal_replacements(
                            recipes=RECIPE_DF,
                            current_recipe_id=meal["Recipe ID"],
                            meal_type=meal["Meal"],
                            target_kcal=float(meal["Calories (kcal)"]),
                            target_protein_g=float(meal["Protein (g)"]),
                            diet_preference=diet_preference,
                            cuisine=cuisine_preference,
                            excluded_ingredients=excluded_ingredients,
                            budget_preference=budget_preference,
                            spice_preference=spice_preference,
                            limit=12,
                        )

                        if not replacement_candidates.empty:

                            replacement_key = f"{int(meal['Day'])}|{meal['Meal']}"

                            option_map = {
                                f"{row['recipe_name']} · {float(row['kcal']):.0f} kcal/serving · "
                                f"{float(row['protein_g']):.1f} g protein": row["recipe_id"]
                                for _, row in replacement_candidates.iterrows()
                            }

                            selected_replacement_label = st.selectbox(
                                f"Replace {meal['Meal'].lower()} with",
                                list(option_map.keys()),
                                key=f"replacement_select_{int(meal['Day'])}_{meal['Meal']}"
                            )

                            if st.button(
                                f"Use this replacement for Day {int(meal['Day'])}",
                                key=f"replacement_button_{int(meal['Day'])}_{meal['Meal']}"
                            ):

                                replacements = st.session_state.get("meal_replacements", {}).copy()
                                replacements[replacement_key] = option_map[selected_replacement_label]
                                st.session_state["meal_replacements"] = replacements
                                st.rerun()

                        else:
                            st.caption("No suitable replacement found for this meal with the current filters.")

            with st.expander("Daily nutrition summary", expanded=False):
                st.dataframe(daily_totals, use_container_width=True, hide_index=True)

            # =================================================
            # WEEKLY GROCERY LIST
            # =================================================

            with st.expander("🛒 Weekly grocery list", expanded=False):

                grocery_rows = []

                recipe_links = RECIPE_DB["recipe_ingredients"].merge(
                    RECIPE_DB["ingredients"][["ingredient_id", "ingredient_name"]],
                    on="ingredient_id",
                    how="left"
                )

                recipe_servings = RECIPE_DF.set_index("recipe_id")["servings"].to_dict()

                for _, planned in meal_plan.iterrows():

                    rid = planned["Recipe ID"]
                    base_yield = max(float(recipe_servings.get(rid, 1)), 1.0)
                    multiplier = float(planned["Planned servings"]) / base_yield

                    selected_links = recipe_links[recipe_links["recipe_id"] == rid]

                    for _, ingredient_row in selected_links.iterrows():
                        grocery_rows.append({
                            "Ingredient": ingredient_row["ingredient_name"],
                            "Quantity (g)": float(ingredient_row["quantity_g"]) * multiplier
                        })

                if grocery_rows:

                    grocery = pd.DataFrame(grocery_rows).groupby("Ingredient", as_index=False)["Quantity (g)"].sum()
                    grocery["Quantity (g)"] = grocery["Quantity (g)"].round(0).astype(int)

                    st.caption("Combined ingredient quantities for the full seven-day plan. Pantry staples and water may already be available at home.")

                    st.dataframe(grocery, use_container_width=True, hide_index=True)

                    st.download_button(
                        "Download grocery list (CSV)",
                        data=grocery.to_csv(index=False).encode("utf-8"),
                        file_name="weekly_grocery_list.csv",
                        mime="text/csv",
                        key="weekly_grocery_download"
                    )

                else:
                    st.info("No ingredient quantities are available for this plan.")

            st.download_button(
                "Download 7-day meal plan (CSV)",
                data=meal_plan.drop(columns=["Recipe ID"]).to_csv(index=False).encode("utf-8"),
                file_name="personalized_7_day_recipe_meal_plan.csv",
                mime="text/csv",
            )

            st.info(
                "Nutrition is estimated from ingredient reference values and suggested portions. It is not a medical prescription. "
                "Check labels and ingredient quantities, especially for allergies; consult a qualified dietitian for medical nutrition needs."
            )


    # =================================================
    # HEALTH SUMMARY
    # =================================================

    st.info(f"""
    Daily Health Summary

    • BMI: {bmi}

    • Water Intake: {water} Liters

    • Protein Requirement: {protein} grams

    • Goal: {goal}

    • Estimated Daily Calorie Target: {target_calories} kcal
    """)

    # =================================================
    # DOWNLOAD BUTTONS FOR RECOMMENDATIONS
    # =================================================

    csv = foods.to_csv(index=False)

    pdf_rec_bytes = generate_pdf_report(
        goal, bmi, water, protein, bmr, tdee, foods, target_calories
    )

    col_rec1, col_rec2 = st.columns(2)

    with col_rec1:
        st.download_button(
            label="📥 Download Recommendations (CSV)",
            data=csv,
            file_name="diet_recommendations.csv",
            mime="text/csv"
        )

    with col_rec2:
        st.download_button(
            label="📄 Download Recommendations (PDF)",
            data=pdf_rec_bytes,
            file_name="diet_recommendations.pdf",
            mime="application/pdf"
        )


# =====================================================
# FOOTER
# =====================================================

st.markdown("---")         