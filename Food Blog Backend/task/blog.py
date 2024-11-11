import argparse
import sqlite3


def parse_arguments():
    parser = argparse.ArgumentParser(description="Search for recipes based on ingredients and meals.")
    parser.add_argument("db_path", help="Path to the SQLite database")
    parser.add_argument("--ingredients", help='List of ingredients separated by commas, e.g., "milk,sugar,tea"')
    parser.add_argument("--meals", help='List of meals separated by commas, e.g., "dinner,supper"')
    return parser.parse_args()


def get_recipes(conn, ingredients=None, meals=None):
    cursor = conn.cursor()
    # Base query to select recipe names with the required conditions
    base_query = """
        SELECT  r.recipe_id, r.recipe_name
        FROM recipes r
        JOIN quantity q ON q.recipe_id = r.recipe_id
        JOIN ingredients i ON i.ingredient_id = q.ingredient_id
        JOIN serve s ON r.recipe_id = s.recipe_id
        JOIN meals m ON s.meal_id = m.meal_id
    """
    # Conditions to apply based on ingredients and meals
    conditions = []
    params = []

    if meals:
        meal_list = meals.split(',')
        meal_placeholder = ",".join(["?" for _ in meal_list])
        conditions.append("WHERE")
        conditions.append(f"m.meal_name IN ({meal_placeholder})")
        params.extend(meal_list)

    if ingredients:
        ingredient_list = ingredients.split(',')
        ingredients_placeholders = " AND ".join(
                [f"SUM(CASE WHEN i.ingredient_name = ? THEN 1 ELSE 0 END) > 0" for _ in ingredient_list])
        conditions.append("GROUP BY r.recipe_id")
        conditions.append("HAVING")
        conditions.append(f"{ingredients_placeholders}")
        params.extend(ingredient_list)

    # Group by recipe name and having all ingredients matched
    final_query = base_query
    if conditions:
        final_query += "\n".join(conditions)

    cursor.execute(final_query, params)
    results = cursor.fetchall()

    return [row[1] for row in results]


def insert_data(conn):
    # Dictionary to populate tables
    data = {
        "meals": ("breakfast", "brunch", "lunch", "supper"),
        "ingredients": ("milk", "cacao", "strawberry", "blueberry", "blackberry", "sugar"),
        "measures": ("ml", "g", "l", "cup", "tbsp", "tsp", "dsp", "")
    }
    cursor = conn.cursor()
    for meal in data["meals"]:
        cursor.execute("INSERT OR IGNORE INTO meals (meal_name) VALUES (?);", (meal,))
    for ingredient in data["ingredients"]:
        cursor.execute("INSERT OR IGNORE INTO ingredients (ingredient_name) VALUES (?);", (ingredient,))
    for measure in data["measures"]:
        cursor.execute("INSERT OR IGNORE INTO measures (measure_name) VALUES (?);", (measure,))
    conn.commit()
    print("Database and tables created, and data populated successfully.")


def create_tables(conn):
    with conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                recipe_id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_name TEXT NOT NULL,
                recipe_description TEXT
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meals (
                meal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                meal_name TEXT NOT NULL,
                CONSTRAINT unique_meal_name UNIQUE (meal_name)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS serve (
                serve_id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                meal_id INTEGER NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id),
                FOREIGN KEY (meal_id) REFERENCES meals(meal_id)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingredients (
                ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingredient_name TEXT NOT NULL,
                CONSTRAINT unique_ingredient_name UNIQUE (ingredient_name)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS measures (
                measure_id INTEGER PRIMARY KEY AUTOINCREMENT,
                measure_name TEXT,
                CONSTRAINT unique_measure_name UNIQUE (measure_name)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quantity (
                quantity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                measure_id INTEGER NOT NULL,
                ingredient_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                recipe_id INTEGER NOT NULL,
                FOREIGN KEY (measure_id) REFERENCES measures(measure_id),
                FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id),
                FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id)
            );
        """)


def insert_recipe(conn, name, description):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO recipes (recipe_name, recipe_description) 
        VALUES (?, ?);
    """, (name, description))
    return cursor.lastrowid


def get_meals(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT meal_id, meal_name FROM meals;")
    return cursor.fetchall()


def link_recipe_to_meals(conn, recipe_id, meal_ids):
    with conn:
        for meal_id in meal_ids:
            conn.execute("""
                INSERT INTO serve (recipe_id, meal_id) 
                VALUES (?, ?);
            """, (recipe_id, meal_id))


def get_measures(conn, search):
    cursor = conn.cursor()
    cursor.execute("SELECT measure_id, measure_name FROM measures WHERE measure_name == ?", (search,))
    return cursor.fetchone()


def insert_measures(conn, measure_input):
    cursor = conn.cursor()
    cursor.execute("""
            INSERT INTO measures (measure_name) 
            VALUES (?);
        """, (measure_input,))
    return cursor.lastrowid


def get_ingredients(conn, search):
    cursor = conn.cursor()
    cursor.execute("SELECT ingredient_id, ingredient_name FROM ingredients WHERE ingredient_name == ?",
                   (search,))
    return cursor.fetchone()


def insert_ingredients(conn, ingredient_input):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ingredients (ingredient_name) 
        VALUES (?);
    """, (ingredient_input,))
    return cursor.lastrowid


def insert_quantity(conn, recipe_id, quantity, measure_id, ingredient_id):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO quantity (quantity, measure_id, ingredient_id, recipe_id) 
        VALUES (?, ?, ?, ?);
    """, (quantity, measure_id, ingredient_id, recipe_id))


def parse_entry(entry):
    parts = entry.split()
    if len(parts) < 2:
        raise ValueError("Invalid entry length")
    quantity = int(parts[0])
    measure_input = parts[1] if len(parts) > 2 else ""
    ingredient_input = parts[1] if len(parts) == 2 else ' '.join(parts[2:])
    return quantity, measure_input, ingredient_input


def select_measure(conn, measure_input):
    measures = get_measures(conn, measure_input)
    if measures is None:
        return None
    return measures[0]


def select_ingredient(conn, ingredient_input):
    ingredients = get_ingredients(conn, ingredient_input)
    if ingredients is None:
        return None
    return ingredients[0]


def interactive_mode(conn):
    while True:
        recipe_name = input("Recipe name: ")
        if recipe_name == "":
            break
        recipe_description = input("Recipe description: ")
        recipe_id = insert_recipe(conn, recipe_name, recipe_description)
        meals = get_meals(conn)
        for meal in meals:
            print(f"{meal[0]}) {meal[1]}", end="  ")
        print()
        meal_times_input = input("Enter proposed meals separated by a space: ")
        meal_ids = list(map(int, meal_times_input.split()))
        link_recipe_to_meals(conn, recipe_id, meal_ids)
        while True:
            entry = input("Input quantity of ingredient <press enter to stop>: ")
            if entry == "":
                break
            try:
                quantity, measure_input, ingredient_input = parse_entry(entry)
            except ValueError:
                print("Invalid format! Use the format: quantity measure ingredient")
                continue
            measure_id = select_measure(conn, measure_input)
            if measure_id is None:
                measure_id = insert_measures(conn, measure_input)
            ingredient_id = select_ingredient(conn, ingredient_input)
            if ingredient_id is None:
                ingredient_id = insert_ingredients(conn, ingredient_input)
            insert_quantity(conn, recipe_id, quantity, measure_id, ingredient_id)
            conn.commit()


def main():
    args = parse_arguments()
    conn = sqlite3.connect(args.db_path)
    create_tables(conn)
    insert_data(conn)
    print("Pass the empty recipe name to exit.")
    try:
        if args.ingredients and args.meals:
            recipes = get_recipes(conn, args.ingredients, args.meals)
            if recipes:
                print(f"Recipes selected for you: {', '.join(recipes)}")
            else:
                print("There are no such recipes in the database.")
        else:
            interactive_mode(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
