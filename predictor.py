import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
import database

# Persona Baselines for typical monthly incomes and expenses (in INR / ₹)
# Helps with the "Cold Start" problem in ML final-year projects
PERSONA_BASELINES = {
    "Student": {"income": 12000.0, "expense": 9500.0},
    "Employee": {"income": 60000.0, "expense": 42000.0},
    "Doctor": {"income": 180000.0, "expense": 110000.0},
    "Business Owner": {"income": 200000.0, "expense": 140000.0},
    "Housewife": {"income": 15000.0, "expense": 13000.0},
    "Middle-Class Family": {"income": 75000.0, "expense": 55000.0},
    "Lower-Income User": {"income": 18000.0, "expense": 16000.0},
    "Other": {"income": 40000.0, "expense": 30000.0}
}

def generate_financial_predictions(user_id, persona="Other"):
    """
    Predicts future expenses and savings using Scikit-learn Linear Regression.
    Incorporates a statistical persona fallback model for cold-start users.
    """
    transactions = database.get_user_transactions(user_id)
    
    # Baseline defaults based on user's persona profile
    baseline = PERSONA_BASELINES.get(persona, PERSONA_BASELINES["Other"])
    
    predictions = {
        "next_month_expense": baseline["expense"],
        "next_quarter_expense": baseline["expense"] * 3,
        "next_year_expense": baseline["expense"] * 12,
        "next_month_savings": baseline["income"] - baseline["expense"],
        "predicted_savings_rate": ((baseline["income"] - baseline["expense"]) / baseline["income"] * 100) if baseline["income"] > 0 else 0.0,
        "model_status": "Persona Baseline Model (Cold-Start Mode)",
        "insights": [],
        "category_predictions": {}
    }
    
    if not transactions or len(transactions) < 5:
        # User has insufficient data. Blend baseline with user's few transactions if available.
        predictions["insights"].append(
            "⚠️ **Standard Baseline Mode**: Predictions are based on average parameters for your persona profile. As you log more transactions (at least 5 distinct dates), our Scikit-learn machine learning engine will train on your unique spending timeline."
        )
        
        # If there are some transactions, adjust baseline slightly
        if transactions:
            df = pd.DataFrame(transactions)
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
            avg_daily_exp = df[df['type'] == 'expense']['amount'].sum() / 30.0 if not df[df['type'] == 'expense'].empty else 0.0
            if avg_daily_exp > 0:
                user_monthly_avg = avg_daily_exp * 30
                # Weighted average: 70% persona, 30% user historical
                blended_expense = (baseline["expense"] * 0.7) + (user_monthly_avg * 0.3)
                predictions.update({
                    "next_month_expense": blended_expense,
                    "next_quarter_expense": blended_expense * 3,
                    "next_year_expense": blended_expense * 12,
                    "model_status": "Blended Persona-User Model (Insufficient Data)"
                })
        return predictions

    # Create DataFrame
    df = pd.DataFrame(transactions)
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # Sort chronologically
    df = df.sort_values('date')
    
    # We aggregate expenses by date
    expenses = df[df['type'] == 'expense']
    incomes = df[df['type'] == 'income']
    
    # Average Income Projection (using median of recorded incomes to represent normal income)
    if not incomes.empty:
        # Group monthly or take standard average monthly income
        incomes['year_month'] = incomes['date'].dt.to_period('M')
        monthly_income_sums = incomes.groupby('year_month')['amount'].sum()
        projected_monthly_income = float(monthly_income_sums.mean())
    else:
        projected_monthly_income = baseline["income"]

    if expenses.empty or len(expenses) < 3:
        # If we have transactions but no expense logs, return baseline with a warning
        predictions["insights"].append("Add expenses to unlock predictive spending regression models.")
        return predictions

    # Group expenses by date (daily aggregate) to construct training features
    daily_expenses = expenses.groupby('date')['amount'].sum().reset_index()
    
    # Train Linear Regression model for overall expenses
    # Feature X: Ordinal date representation (number of days from start date)
    start_date = daily_expenses['date'].min()
    daily_expenses['days_elapsed'] = (daily_expenses['date'] - start_date).dt.days
    
    X = daily_expenses['days_elapsed'].values.reshape(-1, 1)
    y = daily_expenses['amount'].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    # Calculate slope (coefficient) to generate trend insights
    slope = float(model.coef_[0])
    intercept = float(model.intercept_)
    
    # Forecasting timeframes
    last_day = daily_expenses['days_elapsed'].max()
    
    # Forecast next 30 days (Days from last_day + 1 to last_day + 30)
    future_30_days = np.array(range(last_day + 1, last_day + 31)).reshape(-1, 1)
    pred_30_days_raw = model.predict(future_30_days)
    # Ensure no negative predictions
    pred_30_days = np.clip(pred_30_days_raw, 0, None)
    next_month_total = float(pred_30_days.sum())
    
    # Forecast next 90 days (Quarter)
    future_90_days = np.array(range(last_day + 1, last_day + 91)).reshape(-1, 1)
    pred_90_days = np.clip(model.predict(future_90_days), 0, None)
    next_quarter_total = float(pred_90_days.sum())
    
    # Forecast next 365 days (Year)
    future_365_days = np.array(range(last_day + 1, last_day + 366)).reshape(-1, 1)
    pred_365_days = np.clip(model.predict(future_365_days), 0, None)
    next_year_total = float(pred_365_days.sum())
    
    # Savings predictions
    next_month_savings = projected_monthly_income - next_month_total
    savings_rate = (next_month_savings / projected_monthly_income * 100) if projected_monthly_income > 0 else 0.0
    
    # Category specific predictions using scikit-learn
    cat_preds = {}
    categories_present = expenses['category_name'].unique()
    for cat in categories_present:
        cat_df = expenses[expenses['category_name'] == cat].groupby('date')['amount'].sum().reset_index()
        if len(cat_df) >= 3:
            cat_df['days_elapsed'] = (cat_df['date'] - start_date).dt.days
            cX = cat_df['days_elapsed'].values.reshape(-1, 1)
            cy = cat_df['amount'].values
            c_model = LinearRegression().fit(cX, cy)
            
            c_future = np.array(range(last_day + 1, last_day + 31)).reshape(-1, 1)
            c_pred = np.clip(c_model.predict(c_future), 0, None).sum()
            cat_preds[cat] = float(c_pred)
        else:
            # Fallback to simple average daily spending scaled to monthly
            cat_total = cat_df['amount'].sum()
            days_range = max((cat_df['date'].max() - cat_df['date'].min()).days, 1)
            cat_preds[cat] = float((cat_total / days_range) * 30.0)
            
    # Compile dynamic text insights based on regression slope
    insights = []
    if slope > 0.5:
        insights.append(
            f"📈 **Upward Spending Trend**: Your daily expenses are trending upwards at an estimated rate of ₹{slope:.2f} per day. If this continues, your next month's spending is predicted to be ₹{next_month_total:,.2f}."
        )
    elif slope < -0.5:
        insights.append(
            f"📉 **Downward Spending Trend**: Excellent! Your daily expenses show a decreasing trend of ₹{abs(slope):.2f} per day, indicating improved budgetary self-discipline."
        )
    else:
        insights.append(
            "📊 **Stable Spending Flow**: Your expenditure trajectory is currently stable. There are no sudden growth surges detected in your daily cycles."
        )
        
    # Savings warnings
    if next_month_savings < 0:
        insights.append(
            f"🚨 **Projected Deficit**: Based on current trends, your expenses next month are predicted to exceed your income by ₹{abs(next_month_savings):,.2f}. Cut discretionary categories immediately!"
        )
    elif savings_rate > 25.0:
        insights.append(
            f"💡 **Target Achieved**: Predictions indicate you will save about ₹{next_month_savings:,.2f} ({savings_rate:.1f}%) next month, exceeding the 20% standard target."
        )
        
    # Spot category growth projections
    high_growth_cat = None
    max_growth_val = -np.inf
    for cat, val in cat_preds.items():
        # Get historical average monthly spend
        cat_hist_df = expenses[expenses['category_name'] == cat]
        cat_hist_total = cat_hist_df['amount'].sum()
        # Scale to monthly
        date_span = max((expenses['date'].max() - expenses['date'].min()).days, 30)
        hist_monthly_avg = (cat_hist_total / date_span) * 30
        
        growth = val - hist_monthly_avg
        if growth > max_growth_val:
            max_growth_val = growth
            high_growth_cat = cat
            
    if high_growth_cat and max_growth_val > 500:
        insights.append(
            f"🔔 **Category Escalation**: Your expenditure on **{high_growth_cat}** is projected to grow. Keep a close eye on this category to prevent leakage."
        )
        
    predictions.update({
        "next_month_expense": next_month_total,
        "next_quarter_expense": next_quarter_total,
        "next_year_expense": next_year_total,
        "next_month_savings": next_month_savings,
        "predicted_savings_rate": savings_rate,
        "model_status": "Scikit-Learn LinearRegression Engine (Active)",
        "insights": insights,
        "category_predictions": cat_preds
    })
    
    return predictions
