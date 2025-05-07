
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

def calculate_cosine_similarity(list1, list2, weight_dict={
    0: 3,  # Give more weight to Calories
    1: 2,  # More weight to Sodium
    2: 2,  # More weight to Sugars
    # etc.
}
):
    product = 0
    tot1 = 0
    tot2 = 0

    for i in range(len(list1)):
        weight = weight_dict.get(i, 1)  # Default weight is 1, but you can add a dict for key nutrients
        product += (list1[i] * list2[i]) * weight

    for y in range(len(list2)):
        weight = weight_dict.get(y, 1)
        tot1 += (list1[y]**2) * weight
        tot2 += (list2[y]**2) * weight

    return product / (sqrt(tot1) * sqrt(tot2))



def calculate_quantity_error(actual, required, over_penalty=3.0, hard_limit=1.5):
    total_required = sum(required)
    if total_required == 0:
        return 0.0  # Avoid divide-by-zero

    total_error = 0.0

    for a, r in zip(actual, required):
        if a <= r:
            # Under target: normal penalty
            total_error += abs(a - r)
        else:
            # Over target: penalize heavily if above a "hard limit"
            if a > r * 1.25:  # 125% of recommended
                total_error += (a - r) * 5.0  # Stronger penalty for severe excess
            else:
                total_error += abs(a - r) * over_penalty  # Normal penalty for slight overnutrition

    # Normalize error based on required sums
    return min(total_error / total_required, 1.0)  # Clamp the error to [0, 1] scale



# Gives a score of how much the item goes towards getting close to the wanted amount
def coef_calculation(current_amount, item_amount, required_amount):
    combine_amount = [x + y for x, y in zip(current_amount, item_amount)]

    # Cosine similarity to the goal AFTER adding item
    cosine_score = calculate_cosine_similarity(combine_amount, required_amount)

    # Normalize the error for each nutrient (penalizing excess sodium, sugar)
    normalized_errors = []
    for actual, required in zip(combine_amount, required_amount):
        if actual > required * 1.5:  # If above 1.5x the required amount (overconsumption penalty)
            normalized_errors.append((actual - required) * 2)  # Stronger penalty
        else:
            normalized_errors.append(abs(actual - required))  # Normal error for undernutrition or slight over
    normalized_error = sum(normalized_errors) / len(required_amount)

    # Quantity match score: 1 - normalized error (don't penalize too heavily)
    quantity_score = max(0, 1 - normalized_error)  

    # Final combined score (harsher on quantity, i.e., overnutrition)
    final_score = cosine_score * 0.5 + quantity_score * 0.8  # Heavy emphasis on quantity match

    match_percentage = final_score * 100  # Convert to percentage for easier interpretation
    return match_percentage






# Analyses an item's nutritional value using AI compared to the meal and other items, returns a score
def analyse_item(item,meal,requirements):
    
    
    item_values = item.drop(['food_id', 'food_item'])
    meal_values = meal.calculate_total_intake()

    sorted_keys = sorted(requirements.element_dictionnary.keys())
    for key in sorted_keys:
        if key not in item_values:
            item_values[key] = 0.0
        if key not in meal_values:
            meal_values[key] = 0.0
    item_values = item_values[sorted_keys].values.tolist()
    meal_values = meal_values[sorted_keys].values.tolist()

    for key in ["Calories", "Saturated Fat", "Sodium"]:
        if key in item and key in meal_values:
            if meal_values[key] + item[key] > requirements.element_dictionnary[key] * 1.25:
                return 0  # Too much


    requirement_values = [requirements.element_dictionnary[key] for key in sorted_keys]


    coef = coef_calculation(meal_values, item_values, requirement_values)

    if coef<0:
       return "Negative score"
    else :
       return coef


# Main AI Function
def analyse_items(meal,item_list,requirements):
  item_list_complete = item_list.copy()
  item_list_complete["results"] = "None"


  for i in range(len(item_list)):
     print(item_list_complete.loc[i, "food_item"])
     result = analyse_item(item_list.loc[i],meal,requirements)
     item_list_complete.loc[i, "results"] = result
  return (item_list_complete)



def main():
  connection = create_bdd_connexion()
  cursor = create_bdd_cursor(connection)
  user_data = get_user_info("1", cursor)

  requirement = create_requirements(cursor,user_data)
  item_list = get_item_list_from_bdd(cursor)
  print(item_list)
  new_meal = meal(1, item_list.columns)


  #item_list.loc[len(item_list)] = [552,"Super Food", 1000, 33.33, 12.5, 27.3, 1, 12.5]
  #item_list.loc[len(item_list)] = [553,"Nutritional Heaven", 10, 10.33, 12.5, 27.3, 1, 6.5]

  new_meal.add_item(item_list.loc[229])
  final_list = analyse_items(new_meal,item_list,requirement)
  final_list["results"] = pd.to_numeric(final_list["results"], errors="coerce")

  print(final_list.sort_values(by="results"))
  
  print(requirement.element_dictionnary)
main()
