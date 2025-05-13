
import os
from dotenv import load_dotenv, dotenv_values 
import psycopg2
from psycopg2 import OperationalError
import time
import pandas as pd
import re
from math import sqrt
import database_functions as db

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

class requirements:
  def __init__(self, element_dictionnary):
    self.element_dictionnary = element_dictionnary 


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



#Returns a filled requirements object
def create_requirements(cursor,user_data):
  requirement_list = db.get_requirement_list_from_bdd(cursor)
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
 
