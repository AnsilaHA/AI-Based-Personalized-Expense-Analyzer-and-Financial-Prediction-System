import sqlite3
import os
from config import Config


def get_db_connection():
    """Establishes a connection to the SQLite database with row factory enabled."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys support in SQLite
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initializes the database using schema.sql and seeds master categories."""
    db_is_new = not os.path.exists(Config.DATABASE_PATH)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Read and execute schema
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    cursor.executescript(schema_sql)
    conn.commit()
    
    # Seed master categories
    print("Seeding master categories...")
    # Add Income categories
    for cat in Config.MASTER_INCOME_CATEGORIES:
        cursor.execute(
            "INSERT INTO categories (name, type, is_custom, created_by) VALUES (?, 'income', 0, NULL);",
            (cat,)
        )
    
    # Add Expense categories
    for cat in Config.MASTER_EXPENSE_CATEGORIES:
        cursor.execute(
            "INSERT INTO categories (name, type, is_custom, created_by) VALUES (?, 'expense', 0, NULL);",
            (cat,)
        )
    
    conn.commit()
    conn.close()
    print("Database initialized and seeded successfully.")

# ==========================================
# USER OPERATIONS
# ==========================================

def create_user(username, email, password_hash, persona):
    """Creates a new user in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, persona) VALUES (?, ?, ?, ?);",
            (username, email, password_hash, persona)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_id(user_id):
    """Fetches user information by ID."""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?;", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_username(username):
    """Fetches user information by username."""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?;", (username,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_email(email):
    """Fetches user by email address."""
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?;", (email,)).fetchone()
    conn.close()
    return dict(user) if user else None

def update_user_budget(user_id, budget):
    """Updates the user's monthly budget limit."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET monthly_budget = ? WHERE id = ?;", (budget, user_id))
    conn.commit()
    conn.close()

# ==========================================
# CATEGORY OPERATIONS
# ==========================================

def get_all_system_categories():
    """Gets all standard pre-defined and system-wide categories."""
    conn = get_db_connection()
    categories = conn.execute("SELECT * FROM categories WHERE is_custom = 0;").fetchall()
    conn.close()
    return [dict(cat) for cat in categories]

def get_user_selected_categories(user_id):
    """Fetches all categories selected by or custom created for a user."""
    conn = get_db_connection()
    # Fetch standard categories selected by user + custom categories created by user
    query = """
        SELECT c.* FROM categories c
        INNER JOIN user_categories uc ON c.id = uc.category_id
        WHERE uc.user_id = ?
        
        UNION
        
        SELECT * FROM categories
        WHERE is_custom = 1 AND created_by = ?;
    """
    categories = conn.execute(query, (user_id, user_id)).fetchall()
    conn.close()
    return [dict(cat) for cat in categories]

def add_custom_category(user_id, name, cat_type):
    """Adds a custom expense/income category and links it automatically."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if it already exists as system or user custom
        existing = cursor.execute(
            """SELECT * FROM categories 
               WHERE LOWER(name) = LOWER(?) AND (is_custom = 0 OR created_by = ?);""",
            (name, user_id)
        ).fetchone()
        
        if existing:
            # If it already exists in categories but isn't linked to user, link it
            cat_id = existing['id']
        else:
            # Create new custom category
            cursor.execute(
                "INSERT INTO categories (name, type, is_custom, created_by) VALUES (?, ?, 1, ?);",
                (name, cat_type, user_id)
            )
            cat_id = cursor.lastrowid
            
        # Link category to user in user_categories mapping table
        cursor.execute(
            "INSERT OR IGNORE INTO user_categories (user_id, category_id) VALUES (?, ?);",
            (user_id, cat_id)
        )
        conn.commit()
        return cat_id
    except sqlite3.Error as e:
        print(f"Error adding custom category: {e}")
        return None
    finally:
        conn.close()

def save_user_categories(user_id, category_ids):
    """Saves the user's category preferences (syncs the user_categories table)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Clear existing selections (do not delete custom categories, just their links)
        cursor.execute("DELETE FROM user_categories WHERE user_id = ?;", (user_id,))
        
        # Insert selected categories
        for cat_id in category_ids:
            cursor.execute(
                "INSERT INTO user_categories (user_id, category_id) VALUES (?, ?);",
                (user_id, cat_id)
            )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error saving user categories: {e}")
        return False
    finally:
        conn.close()

# ==========================================
# TRANSACTION OPERATIONS
# ==========================================

def add_transaction(user_id, category_id, t_type, amount, date, description, frequency, is_recurring):
    """Inserts a new transaction record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO transactions 
               (user_id, category_id, type, amount, date, description, frequency, is_recurring) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
            (user_id, category_id, t_type, amount, date, description, frequency, is_recurring)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error adding transaction: {e}")
        return None
    finally:
        conn.close()

def get_user_transactions(user_id, type_filter=None, category_id=None, start_date=None, end_date=None):
    """Fetches list of user's transactions with dynamic filtering."""
    conn = get_db_connection()
    query = """
        SELECT t.*, c.name as category_name, c.type as category_type
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ?
    """
    params = [user_id]
    
    if type_filter:
        query += " AND t.type = ?"
        params.append(type_filter)
    if category_id:
        query += " AND t.category_id = ?"
        params.append(category_id)
    if start_date:
        query += " AND t.date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND t.date <= ?"
        params.append(end_date)
        
    query += " ORDER BY t.date DESC, t.id DESC;"
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_transaction_by_id(transaction_id, user_id):
    """Fetches a specific transaction to check ownership."""
    conn = get_db_connection()
    row = conn.execute(
        """SELECT t.*, c.name as category_name 
           FROM transactions t 
           JOIN categories c ON t.category_id = c.id
           WHERE t.id = ? AND t.user_id = ?;""", 
        (transaction_id, user_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def update_transaction(transaction_id, user_id, category_id, t_type, amount, date, description, frequency, is_recurring):
    """Updates an existing transaction record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """UPDATE transactions 
               SET category_id = ?, type = ?, amount = ?, date = ?, description = ?, frequency = ?, is_recurring = ?
               WHERE id = ? AND user_id = ?;""",
            (category_id, t_type, amount, date, description, frequency, is_recurring, transaction_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error updating transaction: {e}")
        return False
    finally:
        conn.close()

def delete_transaction(transaction_id, user_id):
    """Deletes a transaction record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?;", (transaction_id, user_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error deleting transaction: {e}")
        return False
    finally:
        conn.close()
