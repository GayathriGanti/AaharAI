# AaharMind AI — Personalised Nutrition & Meal Planning

AaharMind AI is a Streamlit-based personalised nutrition companion that estimates daily nutrition metrics, recommends foods, explores recipes and builds a practical 7-day meal plan.

## What AaharMind AI includes

- Existing Streamlit dashboard and food recommendation workflow
- BMI, BMR and TDEE estimates, with a fitness goal selected by the user
- USDA-derived food nutrition dataset and supporting cleaned datasets
- 100 starter recipes, ingredient reference data, recipe-to-ingredient links and recipe tags
- Recipe filtering by vegetarian/vegan preference, cuisine and excluded ingredients
- 7-day recipe meal planner with estimated portions and nutrition totals
- CSV meal-plan export and PDF report support
- Optional Gemini-powered diet assistant
- Recipe database validation and meal-planner smoke tests

## 1. Requirements

- Windows 10/11, macOS or Linux
- Python 3.10 or newer (Python 3.11 is a good choice)
- Internet connection for the first installation of Python packages

## 2. Quick start on Windows

1. Extract the ZIP file completely.
2. Open the extracted `AI-Personalized-Diet-Recommendation-System-main` folder.
3. Double-click `run_windows.bat`.
4. On the first run, the script creates a virtual environment and installs the packages. It then starts the Streamlit app.
5. A local browser tab should open. If it does not, copy the Local URL shown in the terminal (usually `http://localhost:8501`) into your browser.

If Windows does not recognize `py`, install Python from https://www.python.org/downloads/ and enable **Add Python to PATH** during installation, then run the batch file again.

## 3. Manual start (all operating systems)

Open a terminal in the project root, the folder containing `requirements.txt`.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run python/app.py
```

If PowerShell blocks activation, use Command Prompt and run:

```bat
.venv\Scripts\activate.bat
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run python/app.py
```

## 4. Optional Gemini API key

The main dashboard and recipe planner can run without a Gemini key. The chatbot needs a Google Gemini API key.

For a temporary session, set an environment variable before starting Streamlit:

**Windows PowerShell**

```powershell
$env:GEMINI_API_KEY="YOUR_API_KEY"
streamlit run python/app.py
```

**macOS / Linux**

```bash
export GEMINI_API_KEY="YOUR_API_KEY"
streamlit run python/app.py
```

Do not publish your API key or commit it to GitHub. You can obtain/manage a key through Google AI Studio: https://aistudio.google.com/app/apikey

## 5. Validate the recipe database

From the project root, with the virtual environment activated:

```bash
python python/validate_recipe_database.py
```

Expected result: 100 recipes, 63 ingredients and 710 recipe-ingredient links.

## 6. Test the recipe meal planner

```bash
python -m pip install pandas
cd python
python test_recipe_meal_planner.py
cd ..
```

The test checks 7-day plan generation, portion ranges, vegan filtering, cuisine filtering and excluded ingredients.

## Project structure

```text
AI-Personalized-Diet-Recommendation-System-main/
├── Cleaned_data/              # Cleaned datasets and saved model
├── datasets/
│   ├── raw/                   # Original source datasets
│   └── recipes/               # 100 recipes and normalized ingredient tables
├── outputs/                   # Existing project output images
├── python/
│   ├── app.py                 # Streamlit application entry point
│   ├── recipe_engine.py       # Recipe database loading and filtering
│   ├── recipe_meal_planner.py # 7-day recipe plan generation
│   ├── meal_plan_generator.py # Existing food-based planner module
│   ├── gemini_chatbot.py      # Optional Gemini assistant
│   ├── pdf_generator.py       # PDF report generation
│   └── ...                    # Notebooks, preprocessing and validation scripts
├── requirements.txt
├── run_windows.bat
└── README.md
```

## Important nutrition note

BMI, BMR, TDEE, water and protein values are estimates, not diagnoses or medical prescriptions. Recipe nutrition is calculated from the ingredient reference data and listed quantities; real values vary by ingredient brand, preparation and serving size. The 100 recipes are a starter dataset and have not all been independently reviewed by a registered dietitian. Ingredient exclusions are a filtering aid, not a guarantee against allergen cross-contact. Consult a qualified dietitian for medical nutrition needs.


### Expanded recipe planner update
- Includes vegetarian, vegan, eggetarian and non-vegetarian recipe choices.
- Food search checks USDA ingredient records plus recipe names and recipe ingredients.
- The 7-day plan is displayed as compact, expandable daily menus.
- Newly added recipe nutrition is calculated from approximate ingredient reference values and should be verified against labels or a trusted food-composition database.

## Latest interface updates

- The 7-day recipe meal plan is the primary personalized recommendation. The separate generic "Recommended Foods" table and its ingredient-only macro chart have been removed from the main interface.
- Food search still searches the USDA food dataset, recipe names, and recipe ingredients. Matching recipes are now expandable directly in the search results, with ingredient quantities, preparation/cooking time, serving yield, and numbered cooking steps.
- Each meal in the 7-day plan has its own expandable recipe card. Ingredient quantities are scaled to the planned portion, while the base recipe yield remains visible.
- Nutrition values are estimates derived from ingredient reference data and should not be treated as medical advice.
\n\n## Version 5 updates\n- Recipe-focused search: dish names, ingredients and cuisines; raw USDA rows are not shown in search.\n- Expanded to 300 uniquely named recipe entries across Indian regional and international cuisines.\n- Added budget category, spice level and potential allergen metadata.\n- Weekly planner supports budget and spice preferences.\n- Nutrition is estimated from ingredient reference data. New starter entries should be reviewed and cooking-tested before public or clinical use. Allergy notes do not guarantee absence of cross-contact.\n- Added a weekly grocery list aggregated from the generated meal plan and basic ingredient substitution suggestions in recipe details.\n\n\n## Version 6 improvements\n- Pantry-based multi-select recipe search: choose multiple available ingredients and match all or any selected items.\n- Search results open complete recipe details, including ingredients, quantities, prep/cook times and cooking steps.\n- Expanded recipe-development drafts now use dish-category-specific cooking methods and ingredient links for named main ingredients where available. Nutrition recalculated from the linked ingredient reference data for those drafts.\n- Recipe instructions are displayed as clean numbered steps, without duplicate numbering.\n- Note: newly generated recipe-development entries remain drafts requiring human review and kitchen testing; ingredient quantities and nutrition are estimates.\n

## Version 7 updates

### Flexible recipe search
- Search by dish name, cuisine, or ingredients typed freely by the user.
- Enter multiple ingredients separated by commas, semicolons, or new lines.
- For multi-ingredient search, choose whether a recipe must contain all entered ingredients or at least one.
- Common aliases are recognised (for example, aloo/potato, gobi/cauliflower, bhindi/okra, dahi/curd, and rajma/kidney beans).

### Cook With What I Have
- Enter the ingredients currently available at home.
- Recipes are ranked by how many entered ingredients they use.
- Each result explains which entered ingredients match and which recipe ingredients may still be needed.

### Free-text exclusions
- Avoid ingredients is now a free-text field rather than a fixed dropdown.
- Enter several ingredients separated by commas, semicolons, or new lines.
- Exclusions are applied to the generated meal plan and meal replacements. This is a recipe filter, not a guarantee against allergen cross-contact.

### Meal replacement
- Each planned meal offers alternatives from the recipe database.
- Alternatives preserve the meal slot and current diet, cuisine, budget, spice and exclusion preferences.
- Suggestions are ranked by similarity to the current meal's estimated calories and protein.
- Selecting a replacement updates the plan, nutrition totals and grocery list.

### Running
From the extracted project folder:
```powershell
python -m pip install -r requirements.txt
streamlit run python/app.py
```

Nutrition values remain estimates derived from the recipe ingredient database. Recipe entries and cooking methods should be reviewed and kitchen-tested before production or clinical use.


## Deploy on Streamlit Community Cloud

1. Push the tested branch to GitHub.
2. Sign in at https://share.streamlit.io/ using the GitHub account that can access this repository.
3. Select **Create app** and choose this repository, the deployment branch, and the entrypoint file `python/app.py`.
4. Keep the dependency file as the root-level `requirements.txt`.
5. For the optional Gemini assistant, add `GEMINI_API_KEY` in the app's **Advanced settings → Secrets**. Do not commit API keys or `.streamlit/secrets.toml`.
6. Select Python 3.12 initially (the Community Cloud default documented at the time of writing), deploy, and inspect the app logs if startup fails.

## Contributing as a team

- Keep `main` as the stable, tested branch.
- Create one feature branch per contributor or task, for example `feature/recipe-cards` or `feature/profile-flow`.
- Commit and push changes to that feature branch, then open a pull request into `main`.
- Pull the latest `main` before starting new work. Avoid having multiple contributors edit `python/app.py` at the same time.
- Never commit `.venv/`, `.env`, API keys, or `.streamlit/secrets.toml`.

## Project identity

**Product name:** AaharMind AI  
**Tagline:** Personalised nutrition, practical meals.  
**GitHub repository slug:** `aaharmind-ai`
