
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


# A list of food items with their nutrients in the meal
class meal:
  def __init__(self, id, item_list_columns):
    self.id = id
    self.food_item_list = pd.DataFrame(columns=item_list_columns)

  # Removes an item from the meal's item list
  def remove_item(self,item_id):
     self.food_item_list = self.food_item_list[self.food_item_list.food_id != item_id]

  # Add an item to the meal's item list
  def add_item(self,item):
     print("a", item)
     self.food_item_list.loc[len(self.food_item_list)] = item

  # Calculate a meal's total intake
  def calculate_total_intake(self):
     return self.food_item_list.iloc[:, 2:].sum()

def fetch_meal_from_db(meal_id, conn, item_list_columns):
    query = """
        SELECT fim.food_id, fim.id_meal, fim.id_quantity, e.label AS nutrient, p.quantity
        FROM FoodInMeal fim
        JOIN Possess p ON fim.food_id = p.food_id
        JOIN Element e ON p.element_id = e.id
        WHERE fim.id_meal = %s;
    """
    df = pd.read_sql(query, conn, params=(meal_id,))

    # Pivot nutrients into columns (one row per food item)
    df_pivot = df.pivot_table(index=['food_id', 'id_meal', 'id_quantity'],
                               columns='nutrient',
                               values='quantity',
                               fill_value=0).reset_index()

    # Ensure columns are ordered correctly to match item_list_columns
    for col in item_list_columns:
        if col not in df_pivot.columns:
            df_pivot[col] = 0  # Add missing columns with zero

    df_pivot = df_pivot[item_list_columns]  # Reorder columns

    meal_save = meal(meal_id, item_list_columns)
    meal_save.food_item_list = df_pivot

    return meal_save


def save_meal_to_db(meal, conn):
    with conn.cursor() as cur:
        # Insert a new meal and get the generated id
        cur.execute("INSERT INTO Meal DEFAULT VALUES RETURNING id;")
        meal_id = cur.fetchone()[0]

        # Count how many times each food_id appears
        food_counts = meal.food_item_list['food_id'].value_counts()

        for food_id, count in food_counts.items():
            for i in range(1, count + 1):
                cur.execute("""
                    INSERT INTO FoodInMeal (food_id, id_meal, id_quantity)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING;
                """, (int(food_id), meal_id, int(i)))

    conn.commit()
    return meal_id

def update_meal_in_db(meal, conn, meal_id):
    with conn.cursor() as cur:
        # Remove existing food items for the given meal
        cur.execute("DELETE FROM FoodInMeal WHERE id_meal = %s;", (meal_id,))

        # Count how many times each food_id appears in the new list
        food_counts = meal.food_item_list['food_id'].value_counts()

        for food_id, count in food_counts.items():
            for i in range(1, count + 1):
                cur.execute("""
                    INSERT INTO FoodInMeal (food_id, id_meal, id_quantity)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING;
                """, (int(food_id), meal_id, int(i)))

    conn.commit()
