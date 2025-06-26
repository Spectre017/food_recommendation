from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import AI_functions as ai
import database_functions as db
import meal
import requirements
from fastapi.responses import JSONResponse


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

connexion = db.create_bdd_connexion()
cursor = db.create_bdd_cursor(connexion)

item_list = db.get_item_list_from_bdd(cursor)
item_list_columns = item_list.columns

@app.get("/get_requirements/")
async def get_requirements():
    print(db.get_requirement_list_from_bdd(cursor))
    return db.get_requirement_list_from_bdd(cursor)
    
@app.get("/get_processed_requirements/")
async def get_processed_requirements(user_id: int = 1):
    user = db.get_user_info(user_id, cursor)
    req_obj = requirements.create_requirements(cursor, user)
    return req_obj.element_dictionnary


@app.get("/get_items/")
async def get_items(limit: int = 1000):
    df = db.get_item_list_from_bdd(cursor, limit=limit)
    return df.to_dict(orient="records") 



@app.get("/get_user_info/")
async def get_user_info(user_id: int):
    return db.get_user_info(user_id, cursor)


@app.get("/create_meal/")
async def create_meal():
    new_meal = meal.meal(1,item_list_columns)
    return meal.save_meal_to_db(new_meal, connexion)


from fastapi.responses import JSONResponse
@app.get("/add_item_to_meal/")
async def add_item_to_meal(meal_id: int, item_id: int):
    try:
        update_meal = meal.fetch_meal_from_db(meal_id, connexion, item_list_columns)
        item_df = db.fetch_food(connexion, item_id)

        if item_df is None or item_df.empty:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found or empty")

        item_df = item_df.drop(columns=["Carbohydrate"], errors='ignore')
        item_df = item_df.rename(columns={"id": "food_id"})
        item_df = item_df[update_meal.food_item_list.columns]
        item_series = item_df.iloc[0]

        update_meal.add_item(item_series)  # Adds one more of this item

        meal.update_meal_in_db(update_meal, connexion, meal_id)

        return {"status": "success", "meal_id": meal_id, "item_id": item_id}

    except Exception as e:
        print("Error in add_item_to_meal:", str(e))
        return JSONResponse(status_code=500, content={"error": str(e)})



@app.get("/remove_item_from_meal/")
async def remove_item_from_meal(meal_id: int, item_id: int):
    update_meal = meal.fetch_meal_from_db(meal_id,connexion,item_list_columns)
    update_meal.remove_item(item_id)
    meal.update_meal_in_db(update_meal,connexion,meal_id)

@app.get("/analyse_items/")
async def analyse_items(meal_id: int):
    fetched_meal = meal.fetch_meal_from_db(meal_id, connexion, item_list_columns)
    req = requirements.create_requirements(cursor, db.get_user_info(1, cursor))
    result_df = ai.analyse_items(fetched_meal, item_list, req)
    return result_df.to_dict(orient="records") 



@app.get("/analyse_item/")
async def analyse_item(
    item_id: int,
    meal_id: int,
):
    fetched_meal = meal.fetch_meal_from_db(meal_id,connexion,item_list_columns)
    fetched_item = db.fetch_food(connexion,item_id)
    req = requirements.create_requirements(cursor,db.get_user_info(1,cursor))
    return ai.analyse_items(fetched_meal, fetched_item, req)
