import requests

API_URL = "http://localhost:8000/api/expenses"

expenses = [
    {"name": "Internet Bill", "amount": None, "day_of_month": 1, "category": "Bills", "description": ""},
    {"name": "Milk Payment", "amount": None, "day_of_month": 1, "category": "Bills", "description": ""},
    {"name": "Credit Card Payment - ICICI", "amount": None, "day_of_month": 2, "category": "Payments", "description": ""},
    {"name": "Credit Card Payment - SBI", "amount": None, "day_of_month": 2, "category": "Payments", "description": ""},
    {"name": "Housekeeping Payment", "amount": None, "day_of_month": 2, "category": "Payments", "description": ""},
    {"name": "Home Maintenance Bill", "amount": None, "day_of_month": 2, "category": "Maintenance", "description": ""},
    {"name": "Money Send to Home 1", "amount": None, "day_of_month": 3, "category": "Payments", "description": ""},
    {"name": "Money Send to Home 2", "amount": None, "day_of_month": 3, "category": "Payments", "description": ""},
    {"name": "Airtel Bill", "amount": None, "day_of_month": 4, "category": "Bills", "description": ""},
    {"name": "PPF - Nootan", "amount": None, "day_of_month": 4, "category": "Investments", "description": ""},
    {"name": "SSY - Nootan", "amount": None, "day_of_month": 4, "category": "Investments", "description": ""},
    {"name": "Mutual funds - Nootan", "amount": None, "day_of_month": 5, "category": "Investments", "description": ""},
    {"name": "Mutual funds - Arun", "amount": None, "day_of_month": 5, "category": "Investments", "description": ""},
    {"name": "Cleaner Payment", "amount": None, "day_of_month": 5, "category": "Payments", "description": ""},
    {"name": "Premium For Term Insurance - Nootan", "amount": None, "day_of_month": 6, "category": "Insurance", "description": ""},
    {"name": "Premium For Term Insurance - Arun", "amount": None, "day_of_month": 6, "category": "Insurance", "description": ""},
    {"name": "Malabar Gold Plan Deposit", "amount": None, "day_of_month": 9, "category": "Investments", "description": ""},
    {"name": "Sohan Fortune EMI", "amount": None, "day_of_month": 9, "category": "EMI", "description": ""},
    {"name": "Arvind Forest Trails EMI", "amount": None, "day_of_month": 9, "category": "EMI", "description": ""},
    {"name": "Electricity bill", "amount": None, "day_of_month": 13, "category": "Bills", "description": ""},
    {"name": "Mana The Right Life EMI", "amount": 24000, "day_of_month": 28, "category": "EMI", "description": "12k Principle + 12k Interest"},
]

print("Adding expenses to the database...")
added_count = 0

for expense in expenses:
    try:
        response = requests.post(API_URL, json=expense)
        if response.status_code == 200:
            added_count += 1
            print(f"✓ Added: {expense['name']}")
        else:
            print(f"✗ Failed: {expense['name']} - {response.status_code}")
    except Exception as e:
        print(f"✗ Error adding {expense['name']}: {str(e)}")

print(f"\n✅ Successfully added {added_count}/{len(expenses)} expenses!")
print("\nRefresh your Monthly Expenses page to see them.")
