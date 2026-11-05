import pandas as pd
from datetime import datetime, timedelta


def generate_meal_plan(foods_df, goal, tdee):

    foods_df = foods_df.copy()

    foods_df = foods_df.fillna(0)

    foods_df = foods_df[
        foods_df["food"].astype(str).str.len() > 3
    ]

    if len(foods_df) == 0:
        return pd.DataFrame()

    # ==================================
    # Goal Based Pools
    # ==================================

    if goal == "Thin":

        breakfast_pool = foods_df[
            foods_df["calories"] >= 250
        ]

        lunch_pool = foods_df[
            foods_df["calories"] >= 400
        ]

        dinner_pool = foods_df[
            foods_df["calories"] >= 300
        ]

    elif goal == "Medium":

        breakfast_pool = foods_df[
            foods_df["calories"] >= 150
        ]

        lunch_pool = foods_df[
            foods_df["calories"] >= 300
        ]

        dinner_pool = foods_df[
            foods_df["calories"] >= 200
        ]

    elif goal == "Fit":

        breakfast_pool = foods_df[
            foods_df["protein"] >= 10
        ]

        lunch_pool = foods_df[
            foods_df["protein"] >= 15
        ]

        dinner_pool = foods_df[
            foods_df["protein"] >= 15
        ]

    else:

        breakfast_pool = foods_df[
            foods_df["protein"] >= 15
        ]

        lunch_pool = foods_df[
            foods_df["protein"] >= 20
        ]

        dinner_pool = foods_df[
            foods_df["protein"] >= 20
        ]

    # ==================================
    # Safety Fallback
    # ==================================

    if breakfast_pool.empty:
        breakfast_pool = foods_df

    if lunch_pool.empty:
        lunch_pool = foods_df

    if dinner_pool.empty:
        dinner_pool = foods_df

    meal_plan = []

    start_date = datetime.today()

    for day in range(84):

        breakfast = breakfast_pool.sample(
            n=1,
            replace=True
        ).iloc[0]

        lunch = lunch_pool.sample(
            n=1,
            replace=True
        ).iloc[0]

        dinner = dinner_pool.sample(
            n=1,
            replace=True
        ).iloc[0]

        total_calories = (
            breakfast["calories"]
            + lunch["calories"]
            + dinner["calories"]
        )

        total_protein = (
            breakfast["protein"]
            + lunch["protein"]
            + dinner["protein"]
        )

        meal_plan.append({

            "Date":
            (
                start_date +
                timedelta(days=day)
            ).strftime("%d-%m-%Y"),

            "Breakfast":
            breakfast["food"],

            "Lunch":
            lunch["food"],

            "Dinner":
            dinner["food"],

            "Calories":
            round(total_calories, 1),

            "Protein":
            round(total_protein, 1)
        })

    return pd.DataFrame(meal_plan)