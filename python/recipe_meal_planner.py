from recipe_engine import ingredient_matches_query
"""Recipe-level meal planning helpers, independent of Streamlit."""
import hashlib
import random
import pandas as pd

def _meal_slots(meals_per_day):
    templates={1:["Lunch"],2:["Breakfast","Dinner"],3:["Breakfast","Lunch","Dinner"],4:["Breakfast","Lunch","Snack","Dinner"],5:["Breakfast","Snack","Lunch","Snack","Dinner"]}
    if meals_per_day<=5: return templates[max(1,meals_per_day)]
    slots=templates[5].copy()
    while len(slots)<meals_per_day: slots.insert(-1,"Snack")
    return slots

def generate_recipe_meal_plan(recipes,target_calories,meals_per_day=3,days=7,diet_preference="No preference",cuisine="All cuisines",excluded_ingredients=None,budget_preference="Any budget",spice_preference="All spice levels"):
    required={"recipe_id","recipe_name","meal_type","diet_type","cuisine","kcal","protein_g"}
    missing=required-set(recipes.columns)
    if missing: raise ValueError(f"Recipe data is missing columns: {', '.join(sorted(missing))}")
    pool=recipes.copy()
    for c in ("meal_type","diet_type","cuisine","recipe_id","recipe_name"): pool[c]=pool[c].fillna("").astype(str)
    diet= str(diet_preference).casefold()
    if diet=="vegan": pool=pool[pool.diet_type.str.casefold().eq("vegan")]
    elif diet=="vegetarian": pool=pool[pool.diet_type.str.casefold().isin(["vegan","vegetarian"])]
    elif diet=="eggetarian": pool=pool[pool.diet_type.str.casefold().isin(["vegan","vegetarian","eggetarian"])]
    elif diet=="non-vegetarian": pool=pool[pool.diet_type.str.casefold().isin(["vegan","vegetarian","eggetarian","non-vegetarian"])]
    if cuisine!="All cuisines": pool=pool[pool.cuisine.str.casefold().eq(str(cuisine).casefold())]
    if budget_preference != "Any budget" and "budget_category" in pool.columns:
        pool=pool[pool.budget_category.fillna("").str.casefold().eq(str(budget_preference).casefold())]
    if spice_preference != "All spice levels" and "spice_level" in pool.columns:
        pool=pool[pool.spice_level.fillna("").str.casefold().eq(str(spice_preference).casefold())]
    excluded=[str(x).strip().casefold() for x in (excluded_ingredients or []) if str(x).strip()]
    if excluded and "ingredient_names" in pool.columns:
        def contains_excluded(value):
            names=[part.strip() for part in str(value).split(" | ")]
            return any(ingredient_matches_query(name, term) for name in names for term in excluded)
        pool=pool[~pool.ingredient_names.fillna("").apply(contains_excluded)]
    pool["kcal"]=pd.to_numeric(pool.kcal,errors="coerce"); pool["protein_g"]=pd.to_numeric(pool.protein_g,errors="coerce")
    pool=pool.dropna(subset=["kcal","protein_g"]); pool=pool[(pool.kcal>0)&(pool.protein_g>=0)]
    if pool.empty:return pd.DataFrame()
    meals_per_day=max(1,int(meals_per_day)); days=max(1,int(days)); slots=_meal_slots(meals_per_day)
    weights={"Breakfast":.25,"Lunch":.30,"Dinner":.30,"Snack":.15}; raw=[weights.get(s,1/len(slots)) for s in slots]; total=sum(raw) or 1
    seed=int(hashlib.sha256(f"{target_calories}|{meals_per_day}|{days}|{diet_preference}|{cuisine}|{sorted(excluded)}".encode()).hexdigest()[:8],16); rng=random.Random(seed)
    rows=[]; used_week=set(); recent_slot={s:[] for s in set(slots)}
    for day in range(1,days+1):
        used_today=set()
        for slot,w in zip(slots,raw):
            candidates=pool[pool.meal_type.str.casefold().eq(slot.casefold())]
            if candidates.empty: candidates=pool
            # When a user explicitly chooses non-vegetarian, make sure lunch/dinner
            # actually include non-vegetarian dishes where the database has options.
            if diet == "non-vegetarian" and slot in ("Lunch", "Dinner"):
                nonveg_candidates=candidates[candidates.diet_type.str.casefold().eq("non-vegetarian")]
                if not nonveg_candidates.empty: candidates=nonveg_candidates
            fresh=candidates[~candidates.recipe_id.isin(used_today | set(recent_slot.get(slot,[])[-2:]))]
            if fresh.empty: fresh=candidates[~candidates.recipe_id.isin(used_today)]
            if fresh.empty: fresh=candidates
            # Sample from a wider pool with a small penalty for recipes already used this week.
            ranked=fresh.copy(); ranked["_score"]=(ranked.kcal-float(target_calories)*w/total).abs()/max(float(target_calories)*w/total,1)
            ranked["_score"] += ranked.recipe_id.isin(used_week).astype(float)*0.22
            best=ranked.sort_values(["_score","protein_g"],ascending=[True,False]).head(min(12,len(ranked)))
            chosen=best.iloc[rng.randrange(len(best))]; rid=chosen.recipe_id; used_today.add(rid); used_week.add(rid); recent_slot.setdefault(slot,[]).append(rid)
            portion=round((float(target_calories)*w/total)/max(float(chosen.kcal),1)*4)/4; portion=min(2.5,max(.5,portion))
            rows.append({"Day":day,"Meal":slot,"Recipe":chosen.recipe_name,"Recipe ID":rid,"Planned servings":portion,"Calories (kcal)":round(float(chosen.kcal)*portion,1),"Protein (g)":round(float(chosen.protein_g)*portion,1),"Cuisine":chosen.cuisine,"Diet":chosen.diet_type})
    return pd.DataFrame(rows)


def find_meal_replacements(recipes, current_recipe_id, meal_type, target_kcal,
                           target_protein_g, diet_preference="No preference",
                           cuisine="All cuisines", excluded_ingredients=None,
                           budget_preference="Any budget", spice_preference="All spice levels",
                           limit=12):
    """Find alternatives for one planned meal, prioritising similar nutrition."""
    pool = recipes.copy()
    for col in ("meal_type", "diet_type", "cuisine", "recipe_id"):
        pool[col] = pool[col].fillna("").astype(str)
    pool = pool[pool["meal_type"].str.casefold() == str(meal_type).casefold()]
    diet = str(diet_preference).casefold()
    if diet == "vegan":
        pool = pool[pool.diet_type.str.casefold().eq("vegan")]
    elif diet == "vegetarian":
        pool = pool[pool.diet_type.str.casefold().isin(["vegan", "vegetarian"])]
    elif diet == "eggetarian":
        pool = pool[pool.diet_type.str.casefold().isin(["vegan", "vegetarian", "eggetarian"])]
    elif diet == "non-vegetarian":
        pool = pool[pool.diet_type.str.casefold().isin(["vegan", "vegetarian", "eggetarian", "non-vegetarian"])]
    if cuisine != "All cuisines":
        pool = pool[pool.cuisine.str.casefold() == str(cuisine).casefold()]
    if budget_preference != "Any budget" and "budget_category" in pool:
        pool = pool[pool.budget_category.fillna("").str.casefold() == str(budget_preference).casefold()]
    if spice_preference != "All spice levels" and "spice_level" in pool:
        pool = pool[pool.spice_level.fillna("").str.casefold() == str(spice_preference).casefold()]
    excluded = [str(x).strip().casefold() for x in (excluded_ingredients or []) if str(x).strip()]
    if excluded and "ingredient_names" in pool.columns:
        def contains_excluded(value):
            names = [part.strip() for part in str(value).split(" | ")]
            return any(ingredient_matches_query(name, term) for name in names for term in excluded)
        pool = pool[~pool.ingredient_names.fillna("").apply(contains_excluded)]
    pool = pool[pool.recipe_id != str(current_recipe_id)]
    if pool.empty:
        return pool
    pool["kcal"] = pd.to_numeric(pool["kcal"], errors="coerce")
    pool["protein_g"] = pd.to_numeric(pool["protein_g"], errors="coerce")
    pool = pool.dropna(subset=["kcal", "protein_g"])
    pool["_nutrition_distance"] = (
        (pool["kcal"] - float(target_kcal)).abs() / max(float(target_kcal), 100)
        + (pool["protein_g"] - float(target_protein_g)).abs() / max(float(target_protein_g), 5)
    )
    return pool.sort_values(["_nutrition_distance", "protein_g"], ascending=[True, False]).head(limit).drop(columns="_nutrition_distance")
