import datetime
import os
from typing import Any, List
# from budget_core import ???
# from data_loader import ???

def days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    next_month = datetime.date(year, month + 1, 1)
    return (next_month - datetime.timedelta(days = 1)).day

def calculate_next_due_date(last_date: datetime.date, frequency: str) -> datetime.date:
    if frequency == 'daily':
        return last_date + datetime.timedelta(days=1)
    elif frequency == 'weekly':
        return last_date + datetime.timedelta(weeks=1)
    elif frequency == 'monthly':
        # Add one month
        year = last_date.year
        month = last_date.month + 1
        if month > 12:
            month = 1
            year += 1
        return datetime.date(year, month, min(last_date.day, days_in_month(year, month)))
    elif frequency == 'yearly':
        return datetime.date(last_date.year + 1, last_date.month, min(last_date.day, days_in_month(last_date.year + 1, last_date.month)))
    else:
        raise ValueError(f"Unsupported frequency: {frequency}")

def generate_recurring_transactions(
    recurring_rules: List[Any],         # dataclass to be defined in budget_core.py
    existing_transactions: List[Any],   # dataclass to be defined in budget_core.py
    today: datetime.date = None
) -> List[Any]:                         # dataclass to be defined in budget_core.py
    """
    Generate new transactions for recurring rules that are due.
    Returns a list of new transactions to add.
    """

    if today is None:
        today = datetime.date.today()
    
    new_transactions = []
    
    # To be adjusted after budget_core.py and data_loader.py are completed.
    
    return new_transactions

def process_recurring_transactions(data_dir: str, transactions: List[Any]) -> List[Any]:
    """
    Load recurring rules, generate new transactions, save updated rules, and return new transactions.
    """
    recurring_file = os.path.join(data_dir, 'recurring_rules.json')
    rules: List[Any]    # dataclass to be defined in budget_core.py
    new_txs = generate_recurring_transactions(rules, transactions)
    if new_txs:
        # Expected: function_to_save_recurring_rules(rules, recurring_file)
        pass
    return new_txs