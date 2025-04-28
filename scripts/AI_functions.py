
import os
from dotenv import load_dotenv, dotenv_values 
import psycopg2
from psycopg2 import OperationalError
import time
import pandas as pd
import re


# CLASS SECTION

# A list of food item in the meal
class meal:
  def __init__(self, id):
    self.id = id
    self.food_item_list = []

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
  if treatment_string=="per kilo":
    quantity = quantity*user_data['Weight']
  if treatment_string=="% of calories":
    quantity = quantity*user_data['Desired_Intake']

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
        INNER JOIN element ON possess.element_id = element.id;
  """)
  results = cursor.fetchall()


  # 1. Create the initial DataFrame
  df = pd.DataFrame(results, columns=['food_id', 'food_item', 'element_id', 'element', 'element_quantity'])

  # 2. Pivot to make one row per food item, columns per element
  pivot_df = df.pivot(index=['food_id', 'food_item'], columns='element', values='element_quantity').reset_index()

  return pivot_df




# Create an item object from a database information
# def create_food_item(item):
   
# Transforms a list of database item into food item class objects
# def transform_food_item_list(cursor, limit=1000):
   






# MEAL CLASS RELATED FUNCTION SECTION

# Create a meal object
def create_meal()

# Removes an item from the meal's item list
def remove_item_from_meal(meal,item_id)

# Add an item to the meal's item list
def add_item_to_meal(meal,item)

# Calculate a meal's total intake
def calculate_total_intake(meal):


"""


# AI FUNCTION SECTION

# Gives a score of how much the item goes towards getting close to the wanted amount
def coef_calculation(current_amount,item_amount,required_amount)

# Analyses an item's nutritional value using AI compared to the meal and other items, returns a score
def analyse_items(total_current_intake,item_list,user,requirements)

# Main AI Function
def analyse_items(meal,item,item_list,user,requirements)




"""


    
connection = create_bdd_connexion()
cursor = create_bdd_cursor(connection)
user_data = get_user_info("1", cursor)

requirement = create_requirements(cursor,user_data)
print(get_item_list_from_bdd(cursor))