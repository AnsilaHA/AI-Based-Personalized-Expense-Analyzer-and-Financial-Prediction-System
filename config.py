import os

# Base configuration class
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "super_secret_session_key_mca_project_2026")
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "finance.db")
    
    # Master Categories list for the database seeding
    MASTER_INCOME_CATEGORIES = [
        "Salary", "Business Income", "Rent Income", "Freelance", 
        "Pension", "Investments", "Pocket Money", "Other Income"
    ]

       
    MASTER_EXPENSE_CATEGORIES = [
        "Groceries", "Food & Dining", "Travel & Fuel", "Shopping", 
        "Medical & Hospital", "Child Education", "Electricity Bills", 
        "Water Bills", "Internet Bills", "AC Bills", "EMI Payments", 
        "LIC & Insurance", "Loan Repayment", "Credit Card Bills", 
        "Investments", "Gym & Fitness", "Trekking & Outdoor", 
        "Entertainment", "Beauty Products", "Donations", 
        "House Maintenance", "Pet Expenses", "Festival Expenses", 
        "Other Expense"
    ]
    
    # Preloaded recommendations by User Persona
    PERSONA_RECOMMENDATIONS = {
        "Student": [
            "Pocket Money", "Other Income", "Groceries", "Food & Dining", 
            "Travel & Fuel", "Shopping", "Internet Bills", "Gym & Fitness", 
            "Entertainment", "Other Expense"
        ],
        "Employee": [
            "Salary", "Other Income", "Groceries", "Food & Dining", 
            "Travel & Fuel", "Shopping", "Electricity Bills", "Internet Bills", 
            "EMI Payments", "LIC & Insurance", "Investments", "Entertainment", 
            "Other Expense"
        ],
        "Doctor": [
            "Salary", "Business Income", "Groceries", "Food & Dining", 
            "Travel & Fuel", "Medical & Hospital", "Electricity Bills", 
            "Internet Bills", "LIC & Insurance", "Investments", "Other Expense"
        ],
        "Business Owner": [
            "Business Income", "Investments", "Groceries", "Food & Dining", 
            "Travel & Fuel", "Electricity Bills", "AC Bills", "EMI Payments", 
            "LIC & Insurance", "Loan Repayment", "Investments", "House Maintenance", 
            "Other Expense"
        ],
        "Housewife": [
            "Other Income", "Groceries", "Food & Dining", "Shopping", 
            "Child Education", "Electricity Bills", "Water Bills", "Internet Bills", 
            "Beauty Products", "House Maintenance", "Festival Expenses", "Other Expense"
        ],
        "Middle-Class Family": [
            "Salary", "Rent Income", "Groceries", "Food & Dining", "Travel & Fuel", 
            "Shopping", "Child Education", "Electricity Bills", "Water Bills", 
            "Internet Bills", "EMI Payments", "LIC & Insurance", "House Maintenance", 
            "Other Expense"
        ],
        "Lower-Income User": [
            "Salary", "Other Income", "Groceries", "Food & Dining", "Travel & Fuel", 
            "Electricity Bills", "Water Bills", "Other Expense"
        ],
        "Other": [
            "Salary", "Other Income", "Groceries", "Food & Dining", "Travel & Fuel", 
            "Shopping", "Electricity Bills", "Internet Bills", "Other Expense"
        ]
    }
