import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import database


def get_financial_summary(user_id, monthly_budget=0.0):
    """
    Computes key financial metrics and analytics using Pandas.
    Returns a structured dictionary containing totals, trends, and AI-driven suggestions.
    """
    # Fetch all user transactions from SQLite
    transactions = database.get_user_transactions(user_id)
    
    # Initialize empty response structure
    summary = {
        "total_income": 0.0,
        "total_expense": 0.0,
        "savings": 0.0,
        "savings_rate": 0.0,
        "total_debt": 0.0,
        "total_credit": 0.0,
        "remaining_balance": 0.0,
        "highest_expense_category": "None",
        "highest_expense_amount": 0.0,
        "budget_utilization": 0.0,
        "suggestions": [],
        "category_totals": {},
        "has_data": False
    }
    
    if not transactions:
        # User has no transaction history yet, provide default onboarding advice
        summary["suggestions"].append(
            "Welcome! Start by adding your regular income sources and daily/monthly expenses in the Transactions panel."
        )
        return summary

    summary["has_data"] = True
    
    # Convert list of dicts to Pandas DataFrame
    df = pd.DataFrame(transactions)
    
    # Convert types and parse date format
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # Filter types
    income_df = df[df['type'] == 'income']
    expense_df = df[df['type'] == 'expense']
    debt_df = df[df['type'] == 'debt']
    credit_df = df[df['type'] == 'credit']
    
    # 1. Totals Calculations
    total_income = float(income_df['amount'].sum()) if not income_df.empty else 0.0
    total_expense = float(expense_df['amount'].sum()) if not expense_df.empty else 0.0
    total_debt = float(debt_df['amount'].sum()) if not debt_df.empty else 0.0
    total_credit = float(credit_df['amount'].sum()) if not credit_df.empty else 0.0
    
    # Savings and rates
    savings = total_income - total_expense
    savings_rate = (savings / total_income * 100) if total_income > 0 else 0.0
    
    # Remaining cash flow balance
    # Net flow = Inflow (Income + Credit received) - Outflow (Expense + Debts paid/taken)
    remaining_balance = (total_income + total_credit) - (total_expense + total_debt)
    
    summary.update({
        "total_income": total_income,
        "total_expense": total_expense,
        "savings": savings,
        "savings_rate": savings_rate,
        "total_debt": total_debt,
        "total_credit": total_credit,
        "remaining_balance": remaining_balance
    })
    
    # 2. Category totals (for charts)
    if not expense_df.empty:
        cat_sums = expense_df.groupby('category_name')['amount'].sum()
        summary["category_totals"] = cat_sums.to_dict()
        
        # Highest spending category
        highest_cat = cat_sums.idxmax()
        highest_val = float(cat_sums.max())
        summary.update({
            "highest_expense_category": highest_cat,
            "highest_expense_amount": highest_val
        })
        
    # 3. Budget utilization
    if monthly_budget > 0:
        summary["budget_utilization"] = (total_expense / monthly_budget) * 100
        
    # 4. Generate intelligent AI financial suggestions using Pandas & NumPy
    suggestions = []
    
    # Insight A: Income vs Expense deficit
    if total_expense > total_income:
        deficit = total_expense - total_income
        suggestions.append({
            "type": "danger",
            "title": "Cash Flow Deficit",
            "text": f"Your expenses (₹{total_expense:,.2f}) exceed your income (₹{total_income:,.2f}) by ₹{deficit:,.2f}. You are operating at a loss. Cut non-essential expenses immediately."
        })
    elif total_income > 0 and savings_rate < 10.0:
        suggestions.append({
            "type": "warning",
            "title": "Low Savings Rate",
            "text": f"Your savings rate is {savings_rate:.1f}%. Financial experts recommend saving at least 20% of your income. Adjust your budget to prioritize savings."
        })
    elif savings_rate >= 20.0:
        suggestions.append({
            "type": "success",
            "title": "Healthy Savings Margin",
            "text": f"Great job! You saved {savings_rate:.1f}% of your income. You are on track to build a solid emergency fund."
        })
        
    # Insight B: Budget limits checks
    if monthly_budget > 0:
        if total_expense > monthly_budget:
            overspent = total_expense - monthly_budget
            suggestions.append({
                "type": "danger",
                "title": "Budget Ceiling Exceeded",
                "text": f"You've exceeded your designated monthly budget of ₹{monthly_budget:,.2f} by ₹{overspent:,.2f}. Consider modifying your alerts or freezing purchases."
            })
        elif total_expense >= 0.8 * monthly_budget:
            pct = (total_expense / monthly_budget) * 100
            suggestions.append({
                "type": "warning",
                "title": "Approaching Budget Cap",
                "text": f"You've used {pct:.1f}% of your monthly budget (₹{monthly_budget:,.2f}). Only purchase essential items for the remainder of this cycle."
            })
            
    # Insight C: Discretionary lifestyle spending inflation
    discretionary_categories = ["Shopping", "Food & Dining", "Entertainment", "Beauty Products", "Trekking & Outdoor"]
    if not expense_df.empty:
        discr_df = expense_df[expense_df['category_name'].isin(discretionary_categories)]
        discr_total = float(discr_df['amount'].sum())
        if total_expense > 0:
            discr_pct = (discr_total / total_expense) * 100
            if discr_pct > 40.0:
                suggestions.append({
                    "type": "warning",
                    "title": "Discretionary Spending Alert",
                    "text": f"Unnecessary spending (dining, shopping, lifestyle) accounts for {discr_pct:.1f}% of your total expenses. Trimming these could free up ₹{discr_total:,.2f}."
                })
                
    # Insight D: High Debt burden checks
    if total_debt > 0 and total_income > 0:
        debt_pct = (total_debt / total_income) * 100
        if debt_pct > 35.0:
            suggestions.append({
                "type": "danger",
                "title": "High Debt Burden",
                "text": f"Your outstanding debt is {debt_pct:.1f}% of your monthly income. Keeping debt payments below 30% is critical for your financial score."
            })
            
    # Insight E: Month-over-Month Category Trend Spike (using Pandas shift & comparison)
    if len(df) > 1 and not expense_df.empty:
        # Add period (Year-Month) column
        df['year_month'] = df['date'].dt.to_period('M')
        
        # Filter expense df and group by month + category
        cat_monthly_df = df[df['type'] == 'expense'].groupby(['year_month', 'category_name'])['amount'].sum().reset_index()
        
        # Make sure we have at least 2 distinct months in data to do comparison
        distinct_months = cat_monthly_df['year_month'].unique()
        if len(distinct_months) >= 2:
            # Sort months safely using Python's built-in sorted (PeriodArray does not have .sort())
            distinct_months = sorted(distinct_months)
            current_month = distinct_months[-1]
            previous_month = distinct_months[-2]
            
            # Fetch current and previous month records
            curr_data = cat_monthly_df[cat_monthly_df['year_month'] == current_month]
            prev_data = cat_monthly_df[cat_monthly_df['year_month'] == previous_month]
            
            # Merge to align categories
            merged = pd.merge(curr_data, prev_data, on='category_name', suffixes=('_curr', '_prev'))
            
            # Calculate MoM percentage change
            merged['pct_change'] = ((merged['amount_curr'] - merged['amount_prev']) / merged['amount_prev']) * 100
            
            # Find categories with increase > 20%
            spikes = merged[merged['pct_change'] > 20.0]
            for _, row in spikes.iterrows():
                suggestions.append({
                    "type": "warning",
                    "title": f"Spike in {row['category_name']}",
                    "text": f"Your spending on '{row['category_name']}' spiked by {row['pct_change']:.1f}% compared to last month (from ₹{row['amount_prev']:,.2f} to ₹{row['amount_curr']:,.2f})."
                })

    summary["suggestions"] = suggestions
    return summary

def get_time_based_reports(user_id):
    """
    Calculates summaries filtered by time frames:
    - Monthly (Current month)
    - Half-Yearly (Last 6 months)
    - Yearly (Last 12 months)
    """
    transactions = database.get_user_transactions(user_id)
    
    reports = {
        "monthly": {"income": 0.0, "expense": 0.0, "savings": 0.0, "categories": {}},
        "half_yearly": {"income": 0.0, "expense": 0.0, "savings": 0.0, "categories": {}},
        "yearly": {"income": 0.0, "expense": 0.0, "savings": 0.0, "categories": {}}
    }
    
    if not transactions:
        return reports
        
    df = pd.DataFrame(transactions)
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)
    start_of_half_year = now - timedelta(days=180)
    start_of_year = now - timedelta(days=365)
    
    # 1. Monthly (Current Month)
    m_df = df[df['date'] >= start_of_month]
    reports["monthly"] = _compile_report_subset(m_df)
    
    # 2. Half-Yearly (Last 6 Months)
    h_df = df[df['date'] >= start_of_half_year]
    reports["half_yearly"] = _compile_report_subset(h_df)
    
    # 3. Yearly (Last 12 Months)
    y_df = df[df['date'] >= start_of_year]
    reports["yearly"] = _compile_report_subset(y_df)
    
    return reports

def _compile_report_subset(sub_df):
    """Helper method to group and aggregate subsets of transactions."""
    if sub_df.empty:
        return {"income": 0.0, "expense": 0.0, "savings": 0.0, "categories": {}}
        
    income_sum = float(sub_df[sub_df['type'] == 'income']['amount'].sum())
    expense_sum = float(sub_df[sub_df['type'] == 'expense']['amount'].sum())
    savings = income_sum - expense_sum
    
    categories = {}
    expense_subset = sub_df[sub_df['type'] == 'expense']
    if not expense_subset.empty:
        grouped = expense_subset.groupby('category_name')['amount'].sum()
        categories = grouped.to_dict()
        
    return {
        "income": income_sum,
        "expense": expense_sum,
        "savings": savings,
        "categories": categories
    }
