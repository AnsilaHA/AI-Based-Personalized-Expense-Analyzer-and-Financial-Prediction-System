import os
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import bcrypt
from datetime import datetime, date
import csv
import io
from fastapi.responses import StreamingResponse

import database
from config import Config
import analyzer
import predictor

# Initialize FastAPI Application
app = FastAPI(title="AI-Based Personalized Expense Analyzer and Financial Prediction System")

# Enable secure cookie sessions via Starlette
app.add_middleware(SessionMiddleware, secret_key=Config.SECRET_KEY)

# Password hashing utilities
def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    pwd_bytes = password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)

# Mount Static assets & Setup Jinja2 HTML Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Helper to check authentication
def get_session_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = database.get_user_by_id(user_id)
    return user

# Startup database initialization
@app.on_event("startup")
async def startup_event():
    # If DB doesn't exist, create it and seed master categories
    if not os.path.exists(Config.DATABASE_PATH):
        print("Database not found. Initializing new database...")
        database.init_db()
    else:
        # Check if users table exists by running a quick query
        try:
            database.get_db_connection().execute("SELECT count(*) FROM users;").close()
        except Exception:
            print("Database structure incomplete. Re-initializing database...")
            database.init_db()

# ==========================================
# AUTHENTICATION ROUTERS
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    user = get_session_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/login", status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    user = get_session_user(request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={"error": error})

@app.post("/login")
async def handle_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    user = database.get_user_by_username(username)
    if not user or not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            request=request,
            name="login.html", 
            context={"error": "Invalid username or password"}
        )
    
    # Set session keys
    request.session["user_id"] = user["id"]
    request.session["username"] = user["username"]
    
    # Check if user has selected categories
    selected = database.get_user_selected_categories(user["id"])
    if not selected:
        return RedirectResponse(url="/onboarding", status_code=303)
        
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str = None):
    return templates.TemplateResponse(request=request, name="register.html", context={"error": error})

@app.post("/register")
async def handle_register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    persona: str = Form(...)
):
    if password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="register.html", 
            context={"error": "Passwords do not match"}
        )
        
    # Check existing user
    if database.get_user_by_username(username):
        return templates.TemplateResponse(
            request=request,
            name="register.html", 
            context={"error": "Username already taken"}
        )
    if database.get_user_by_email(email):
        return templates.TemplateResponse(
            request=request,
            name="register.html", 
            context={"error": "Email already registered"}
        )
        
    # Create user
    password_hash = hash_password(password)
    user_id = database.create_user(username, email, password_hash, persona)
    
    if not user_id:
        return templates.TemplateResponse(
            request=request,
            name="register.html", 
            context={"error": "Database error during registration"}
        )
        
    # Pre-select recommended categories based on persona automatically to streamline onboarding
    recommended_cats = Config.PERSONA_RECOMMENDATIONS.get(persona, [])
    all_cats = database.get_all_system_categories()
    
    recom_ids = [cat["id"] for cat in all_cats if cat["name"] in recommended_cats]
    database.save_user_categories(user_id, recom_ids)
    
    # Store session variables
    request.session["user_id"] = user_id
    request.session["username"] = username
    
    return RedirectResponse(url="/onboarding", status_code=303)

@app.get("/logout")
async def handle_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page(request: Request):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    system_categories = database.get_all_system_categories()
    
    # Break into income and expense for display
    income_cats = [cat for cat in system_categories if cat["type"] == "income"]
    expense_cats = [cat for cat in system_categories if cat["type"] == "expense"]
    
    # Retrieve recommended categories based on user's persona to check them by default
    recommended = Config.PERSONA_RECOMMENDATIONS.get(user["persona"], [])
    
    return templates.TemplateResponse(
        request=request,
        name="onboarding.html",
        context={
            "user": user,
            "income_cats": income_cats,
            "expense_cats": expense_cats,
            "recommended": recommended
        }
    )

@app.post("/onboarding")
async def handle_onboarding(
    request: Request,
    selected_categories: list[int] = Form(default=[])
):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    database.save_user_categories(user["id"], selected_categories)
    return RedirectResponse(url="/dashboard", status_code=303)

# ==========================================
# CORE DASHBOARD & ANALYTICS PAGES
# ==========================================

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    # Get general spending analytics from analyzer (Pandas)
    summary = analyzer.get_financial_summary(user["id"], user["monthly_budget"])
    
    # Get ML forecasts from predictor (Scikit-learn)
    predictions = predictor.generate_financial_predictions(user["id"], user["persona"])
    
    # Combine insights
    ai_insights = predictions["insights"]
    
    # Fetch recent transactions
    recent_transactions = database.get_user_transactions(user["id"])[:5]
    
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "summary": summary,
            "predictions": predictions,
            "ai_insights": ai_insights,
            "recent_transactions": recent_transactions
        }
    )

# ==========================================
# TRANSACTIONS MANAGEMENT CRUD
# ==========================================

@app.get("/transactions", response_class=HTMLResponse)
async def transactions_page(request: Request, type_filter: str = None, category_filter: str = None):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    # Safely parse category_filter to integer if provided, else None
    category_id = None
    if category_filter and category_filter.strip():
        try:
            category_id = int(category_filter)
        except ValueError:
            category_id = None

    # Fetch all user-active categories for dropdowns
    categories = database.get_user_selected_categories(user["id"])
    income_cats = [cat for cat in categories if cat["type"] == "income"]
    expense_cats = [cat for cat in categories if cat["type"] == "expense"]
    
    # Fetch filtered transactions
    transactions = database.get_user_transactions(
        user["id"], 
        type_filter=type_filter, 
        category_id=category_id
    )
    
    return templates.TemplateResponse(
        request=request,
        name="transactions.html",
        context={
            "user": user,
            "transactions": transactions,
            "income_cats": income_cats,
            "expense_cats": expense_cats,
            "categories": categories,
            "type_filter": type_filter,
            "category_filter": category_id
        }
    )

@app.post("/transactions/add")
async def add_new_transaction(
    request: Request,
    type: str = Form(...),
    category_id: int = Form(...),
    amount: float = Form(...),
    date: str = Form(...),
    description: str = Form(default=""),
    frequency: str = Form("one-time"),
    is_recurring: int = Form(0)
):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    if amount <= 0:
        # Invalid amount, redirect back with error or skip
        return RedirectResponse(url="/transactions?error=Amount+must+be+greater+than+zero", status_code=303)
        
    database.add_transaction(
        user_id=user["id"],
        category_id=category_id,
        t_type=type,
        amount=amount,
        date=date,
        description=description,
        frequency=frequency,
        is_recurring=is_recurring
    )
    return RedirectResponse(url="/transactions", status_code=303)

@app.post("/transactions/edit/{transaction_id}")
async def edit_existing_transaction(
    transaction_id: int,
    request: Request,
    type: str = Form(...),
    category_id: int = Form(...),
    amount: float = Form(...),
    date: str = Form(...),
    description: str = Form(default=""),
    frequency: str = Form("one-time"),
    is_recurring: int = Form(0)
):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    # Verify transaction owner
    tx = database.get_transaction_by_id(transaction_id, user["id"])
    if not tx:
         raise HTTPException(status_code=403, detail="Unauthorized transaction edit")
         
    database.update_transaction(
        transaction_id=transaction_id,
        user_id=user["id"],
        category_id=category_id,
        t_type=type,
        amount=amount,
        date=date,
        description=description,
        frequency=frequency,
        is_recurring=is_recurring
    )
    return RedirectResponse(url="/transactions", status_code=303)

@app.post("/transactions/delete/{transaction_id}")
async def delete_existing_transaction(
    transaction_id: int,
    request: Request
):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    # Verify owner
    tx = database.get_transaction_by_id(transaction_id, user["id"])
    if not tx:
         raise HTTPException(status_code=403, detail="Unauthorized transaction delete")
         
    database.delete_transaction(transaction_id, user["id"])
    return RedirectResponse(url="/transactions", status_code=303)

# ==========================================
# ANALYTICAL REPORTS
# ==========================================

@app.get("/reports", response_class=HTMLResponse)
async def reports_page(
    request: Request, 
    start_date: str = None, 
    end_date: str = None
):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    # 1. Fetch pre-calculated static aggregates for current month, half-yearly and yearly
    time_reports = analyzer.get_time_based_reports(user["id"])
    
    # 2. Handle Custom Date Range Search Query
    custom_transactions = []
    custom_totals = {"income": 0.0, "expense": 0.0, "savings": 0.0}
    if start_date or end_date:
        custom_transactions = database.get_user_transactions(
            user["id"],
            start_date=start_date if start_date else None,
            end_date=end_date if end_date else None
        )
        for tx in custom_transactions:
            if tx["type"] == "income":
                custom_totals["income"] += tx["amount"]
            elif tx["type"] == "expense":
                custom_totals["expense"] += tx["amount"]
        custom_totals["savings"] = custom_totals["income"] - custom_totals["expense"]
        
    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={
            "user": user,
            "time_reports": time_reports,
            "custom_transactions": custom_transactions,
            "custom_totals": custom_totals,
            "start_date": start_date,
            "end_date": end_date
        }
    )

@app.get("/reports/export")
async def export_csv(request: Request, start_date: str = None, end_date: str = None):
    user = get_session_user(request)
    if not user:
         return RedirectResponse(url="/login", status_code=303)
         
    transactions = database.get_user_transactions(
        user["id"],
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None
    )
    
    # Write transactions to temporary memory file
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Date", "Type", "Category", "Amount (₹)", "Description", "Frequency", "Recurring"])
    
    for tx in transactions:
        writer.writerow([
            tx["id"], 
            tx["date"], 
            tx["type"].capitalize(), 
            tx["category_name"], 
            tx["amount"], 
            tx["description"], 
            tx["frequency"].capitalize(),
            "Yes" if tx["is_recurring"] else "No"
        ])
        
    output.seek(0)
    
    headers = {
        'Content-Disposition': f'attachment; filename=ExpenseReport_{datetime.now().strftime("%Y%m%d")}.csv'
    }
    return StreamingResponse(io.BytesIO(output.getvalue().encode('utf-8')), media_type='text/csv', headers=headers)

# ==========================================
# SETTINGS & CUSTOMIZATION
# ==========================================

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    # Get all categories
    system_categories = database.get_all_system_categories()
    
    # Get user selected categories
    selected_cats = database.get_user_selected_categories(user["id"])
    selected_ids = [cat["id"] for cat in selected_cats]
    
    income_cats = [cat for cat in system_categories if cat["type"] == "income"]
    expense_cats = [cat for cat in system_categories if cat["type"] == "expense"]
    
    # Custom categories created specifically by user
    custom_cats = [cat for cat in selected_cats if cat["is_custom"] == 1]
    
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "user": user,
            "income_cats": income_cats,
            "expense_cats": expense_cats,
            "selected_ids": selected_ids,
            "custom_cats": custom_cats
        }
    )

@app.post("/settings/budget")
async def update_budget(request: Request, budget: float = Form(...)):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    database.update_user_budget(user["id"], max(budget, 0.0))
    return RedirectResponse(url="/settings?msg=Budget+updated+successfully", status_code=303)

@app.post("/settings/custom_category")
async def add_user_custom_category(
    request: Request,
    name: str = Form(...),
    type: str = Form(...)
):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    # Add custom category to db (automatically links to user_categories)
    database.add_custom_category(user["id"], name.strip(), type)
    return RedirectResponse(url="/settings?msg=Custom+category+added", status_code=303)

@app.post("/settings/categories/save")
async def save_active_categories(
    request: Request,
    selected_categories: list[int] = Form(default=[])
):
    user = get_session_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
        
    database.save_user_categories(user["id"], selected_categories)
    return RedirectResponse(url="/settings?msg=Category+selections+saved", status_code=303)

# ==========================================
# CHARTING & ML FORECAST JSON API ENDPOINTS
# ==========================================

@app.get("/api/dashboard_data")
async def get_api_dashboard_data(request: Request):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    transactions = database.get_user_transactions(user["id"])
    if not transactions:
        return {"category_labels": [], "category_values": [], "timeline_labels": [], "timeline_income": [], "timeline_expense": []}
        
    import pandas as pd
    df = pd.DataFrame(transactions)
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # 1. Category Distribution (Expenses only)
    expenses_df = df[df['type'] == 'expense']
    if not expenses_df.empty:
        cat_grouped = expenses_df.groupby('category_name')['amount'].sum().sort_values(ascending=False)
        cat_labels = cat_grouped.index.tolist()
        cat_values = cat_grouped.values.tolist()
    else:
        cat_labels, cat_values = [], []
        
    # 2. Timeline chart (Grouped by year-month)
    df['year_month'] = df['date'].dt.strftime('%b %Y')
    # To sort chronologically, group by period first
    df['period'] = df['date'].dt.to_period('M')
    
    timeline_grouped = df.groupby(['period', 'year_month', 'type'])['amount'].sum().unstack(fill_value=0.0).reset_index()
    # Sort chronologically
    timeline_grouped = timeline_grouped.sort_values('period')
    
    timeline_labels = timeline_grouped['year_month'].tolist()
    timeline_income = timeline_grouped['income'].tolist() if 'income' in timeline_grouped else [0.0] * len(timeline_labels)
    timeline_expense = timeline_grouped['expense'].tolist() if 'expense' in timeline_grouped else [0.0] * len(timeline_labels)
    
    # If columns were missing, unstack might not have populated columns properly
    if 'income' not in timeline_grouped.columns:
        timeline_income = [0.0] * len(timeline_labels)
    if 'expense' not in timeline_grouped.columns:
        timeline_expense = [0.0] * len(timeline_labels)
        
    return {
        "category_labels": cat_labels,
        "category_values": cat_values,
        "timeline_labels": timeline_labels,
        "timeline_income": timeline_income,
        "timeline_expense": timeline_expense
    }

@app.get("/api/predictions")
async def get_api_predictions_data(request: Request):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    predictions = predictor.generate_financial_predictions(user["id"], user["persona"])
    
    # Format labels & values for Category Prediction Chart
    cat_labels = list(predictions["category_predictions"].keys())
    cat_values = list(predictions["category_predictions"].values())
    
    return {
        "next_month_expense": predictions["next_month_expense"],
        "next_quarter_expense": predictions["next_quarter_expense"],
        "next_year_expense": predictions["next_year_expense"],
        "next_month_savings": predictions["next_month_savings"],
        "predicted_savings_rate": predictions["predicted_savings_rate"],
        "model_status": predictions["model_status"],
        "insights": predictions["insights"],
        "cat_labels": cat_labels,
        "cat_values": cat_values
    }
