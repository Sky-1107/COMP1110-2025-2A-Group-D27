import datetime
import os
from typing import Any, List
from budget_core import RecurringRule, Transaction
from data_loader import load_recurring_rules, save_recurring_rules, generate_new_transaction_id

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
    recurring_rules: List[RecurringRule],
    existing_transactions: List[Transaction],
    today: datetime.date = None
) -> List[Transaction]:
    """
    Generate new transactions for recurring rules that are due.
    Returns a list of new transactions to add.
    """

    if today is None:
        today = datetime.date.today()
    
    new_transactions = []
    
    for rule in recurring_rules:
        if today < rule.start_date or (rule.end_date and today > rule.end_date):
            continue
        
        # Calculate next due date
        last_gen = rule.last_generated_date or (rule.start_date - datetime.timedelta(days=1))
        next_due = calculate_next_due_date(last_gen, rule.frequency)
        
        while next_due <= today and (not rule.end_date or next_due <= rule.end_date):
            # Generate transaction
            new_id = generate_new_transaction_id(existing_transactions + new_transactions)
            tx = Transaction(
                date=next_due,
                amount=rule.amount,
                category=rule.category,
                description=f"[Recurring] {rule.name}",
                notes=rule.description,
                id=new_id
            )
            new_transactions.append(tx)
            
            # Update last_generated_date
            rule.last_generated_date = next_due
            next_due = calculate_next_due_date(next_due, rule.frequency)
    
    return new_transactions

def process_recurring_transactions(data_dir: str, transactions: List[Any]) -> List[Any]:
    """
    Load recurring rules, generate new transactions, save updated rules, and return new transactions.
    """
    recurring_file = os.path.join(data_dir, 'recurring_rules.json')
    rules = load_recurring_rules(recurring_file)
    new_txs = generate_recurring_transactions(rules, transactions)
    if new_txs:
        save_recurring_rules(rules, recurring_file)
        pass
    return new_txs