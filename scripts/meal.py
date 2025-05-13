
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
     self.food_item_list.loc[len(self.food_item_list)] = item

  # Calculate a meal's total intake
  def calculate_total_intake(self):
     return self.food_item_list.iloc[:, 2:].sum()