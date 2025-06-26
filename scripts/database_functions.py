
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
  """, str(user_id))
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
        SELECT food.id, food.label, element.id, element.label, quantity
        FROM food 
        INNER JOIN possess ON food.id = possess.food_id
        INNER JOIN element ON possess.element_id = element.id
        WHERE element.label != 'Carbohydrate'; 
    """)  # To change for Carbohydrate if needed
    results = cursor.fetchall()

    print(results)
    print("hzdnzeijkfhzekfhezniu")

    # 1. Create the initial DataFrame
    df = pd.DataFrame(results, columns=['food_id', 'food_item', 'element_id', 'element', 'element_quantity'])

    # 2. Pivot to make one row per food item, columns per element
    pivot_df = df.pivot(index=['food_id', 'food_item'], columns='element', values='element_quantity').reset_index()

    # 3. Replace missing values with 0 (optional — can also leave them as NaN)
    pivot_df = pivot_df.fillna(0)

    # 4. Return the DataFrame without normalizing anything
    return pivot_df


def fetch_food(conn, food_id):
    query = """
        SELECT fim.id, fim.Label AS food_item, e.label AS nutrient, p.quantity
        FROM Food fim
        JOIN Possess p ON fim.id = p.food_id
        JOIN Element e ON p.element_id = e.id
        WHERE fim.id = %s;
    """
    df = pd.read_sql(query, conn, params=(food_id,))

    # Keep 'food_item' during pivot by separating it out
    food_label = df[['id', 'food_item']].drop_duplicates()
    df_pivoted = df.pivot(index='id', columns='nutrient', values='quantity').reset_index()

    # Merge back food name
    result = pd.merge(df_pivoted, food_label, on='id', how='left')

    # Optional: move 'food_item' to first column
    cols = ['id', 'food_item'] + [col for col in result.columns if col not in ['id', 'food_item']]
    result = result[cols]


    return result


