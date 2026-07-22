-- SQLite database schema

-- Drop tables if they exist to allow clean resets
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS user_categories;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;

-- 1. Users Table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    persona TEXT NOT NULL CHECK(persona IN ('Student', 'Employee', 'Doctor', 'Business Owner', 'Housewife', 'Middle-Class Family', 'Lower-Income User', 'Other')),
    monthly_budget REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Categories Table
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
    is_custom INTEGER DEFAULT 0 CHECK(is_custom IN (0, 1)),
    created_by INTEGER,
    FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. User Selected Categories Table (personalized categories selection)
CREATE TABLE user_categories (
    user_id INTEGER,
    category_id INTEGER,
    PRIMARY KEY (user_id, category_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE
);

-- 4. Transactions Table (Income, Expenses, Debts, Credits)
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('income', 'expense', 'debt', 'credit')),
    amount REAL NOT NULL CHECK(amount > 0),
    date DATE NOT NULL,
    description TEXT,
    frequency TEXT NOT NULL CHECK(frequency IN ('daily', 'weekly', 'bi-weekly', 'monthly', 'quarterly', 'half-yearly', 'yearly', 'one-time')),
    is_recurring INTEGER DEFAULT 0 CHECK(is_recurring IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE RESTRICT
);

-- Indexes for performance optimization
CREATE INDEX idx_transactions_user_date ON transactions(user_id, date);
CREATE INDEX idx_transactions_user_type ON transactions(user_id, type);
CREATE INDEX idx_user_categories_user ON user_categories(user_id);
