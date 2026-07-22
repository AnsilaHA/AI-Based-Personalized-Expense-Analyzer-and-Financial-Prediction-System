# AI-Based Personalized Expense Analyzer and Financial Prediction System

An advanced, research-oriented, and highly personalized full-stack web application designed for academic submission (suitable for MCA final year project). Built using **Python FastAPI**, **SQLite**, **Pandas**, **NumPy**, **Scikit-learn**, **Chart.js**, and **Bootstrap 5**.

---

## 1. Project Overview & Objectives
The goal of this system is to act as a personalized financial behavioral analyzer and predictive manager for diverse demographic classes (students, doctors, employees, business owners, housewives, and low-income groups). Users are empowered to track daily transaction streams (incomes, expenses, debts, credits) with various recurrence frequencies, select tracking categories relevant to their lifestyle persona, review dynamic Chart.js dashboards, and receive machine learning-based future spending forecasts alongside statistical insights.

### Core Objectives:
*   **Persona-based Customization**: Dynamic UI that adapts inputs and dashboards based on user class (Student, Doctor, Housewife, etc.).
*   **Multi-Frequency CRUD Ledger**: Log transactions with daily, weekly, monthly, quarterly, or yearly recurrences.
*   **Pandas-Powered Financial Warnings**: Automatically checks for month-over-month category spending spikes, high discretionary spending ratios, and budget limits.
*   **Scikit-Learn Predictive Modeling**: Uses Linear Regression to forecast future monthly, quarterly, and yearly spending.
*   **Premium Interactive Interface**: Responsive dashboard featuring dynamic charts, dark-mode toggle, and clean glassmorphism styling.

---

## 2. System Architecture & Folder Structure

### High-Level Architecture Block:
```
               ┌──────────────────────────────┐
               │    Client Web Browser        │
               │ (Bootstrap 5, Chart.js, JS)  │
               └──────────────┬───────────────┘
                              │ HTTP Requests / JSON Data
                              ▼
               ┌──────────────────────────────┐
               │   FastAPI Backend Controller │ (main.py, config.py)
               │ (Jinja2 Templates, Sessions) │
               └──────────────┬───────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ SQLite DB Driver │ │   Pandas/NumPy   │ │   Scikit-Learn   │
│  (database.py)   │ │ Analyzer Engine  │ │ Predictor Engine │
│                  │ │  (analyzer.py)   │ │  (predictor.py)  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

### Complete Folder Layout:
```
Personal_expense_analyzer/
├── main.py                 # FastAPI routing, session middlewares, and template rendering
├── config.py               # Settings (secret key, preloaded category persona recommendations)
├── database.py             # Raw SQL SQLite helper executions & transactional CRUD mapping
├── analyzer.py             # Financial warning logic, savings rate, MoM spikes (Pandas & NumPy)
├── predictor.py            # ML spending & savings projections (Scikit-learn LinearRegression)
├── schema.sql              # Database structure with constraint checks and performance indexes
├── requirements.txt        # Python package dependencies
├── README.md               # Extensive project documentation & installation guidelines
│
├── templates/              # HTML layout and forms (Jinja2)
│   ├── base.html           # Main shell frame with collapsible sidebar & dark-mode switch
│   ├── login.html          # Secure login form
│   ├── register.html       # Signup form with persona selector dropdown
│   ├── onboarding.html     # Dynamic category checklist configured on first-time login
│   ├── dashboard.html      # Metrics cards, AI suggestions, and dynamic Chart.js canvases
│   ├── transactions.html   # CRUD ledger list containing edit/delete Bootstrap modals
│   ├── reports.html        # Aggregate tabs (Monthly, Half-Yearly, Yearly) & CSV downloads
│   └── settings.html       # Configurations (Budget targets, custom categories, checked tags)
│
└── static/
    ├── css/
    │   └── style.css       # Premium CSS stylesheet (glassmorphism cards, custom gradients)
    └── js/
        ├── main.js         // General script (sidebar collapsing, edit modals prep, check tags)
        └── dashboard.js    // Chart.js initialization drawing timeline, doughnut, and forecasts
```

---

## 3. Database Schema

The SQLite schema utilizes index creation and explicit check constraints to ensure relational data integrity:

### Schema Visual ERD representation:
```
 ┌──────────────┐             ┌──────────────┐
 │    USERS     │1          * │ DYNAMIC CATS │
 ├──────────────┤ ──────────> ├──────────────┤
 │ id (PK)      │             │ id (PK)      │
 │ username     │             │ name, type   │
 │ email        │             │ is_custom    │
 │ password_hash│             │ created_by(FK)
 │ persona      │             └──────┬───────┘
 │ budget       │                    │ 1
 └──────┬───────┘                    │
        │ 1                          │ *
        │                            ▼
        │ *                   ┌──────────────┐
        └───────────────────> │ TRANSACTIONS │
                              ├──────────────┤
                              │ id (PK)      │
                              │ user_id (FK) │
                              │ cat_id (FK)  │
                              │ type, amount │
                              │ date, freq   │
                              │ is_recurring │
                              └──────────────┘
```

---

## 4. Key Raw SQL Queries

The application executes the following core SQL queries in `database.py`:

*   **Initialize custom user category mappings**:
    ```sql
    INSERT OR IGNORE INTO user_categories (user_id, category_id) VALUES (?, ?);
    ```
*   **Fetch transaction history with filters**:
    ```sql
    SELECT t.*, c.name as category_name, c.type as category_type
    FROM transactions t
    JOIN categories c ON t.category_id = c.id
    WHERE t.user_id = ? AND t.type = ? AND t.category_id = ?
    ORDER BY t.date DESC, t.id DESC;
    ```
*   **Fetch user-active categories (Selected system list + Custom additions)**:
    ```sql
    SELECT c.* FROM categories c
    INNER JOIN user_categories uc ON c.id = uc.category_id
    WHERE uc.user_id = ?
    UNION
    SELECT * FROM categories
    WHERE is_custom = 1 AND created_by = ?;
    ```
*   **Add customized category dynamically**:
    ```sql
    INSERT INTO categories (name, type, is_custom, created_by) VALUES (?, ?, 1, ?);
    ```
*   **Modify existing ledger transaction**:
    ```sql
    UPDATE transactions 
    SET category_id = ?, type = ?, amount = ?, date = ?, description = ?, frequency = ?, is_recurring = ?
    WHERE id = ? AND user_id = ?;
    ```

---

## 5. Machine Learning & Data Analysis Methodology

### A. Scikit-learn Linear Regression Projections
In `predictor.py`, the system groups daily expenditures:
1.  Creates index representation `X` (days elapsed since first transaction) and target `y` (daily total amount spent).
2.  Fits a Scikit-learn `LinearRegression` model.
3.  Forecasts future timelines:
    *   **Next Month**: Predicts days $t+1$ to $t+30$, and sums predicted values.
    *   **Next Quarter**: Predicts days $t+1$ to $t+90$, and sums predicted values.
    *   **Next Year**: Predicts days $t+1$ to $t+365$, and sums predicted values.
4.  **Persona Fallback Blending**: If a user is new (having $<5$ transactions), regression can overfit or crash. The system blends a persona statistical baseline (e.g. Student averages ₹9,500 expenses, Doctor averages ₹110,000) with any actual logs to serve smart default forecasts immediately.

### B. Pandas Data Auditing
In `analyzer.py`, the backend runs analytical jobs on user data:
*   **MoM category spikes**: Group by Year-Month and Category, compares category sums of current month $M$ against previous month $M-1$. Alerts are triggered if expenditure grew by $>20\%$.
*   **Savings Rate indicator**: Computes `(Income - Expense) / Income * 100`, firing warning badges if savings rate falls below 10%.
*   **Discretionary ratio analysis**: Filters items belonging to discretionary categories (shopping, travel, dining, etc.). If their sum exceeds 40% of total outflow, recommendations to cut back are rendered in the dashboard.

---

## 6. Installation & Execution Guide

### Prerequisites
Make sure you have Python 3.8+ installed on your computer.

### Step 1: Clone or Copy Project Files
Place all files inside a directory named `Personal_expense_analyzer` on your local disk.

### Step 2: Install Package Dependencies
Open terminal/cmd inside the directory and run:
```bash
pip install -r requirements.txt
```

### Step 3: Run the Local Server
Launch FastAPI's ASGI server via Uvicorn:
```bash
python -m uvicorn main:app --reload
```

### Step 4: Access Application
Open your web browser and navigate to:
```
http://127.0.0.1:8000
```
*(On first execution, the database `finance.db` will be created automatically in the root folder, and pre-seeded with master tracking categories).*

---

## 7. Final Academic Project Submission Notes

### Recommended Customization for Presentation:
1.  **Select Persona**: Register multiple accounts with distinct personas (e.g. Student vs Doctor). Log transactions and demonstrate how the dashboard charts and category options customize themselves automatically.
2.  **Verify ML Trends**: Log a sequence of increasing expenses (e.g., Grocery cost increasing by ₹200 every week) and show how the AI Suggestions panel triggers a "Upward Spending Trend" alert based on the regression slope.
3.  **Audit CSV Export**: Verify database integrity by adding several records, navigating to Reports, filtering by date range, and clicking "Export CSV" to show clean file generations.
