
import os
from dotenv import load_dotenv, dotenv_values 
import psycopg2
from psycopg2 import OperationalError
import time
import pandas as pd
import re
from math import sqrt

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


# CLASS SECTION

# A list of food item in the meal
class meal:
  def __init__(self, id, item_list_columns):
    self.id = id
    self.food_item_list = pd.DataFrame(columns=item_list_columns)

  # Removes an item from the meal's item list
  def remove_item(self,item_id):
     self.food_item_list = self.food_item_list[self.food_item_list.food_id != item_id]

  # Add an item to the meal's item list
  def add_item(self,item):
     self.food_item_list.loc[len(self.food_item_list)] = item

  # Calculate a meal's total intake
  def calculate_total_intake(self):
     return self.food_item_list.iloc[:, 2:].sum()
     

# An item associated with a food together with all it's nutrient value in a dictionnary
"""

class food_item:
  def __init__(self, name, id, element_dictionnary):
    self.id = id
    self.name = name
    self.element_dictionnary = element_dictionnary

"""


# The required/advised amount for each nutrients in a dictionnary and user infos important for calculations
class requirements:
  def __init__(self, element_dictionnary):
    self.element_dictionnary = element_dictionnary 


# DATABASE FUNCTION SECTION

# Creates a connexion with the database
def create_bdd_connexion(retries=5, delay=5):
      # loading variables from .env file
    load_dotenv() 

    database=os.getenv("DATABASE_NAME")
    user=os.getenv("DB_USERNAME") # WARNING: CANNOT BE USERNAME AS IT CONFLICTS WITH DEFAULT ENV VARIABLE
    password=os.getenv("PASSWORD")
    host=os.getenv("HOST")
    port=os.getenv("PORT")

    for i in range(retries):
        try:
            connection = psycopg2.connect(
                database=database,
                user=user,
                password=password,
                host=host,
                port=port
            )
            print("Connected to DB!")
            return connection
        except OperationalError as e:
            print(f"DB connection failed, retrying in {delay} seconds...")
            time.sleep(delay)

    raise Exception("Could not connect to the database after several retries.")

# Creates a transaction with the database
def create_bdd_cursor(connection):
    cursor = connection.cursor()
    cursor.execute("SET SCHEMA 'ai_data';")
    cursor.execute("SET search_path TO ai_data;")

    return cursor







# FUNCTION TO GET USER DATA

#Gets all user-related info important for requirements(Sex, Age, Calories, Height, Weight) before being used to create them
def get_user_info(user_id,cursor):
  cursor.execute("""
        SELECT Age, Sex, Weight, Height, Desired_Intake
        FROM Users 
        WHERE id=%s;
  """, user_id)
  results = cursor.fetchall()
  results = results[0]
  user_info = {}
  user_info['Age'] = results[0]
  user_info['Sex'] = results[1]
  user_info['Weight'] = results[2]
  user_info['Height'] = results[3]
  user_info['Desired_Intake'] = results[4]

  return user_info











# REQUIREMENTS RELATED FUNCTION SECTION

# Treat the strings
def requirement_treatment(quantity,treatment_string,user_data):
  print(treatment_string)

  if treatment_string=="per kilo":
    quantity = quantity*user_data['Weight']
  if treatment_string=="% of calories":
    quantity = quantity*user_data['Desired_Intake']
  if treatment_string=="% of calories, /9":
    quantity = (quantity*user_data['Desired_Intake'])/9
  if treatment_string=="% of calories, /4":
    quantity = (quantity*user_data['Desired_Intake'])/4

  if re.match(r'^\d+-\d+$', treatment_string):  # Pattern like "10-20"
      start, end = map(int, treatment_string.split('-'))
      if user_data["Age"]>start and user_data["Age"]<end :
        return quantity
      else:
        return None
  elif re.match(r'^\d+\+$', treatment_string):  # Pattern like "15+"
      num = int(treatment_string[:-1])
      if user_data["Age"]>=num:
        return quantity
      else:
        return None
    
  elif re.match(r'^\d+-$', treatment_string):  # Pattern like "30-"
      num = int(treatment_string[:-1])
      if user_data["Age"]<=num:
        return quantity
      else:
        return None
      
  return quantity


#Gets all requirements/advised amounts for each nutrient in the database
def get_requirement_list_from_bdd(cursor):
  cursor.execute("""
        SELECT label, recommended_quantity, age_range, for_weight, for_height, for_calories
        FROM Element 
        INNER JOIN Recommendation ON Recommendation.element_id = Element.id;
  """)
  results = cursor.fetchall()
  return results

#Returns a filled requirements object
def create_requirements(cursor,user_data):
  requirement_list = get_requirement_list_from_bdd(cursor)
  requirements_dictionnary = {}
  requirements_dictionnary["Calories"]=user_data["Desired_Intake"]

  for item in requirement_list:
     quantity = item[1]
     for index in range(2,len(item)):
        if item[index]!=None:
           quantity = requirement_treatment(item[1],item[index],user_data)
     if quantity != None:
      requirements_dictionnary[item[0]]=quantity
  return requirements(requirements_dictionnary)
 


# FOOD ITEM CLASS RELATED FUNCTION SECTION

# Gets a certain amount of items from the database together with their nutrients and creates the food item list
def get_item_list_from_bdd(cursor, limit=1000):
  cursor.execute("""
        SELECT food.id,food.label,element.id, element.label, quantity
        FROM food 
        INNER JOIN possess ON food.id = possess.food_id
        INNER JOIN element ON possess.element_id = element.id
        WHERE element.label!='Carbohydrate'; 
  """) #To change for Carbohydrate
  results = cursor.fetchall()


  # 1. Create the initial DataFrame
  df = pd.DataFrame(results, columns=['food_id', 'food_item', 'element_id', 'element', 'element_quantity'])

  # 2. Pivot to make one row per food item, columns per element
  pivot_df = df.pivot(index=['food_id', 'food_item'], columns='element', values='element_quantity').reset_index()

  pivot_df = pivot_df.fillna(0)

  nutrient_columns = [col for col in pivot_df.columns if col not in ['food_id', 'food_item', 'Calories']]
  nutrients_to_normalize = [col for col in nutrient_columns if col not in ['Sodium', 'Sugars']]
  pivot_df[nutrients_to_normalize] = pivot_df[nutrients_to_normalize].div(pivot_df['Calories'], axis=0) * 100


  return pivot_df




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
  connection = create_bdd_connexion()
  cursor = create_bdd_cursor(connection)
  user_data = get_user_info("1", cursor)

  requirement = create_requirements(cursor,user_data)
  item_list = get_item_list_from_bdd(cursor)
  #print(item_list)
  new_meal = meal(1, item_list.columns)


  #item_list.loc[len(item_list)] = [552,"Super Food", 1000, 33.33, 12.5, 27.3, 1, 12.5]
  #item_list.loc[len(item_list)] = [553,"Nutritional Heaven", 10, 10.33, 12.5, 27.3, 1, 6.5]

  new_meal.add_item(item_list.loc[417])
  final_list = analyse_items(new_meal,item_list,requirement)
  final_list["results"] = pd.to_numeric(final_list["results"], errors="coerce")

  print(final_list.sort_values(by="results").to_string())

  print(item_list.loc[417])
  print(requirement.element_dictionnary)
main()
