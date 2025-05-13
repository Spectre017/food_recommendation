
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

     

# An item associated with a food together with all it's nutrient value in a dictionnary
"""

class food_item:
  def __init__(self, name, id, element_dictionnary):
    self.id = id
    self.name = name
    self.element_dictionnary = element_dictionnary

"""












# REQUIREMENTS RELATED FUNCTION SECTION


# FOOD ITEM CLASS RELATED FUNCTION SECTION




# Create an item object from a database information
# def create_food_item(item):
   
# Transforms a list of database item into food item class objects
# def transform_food_item_list(cursor, limit=1000):
   










# AI FUNCTION SECTION

# 1. Weighted cosine similarity by nutrient name (unchanged)
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


# 2. Sharpened quantity-error with stronger excess penalties (unchanged)
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


# 3. Combined score re-scaled to 0–100, with bonuses & penalties (unchanged)
def coef_calculation(current_amount, item_amount, required_amount, nutrient_names):
    combine = [c + i for c, i in zip(current_amount, item_amount)]

    nutrient_weights = {
        "Calories":     3,
        "Sodium":       5,
        "Sugars":       4,
        "Saturated Fat":4,
        "Protein":      2,
        "Fiber":        2,
    }
    weights = [nutrient_weights.get(n, 1) for n in nutrient_names]

    cos_sim    = calculate_cosine_similarity(combine, required_amount, weights)
    cosine_pct = cos_sim * 100

    qty_err     = calculate_quantity_error(combine, required_amount)
    quantity_pct = (1 - qty_err) * 100

    bonus = 0
    idx_prot  = nutrient_names.index("Protein") if "Protein" in nutrient_names else None
    idx_fiber = nutrient_names.index("Fiber")  if "Fiber"  in nutrient_names else None
    if idx_prot  is not None and combine[idx_prot]  < required_amount[idx_prot]:
        bonus += 10
    if idx_fiber is not None and combine[idx_fiber] < required_amount[idx_fiber]:
        bonus += 5

    penalty = 0
    for nut, thresh, p in [("Sodium", 0.5, 15), ("Sugars", 0.5, 15), ("Saturated Fat", 0.5, 20)]:
        if nut in nutrient_names:
            idx = nutrient_names.index(nut)
            if item_amount[idx] > required_amount[idx] * thresh:
                penalty += p

    final = 0.4 * cosine_pct + 0.6 * quantity_pct + bonus - penalty
    return max(0, min(100, final))


# 4. analyse_item with safe lookups and immediate zero-out
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


# Main AI Function
def analyse_items(meal,item_list,requirements):
  item_list_complete = item_list.copy()
  item_list_complete["results"] = "None"


  for i in range(len(item_list)):
     result = analyse_item(item_list.loc[i],meal,requirements)
     item_list_complete.loc[i, "results"] = result
  return (item_list_complete)



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
main()
