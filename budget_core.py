#budget_core.py

import datetime
from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass
class Transaction:
    date: datetime.date
    amount: float
    category: str
    description: str
    notes: str = ""
    id: int = 0

@dataclass
class BudgetRule:
    category: str
    period: str  # daily, weekly, monthly, percentage
    threshold: float
    alert_type: str  # exceed, percentage

@dataclass
class RecurringRule:
    name: str
    category: str
    amount: float
    description: str
    frequency: str  # daily, weekly, monthly, yearly
    start_date: datetime.date
    end_date: datetime.date = None
    last_generated_date: datetime.date = None

DEFAULT_CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Other"]

def spending_by_category(transactions: List[Transaction]) -> Dict[str, float]:
    totals = {}
    for tx in transactions:
        totals[tx.category] = totals.get(tx.category, 0.0) + tx.amount
    return totals
