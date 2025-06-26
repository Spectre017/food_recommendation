drop schema if exists ai_data cascade;
create schema ai_data;
set schema 'ai_data';

CREATE TABLE Users (
    id SERIAL PRIMARY KEY,
    Name VARCHAR(100),
    Age INT,
    Sex VARCHAR,
    Weight FLOAT,
    Height FLOAT,
    Desired_Intake FLOAT
);

-- Table for Food
CREATE TABLE Food (
    id SERIAL PRIMARY KEY,
    Label VARCHAR(100)
);

-- Table for Meal
CREATE TABLE FoodInMeal (
    food_id INT,
    id_meal INT,
    id_quantity INT,
    PRIMARY KEY (food_id,id_meal,id_quantity)
);

-- Table for Meal
CREATE TABLE Meal (
    id SERIAL PRIMARY KEY,
    id_user INT,
    FOREIGN KEY (id_user) REFERENCES Users(id)
);

-- Table to represent User's liked Food
CREATE TABLE UserLikesFood (
    user_id INT,
    food_id INT,
    PRIMARY KEY (user_id, food_id),
    FOREIGN KEY (user_id) REFERENCES Users(id),
    FOREIGN KEY (food_id) REFERENCES Food(id)
);

-- Table for Elements (e.g., nutrients)
CREATE TABLE Element (
    id SERIAL PRIMARY KEY,
    label VARCHAR(100)
);

-- Table for Food possessing Elements with quantity
CREATE TABLE Possess (
    food_id INT,
    element_id INT,
    quantity FLOAT,
    PRIMARY KEY (food_id, element_id),
    FOREIGN KEY (food_id) REFERENCES Food(id),
    FOREIGN KEY (element_id) REFERENCES Element(id)
);

-- Table for Recommendation based on Element and user factors
CREATE TABLE Recommendation (
    id SERIAL PRIMARY KEY,
    element_id INT,
    recommended_quantity FLOAT,
    age_range VARCHAR,
    for_weight VARCHAR,
    for_height VARCHAR,
    for_calories VARCHAR,
    FOREIGN KEY (element_id) REFERENCES Element(id)
);





INSERT INTO Element (label)
VALUES ('Protein'),
('Fiber'),
('Carbohydrate'),
('Sodium'),
('Fat'),
('Calories'),
('Sugars');



INSERT INTO Users (Name, Age, Sex, Weight, Height, Desired_Intake)
VALUES ('Frank', '22', 'Male', 65, 175, 2000);





INSERT INTO Recommendation (element_id, recommended_quantity, for_weight)
VALUES (1,0.84,'per kilo');

INSERT INTO Recommendation (element_id, recommended_quantity, age_range)
VALUES (2,25,'10+');
INSERT INTO Recommendation (element_id, recommended_quantity, age_range)
VALUES (2,21,'7-9');
INSERT INTO Recommendation (element_id, recommended_quantity, age_range)
VALUES (2,15,'6-');

INSERT INTO Recommendation (element_id, recommended_quantity)
VALUES (4,2);

INSERT INTO Recommendation (element_id, recommended_quantity, for_calories)
VALUES (5,0.30,'% of calories, /9');


INSERT INTO Recommendation (element_id, recommended_quantity, for_calories)
VALUES (7,0.05,'% of calories, /4');



DROP TABLE IF EXISTS ai_data.NutritionStaging;
CREATE TABLE ai_data.NutritionStaging (
    id SERIAL,  
    unnamed_0 INT,      
    food TEXT,
    caloric_value FLOAT,
    fat FLOAT,
    saturated_fats FLOAT,
    monounsaturated_fats FLOAT,
    polyunsaturated_fats FLOAT,
    carbohydrates FLOAT,
    sugars FLOAT,
    protein FLOAT,
    dietary_fiber FLOAT,
    cholesterol FLOAT,
    sodium FLOAT,
    water FLOAT,
    vitamin_a FLOAT,
    vitamin_b1 FLOAT,
    vitamin_b11 FLOAT,
    vitamin_b12 FLOAT,
    vitamin_b2 FLOAT,
    vitamin_b3 FLOAT,
    vitamin_b5 FLOAT,
    vitamin_b6 FLOAT,
    vitamin_c FLOAT,
    vitamin_d FLOAT,
    vitamin_e FLOAT,
    vitamin_k FLOAT,
    calcium FLOAT,
    copper FLOAT,
    iron FLOAT,
    magnesium FLOAT,
    manganese FLOAT,
    phosphorus FLOAT,
    potassium FLOAT,
    selenium FLOAT,
    zinc FLOAT,
    nutrition_density FLOAT
);



COPY ai_data.NutritionStaging
FROM '/docker-entrypoint-initdb.d/populate/FOOD-DATA-GROUP1.csv'
WITH (
  FORMAT csv,
  HEADER true
);

DO $$
DECLARE
    v_food_id INT;
    v_element_id INT;
    rec RECORD;  
BEGIN
    FOR rec IN
        SELECT
            ns.food,
            ns.caloric_value AS "Calories",
            ns.fat AS "Fat",
            ns.carbohydrates AS "Carbohydrate",
            ns.sugars AS "Sugars",
            ns.protein AS "Protein",
            ns.dietary_fiber AS "Fiber",
            ns.sodium AS "Sodium"
        FROM ai_data.NutritionStaging ns
    LOOP
        -- Insert food if not exists
        SELECT id INTO v_food_id FROM ai_data.Food WHERE Label = rec.food;
        IF v_food_id IS NULL THEN
            INSERT INTO ai_data.Food (Label) VALUES (rec.food);
            SELECT id INTO v_food_id FROM ai_data.Food WHERE Label = rec.food;
        END IF;

        -- Insert relevant elements
        IF rec."Protein" IS NOT NULL THEN
            SELECT id INTO v_element_id FROM ai_data.Element WHERE label = 'Protein';
            INSERT INTO ai_data.Possess (food_id, element_id, quantity)
            VALUES (v_food_id, v_element_id, rec."Protein")
            ON CONFLICT DO NOTHING;
        END IF;

        IF rec."Fiber" IS NOT NULL THEN
            SELECT id INTO v_element_id FROM ai_data.Element WHERE label = 'Fiber';
            INSERT INTO ai_data.Possess (food_id, element_id, quantity)
            VALUES (v_food_id, v_element_id, rec."Fiber")
            ON CONFLICT DO NOTHING;
        END IF;

        IF rec."Carbohydrate" IS NOT NULL THEN
            SELECT id INTO v_element_id FROM ai_data.Element WHERE label = 'Carbohydrate';
            INSERT INTO ai_data.Possess (food_id, element_id, quantity)
            VALUES (v_food_id, v_element_id, rec."Carbohydrate")
            ON CONFLICT DO NOTHING;
        END IF;

        IF rec."Sodium" IS NOT NULL THEN
            SELECT id INTO v_element_id FROM ai_data.Element WHERE label = 'Sodium';
            INSERT INTO ai_data.Possess (food_id, element_id, quantity)
            VALUES (v_food_id, v_element_id, rec."Sodium")
            ON CONFLICT DO NOTHING;
        END IF;

        IF rec."Fat" IS NOT NULL THEN
            SELECT id INTO v_element_id FROM ai_data.Element WHERE label = 'Fat';
            INSERT INTO ai_data.Possess (food_id, element_id, quantity)
            VALUES (v_food_id, v_element_id, rec."Fat")
            ON CONFLICT DO NOTHING;
        END IF;

        IF rec."Calories" IS NOT NULL THEN
            SELECT id INTO v_element_id FROM ai_data.Element WHERE label = 'Calories';
            INSERT INTO ai_data.Possess (food_id, element_id, quantity)
            VALUES (v_food_id, v_element_id, rec."Calories")
            ON CONFLICT DO NOTHING;
        END IF;

        IF rec."Sugars" IS NOT NULL THEN
            SELECT id INTO v_element_id FROM ai_data.Element WHERE label = 'Sugars';
            INSERT INTO ai_data.Possess (food_id, element_id, quantity)
            VALUES (v_food_id, v_element_id, rec."Sugars")
            ON CONFLICT DO NOTHING;
        END IF;
    END LOOP;
END $$;
