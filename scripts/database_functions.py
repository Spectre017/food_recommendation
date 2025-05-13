
import os
from dotenv import load_dotenv, dotenv_values 
import psycopg2
from psycopg2 import OperationalError
import time
import pandas as pd
import re
from math import sqrt

# Creates a connection with the database
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


#Gets all requirements/advised amounts for each nutrient in the database
def get_requirement_list_from_bdd(cursor):
  cursor.execute("""
        SELECT label, recommended_quantity, age_range, for_weight, for_height, for_calories
        FROM Element 
        INNER JOIN Recommendation ON Recommendation.element_id = Element.id;
  """)
  results = cursor.fetchall()
  return results

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

