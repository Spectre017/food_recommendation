import os
from dotenv import load_dotenv, dotenv_values 
import psycopg2
from psycopg2 import OperationalError
import time
import pandas as pd
import re
from math import sqrt
import meal as me
import database_functions as db
import requirements as req

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)




# AI FUNCTION SECTION

# Calculate the similarity between two items' vectors and their nutrients to keep balance
def calculate_cosine_similarity(list1, list2, weights):
    product = 0.0
    tot1 = 0.0
    tot2 = 0.0

    for v1, v2, w in zip(list1, list2, weights):
        product += (v1 * v2) * w
        tot1    += (v1**2) * w
        tot2    += (v2**2) * w

    if tot1 == 0 or tot2 == 0:
        return 0.0
    return product / (sqrt(tot1) * sqrt(tot2))


# Calculate the difference between an item's nutrient and it's requirements
def calculate_quantity_error(actual, required, slight_penalty=3.0, severe_penalty=5.0):
    total_required = sum(required)
    if total_required == 0:
        return 0.0

    total_error = 0.0
    for a, r in zip(actual, required):
        if a <= r:
            total_error += abs(a - r)
        else:
            if a <= r * 1.25:
                total_error += abs(a - r) * slight_penalty
            else:
                total_error += abs(a - r) * severe_penalty

    return min(total_error / total_required, 1.0)

def calculate_asymmetric_error(combined, required):
    penalty = 0
    for c, r in zip(combined, required):
        if r == 0:
            continue
        ratio = c / r
        if ratio <= 1:
            # underfed: linear penalty
            penalty += (1 - ratio)
        else:
            # overfed: steeper penalty (quadratic or exponential)
            penalty += (ratio - 1) ** 2
    return penalty / len(required)  # normalize to [0, ~]


# Calculate the score of an item in relation to current meal
def coef_calculation(current_amount, item_amount, required_amount, nutrient_names):
    combine = [c + i for c, i in zip(current_amount, item_amount)]

    # Nutrient importance
    nutrient_weights = {
        "Calories":     3,
        "Sodium":       5,
        "Sugars":       4,
        "Saturated Fat":4,
        "Protein":      2,
        "Fiber":        2,
    }

    # Dynamic need-based weighting
    weights = []
    for i, name in enumerate(nutrient_names):
        base_weight = nutrient_weights.get(name, 1)
        required = required_amount[i]
        current = current_amount[i]
        if required == 0:
            relative_need = 0
        else:
            relative_need = max(0, 1 - current / required)
        weights.append(base_weight * (0.5 + 0.5 * relative_need))

    # Cosine similarity and quantity error
    cos_sim = calculate_cosine_similarity(combine, required_amount, weights)
    cosine_pct = cos_sim * 100

    asym_err = calculate_asymmetric_error(combine, required_amount)
    quantity_pct = max(0, (1 - asym_err)) * 100

    # Contribution to remaining gaps
    contribution_score = 0
    for i in range(len(nutrient_names)):
        req = required_amount[i]
        cur = current_amount[i]
        add = item_amount[i]
        if req <= 0:
            continue
        gap = max(0, req - cur)
        contrib = min(gap, add) / req
        weight = nutrient_weights.get(nutrient_names[i], 1)
        contribution_score += contrib * weight
    contribution_score *= 15  # Boost this significantly

    # Explicit calorie targeting
    cal_bonus = 0
    cal_penalty = 0
    if "Calories" in nutrient_names:
        idx_cal = nutrient_names.index("Calories")
        cur_cal = current_amount[idx_cal]
        item_cal = item_amount[idx_cal]
        req_cal = required_amount[idx_cal]
        new_total = cur_cal + item_cal

        if req_cal > 0:
            gap = req_cal - cur_cal
            cal_contrib = min(gap, item_cal) / req_cal
            cal_bonus += 25 * cal_contrib  # Strong bonus for closing calorie gap

            # Penalize only severe overshoot
            if new_total > req_cal * 1.15:
                over = (new_total / req_cal) - 1.15
                cal_penalty += 25 * over ** 2  # Smooth quadratic

    # Dangerous overage penalty
    danger_penalty = 0
    for nut, thresh, penalty_strength in [("Sodium", 0.5, 20), ("Sugars", 0.5, 20), ("Saturated Fat", 0.5, 25)]:
        if nut in nutrient_names:
            idx = nutrient_names.index(nut)
            required = required_amount[idx]
            combined = combine[idx]
            if required > 0 and combined > required * 1.1:
                over = (combined / required) - 1.1
                danger_penalty += penalty_strength * (over ** 2)

    # Final score
    final = (
        0.3 * cosine_pct +
        0.4 * quantity_pct +
        contribution_score +
        cal_bonus -
        cal_penalty -
        danger_penalty
    )

    return max(0, min(100, final))



# Analyse an item to know it's nutritional value
def analyse_item(item, meal, requirements):
    # build raw lookup dicts
    keys     = sorted(requirements.element_dictionnary.keys())
    meal_vals = meal.calculate_total_intake()
    item_raw  = {k: float(item.get(k, 0)) for k in keys}
    meal_raw  = {k: float(meal_vals.get(k, 0)) for k in keys}
    req_raw   = requirements.element_dictionnary  # dict

    # immediate reject if any critical nutrient exceeds 125%
    for nut in ("Calories", "Saturated Fat", "Sodium"):
        if (item_raw.get(nut, 0) + meal_raw.get(nut, 0)) > req_raw.get(nut, float("inf")) * 1.25:
            return 0

    # build vectors for scoring
    item_vec  = [item_raw[k] for k in keys]
    meal_vec  = [meal_raw[k] for k in keys]
    req_vec   = [req_raw.get(k, 0) for k in keys]

    # compute and return the final score
    return coef_calculation(meal_vec, item_vec, req_vec, keys)


# Analyses a list of items
def analyse_items(meal, item_list, requirements):
    item_list_complete = item_list.copy()
    item_list_complete["results"] = "None"

    for i in range(len(item_list)):
        result = analyse_item(item_list.loc[i], meal, requirements)
        item_list_complete.loc[i, "results"] = result

    # Sort by the 'results' column
    item_list_complete = item_list_complete.sort_values(by="results", ascending=False)

    return item_list_complete


def main():
  connection = db.create_bdd_connexion()
  cursor = db.create_bdd_cursor(connection)
  user_data = db.get_user_info("1", cursor)

  requirement = req.create_requirements(cursor,user_data)
  item_list = db.get_item_list_from_bdd(cursor)
  #print(item_list)
  new_meal = me.meal(1, item_list.columns)


  #item_list.loc[len(item_list)] = [552,"Super Food", 1000, 33.33, 12.5, 27.3, 1, 12.5]
  #item_list.loc[len(item_list)] = [553,"Nutritional Heaven", 10, 10.33, 12.5, 27.3, 1, 6.5]
  new_meal.add_item(item_list.loc[417])
  final_list = analyse_items(new_meal,item_list,requirement)
  final_list["results"] = pd.to_numeric(final_list["results"], errors="coerce")

  print(final_list.sort_values(by="results").to_string())

  print(item_list.loc[417])
  print(requirement.element_dictionnary)




  me.save_meal_to_db(new_meal, connection)
  new_meal = me.fetch_meal_from_db(1,connection, item_list.columns)
  me.save_meal_to_db(new_meal, connection)
  print(new_meal.food_item_list)

  food = db.fetch_food(connection, 1)
  print(food)
main()
