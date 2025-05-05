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
VALUES (4,2000);

INSERT INTO Recommendation (element_id, recommended_quantity, for_calories)
VALUES (5,0.30,'% of calories, /9');


INSERT INTO Recommendation (element_id, recommended_quantity, for_calories)
VALUES (7,0.05,'% of calories, /4');


DROP VIEW IF EXISTS ai_data.FoodLogView cascade;
CREATE VIEW ai_data.FoodLogView AS
SELECT
    NULL::DATE AS Date,
    NULL::INT AS User_ID,
    NULL::VARCHAR AS Food_Item,
    NULL::VARCHAR AS Category,
    NULL::FLOAT AS Calories,
    NULL::FLOAT AS Protein,
    NULL::FLOAT AS Carbohydrates,
    NULL::FLOAT AS Fat,
    NULL::FLOAT AS Fiber,
    NULL::FLOAT AS Sugars,
    NULL::FLOAT AS Sodium,
    NULL::FLOAT AS Cholesterol,
    NULL::VARCHAR AS Meal_Type,
    NULL::FLOAT AS Water_Intake
WHERE FALSE;
CREATE OR REPLACE FUNCTION ai_data.insert_food_log()
RETURNS TRIGGER AS $$
DECLARE
    v_food_id INT;
    v_element_id INT;
    v_element_label TEXT;
    v_element_value FLOAT;
    element_map JSON := json_build_object(
        'Calories', NEW.Calories,
        'Protein', NEW.Protein,
        'Fat', NEW.Fat,
        'Fiber', NEW.Fiber,
        'Sugars', NEW.Sugars,
        'Sodium', NEW.Sodium
    );
BEGIN
    -- Get or insert food
    SELECT id INTO v_food_id FROM ai_data.Food WHERE Label = NEW.Food_Item LIMIT 1;

    IF v_food_id IS NULL THEN
        INSERT INTO ai_data.Food (Label) VALUES (NEW.Food_Item);
        SELECT id INTO v_food_id FROM ai_data.Food WHERE Label = NEW.Food_Item ORDER BY id DESC LIMIT 1;
    END IF;

    -- Loop through elements
    FOR v_element_label, v_element_value IN
        SELECT * FROM json_each_text(element_map)
    LOOP
        -- Get or insert element
        SELECT id INTO v_element_id FROM ai_data.Element WHERE label = v_element_label LIMIT 1;

        IF v_element_id IS NULL THEN
            INSERT INTO ai_data.Element (label) VALUES (v_element_label);
            SELECT id INTO v_element_id FROM ai_data.Element WHERE label = v_element_label ORDER BY id DESC LIMIT 1;
        END IF;

        -- Insert possess if not exists
        IF NOT EXISTS (
            SELECT 1 FROM ai_data.Possess p
            WHERE p.food_id = v_food_id AND p.element_id = v_element_id
        ) THEN
            INSERT INTO ai_data.Possess (food_id, element_id, quantity)
            VALUES (v_food_id, v_element_id, v_element_value::FLOAT);
        END IF;
    END LOOP;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_insert_food_log
INSTEAD OF INSERT ON ai_data.FoodLogView
FOR EACH ROW
EXECUTE FUNCTION ai_data.insert_food_log();

--ALTER TABLE ai_data.Food ADD CONSTRAINT unique_food_label UNIQUE (Label);


COPY ai_data.FoodLogView
FROM '/docker-entrypoint-initdb.d/populate/FOOD-DATA-GROUP1.csv'
WITH (
  FORMAT csv,
  HEADER true,
  DELIMITER ','
);
