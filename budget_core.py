import datetime
from dataclasses import dataclass
from typing import List, Dict, Tuple


DEFAULT_CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Other"]


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

    def __post_init__(self):
        """Validate BudgetRule data after initialization."""
        # Validate category is not empty
        if not self.category or not self.category.strip():
            raise ValueError("Category cannot be empty")
        
        # Validate period is one of allowed values
        allowed_periods = {'daily', 'weekly', 'monthly', 'percentage'}
        if self.period not in allowed_periods:
            raise ValueError(f"Period must be one of {allowed_periods}, got '{self.period}'")
        
        # Validate threshold is strictly positive
        if self.threshold <= 0:
            raise ValueError(f"Threshold must be strictly positive, got {self.threshold}")
        
        # Validate alert_type is one of allowed values
        allowed_alert_types = {'exceed', 'percentage'}
        if self.alert_type not in allowed_alert_types:
            raise ValueError(f"Alert type must be one of {allowed_alert_types}, got '{self.alert_type}'")
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

    def __post_init__(self):
        """Validate RecurringRule data after initialization."""
        # Validate amount is strictly positive
        if self.amount <= 0:
            raise ValueError(f"Amount must be strictly positive, got {self.amount}")
        
        # Validate frequency is one of allowed values
        allowed_frequencies = {'daily', 'weekly', 'monthly', 'yearly'}
        if self.frequency not in allowed_frequencies:
            raise ValueError(f"Frequency must be one of {allowed_frequencies}, got '{self.frequency}'")
        
        # Validate end_date is not earlier than start_date
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError(f"End date ({self.end_date}) cannot be earlier than start date ({self.start_date})")
        
        # Validate last_generated_date is not in the future
        today = datetime.date.today()
        if self.last_generated_date is not None and self.last_generated_date > today:
            raise ValueError(f"Last generated date ({self.last_generated_date}) cannot be in the future")


def validate_category(category: str) -> bool:
    """Validate that a category name is valid (non-empty string)."""
    return isinstance(category, str) and len(category.strip()) > 0


def validate_categories(categories: List[str]) -> bool:
    """Validate that all categories are valid non-empty strings."""
    if not isinstance(categories, list):
        return False
    return all(validate_category(cat) for cat in categories)


def validate_transaction(date, amount, category, categories, description):
    """Validate a transaction"""
    errors = []
    try:
        date_val = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        if date_val > datetime.date.today():
            errors.append('Date cannot be in the future.')
    except ValueError:
        errors.append('Invalid date format. Use YYYY-MM-DD.')

    try:
        amount_val = float(amount)
        if amount_val < 0:
            errors.append('Amount must be non-negative.')
    except ValueError:
        errors.append('Invalid amount.')

    if category not in categories:
        errors.append('Category must be one of the allowed categories.')

    if not description:
        errors.append('Description is required.')

    return errors


def spending_by_category(transactions: List[Transaction]) -> Dict[str, float]:
    totals = {}
    for tx in transactions:
        totals[tx.category] = totals.get(tx.category, 0.0) + tx.amount
    return totals


def spending_by_period(transactions: List[Transaction], period: str = "daily") -> Dict[str, float]:
    totals = {}
    for tx in transactions:
        if period == "daily":
            label = tx.date.strftime("%Y-%m-%d")
        elif period == "weekly":
            year, week, _ = tx.date.isocalendar()
            label = f"{year}-W{week:02d}"
        elif period == "monthly":
            label = tx.date.strftime("%Y-%m")
        else:
            raise ValueError(f"Unsupported period: {period}")
        totals[label] = totals.get(label, 0.0) + tx.amount
    
    # Sort `totals` by its keys in ascending order
    return dict(sorted(totals.items()))


def top_categories(transactions: List[Transaction], n: int = 3) -> List[Tuple[str, float]]:
    '''
    Sort the categories in descending order of amount spent, and return the first `n` categories.
    '''

    totals = spending_by_category(transactions)
    return sorted(totals.items(), key=lambda x: x[1], reverse=True)[:n]


def spending_trend(transactions: List[Transaction], n: int = 7) -> Dict[str, float]:
    '''
    Amount spent for the last `n` days.
    '''

    if n <= 0:
        return {}
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=n-1)
    trend = { (start_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d"): 0.0 for i in range(n) }
    for tx in transactions:
        if start_date <= tx.date <= today:
            key = tx.date.strftime("%Y-%m-%d")
            trend[key] += tx.amount
    return trend


def monthly_spending_trend(transactions: List[Transaction]) -> Tuple[List[str], List[float]]:
    '''
    Returns a list of month-year labels and total spending for each month.
    '''
    monthly_totals = {}
    for tx in transactions:
        month_key = tx.date.strftime("%Y-%m")
        monthly_totals[month_key] = monthly_totals.get(month_key, 0.0) + tx.amount
    sorted_months = sorted(monthly_totals.keys())
    labels = sorted_months
    values = [monthly_totals[m] for m in sorted_months]
    return labels, values


def check_alerts(transactions: List[Transaction], rules: List[BudgetRule], categories: List[str]) -> List[str]:
    '''
    Generate alert messages.
    '''
    
    alerts = []

    if not transactions:
        return alerts

    # quick index by category
    tx_by_category: Dict[str, List[Transaction]] = {}
    for tx in transactions:
        tx_by_category.setdefault(tx.category, []).append(tx)

    # Rule 5: uncategorized check
    for tx in transactions:
        if tx.category not in categories:
            alerts.append(f"Uncategorized transaction: {tx.description} on {tx.date} as '{tx.category}'")

    total_all = sum(tx.amount for tx in transactions)

    for rule in rules:
        if rule.alert_type not in ("exceed", "percentage"):
            continue

        if rule.period == "percentage" or rule.alert_type == "percentage":
            category_total = sum(tx.amount for tx in tx_by_category.get(rule.category, []))
            if total_all > 0 and (category_total / total_all * 100) > rule.threshold:
                alerts.append(f"{rule.category} is {category_total / total_all * 100:.1f}% of total spending (threshold {rule.threshold}%).")
            continue

        # Only daily/weekly/monthly exceed
        category_txs = tx_by_category.get(rule.category, [])
        if not category_txs:
            continue

        period_totals = spending_by_period(category_txs, rule.period)
        for period_key, total in period_totals.items():
            if total > rule.threshold:
                alerts.append(f"{rule.category} spending ({rule.period} {period_key}) is {total:.2f}, exceeds threshold {rule.threshold:.2f}.")

    # Rule 4: consecutive overspend days by daily category cap
    daily_caps = {r.category: r.threshold for r in rules if r.period == "daily" and r.alert_type == "exceed"}
    if daily_caps:
        for category, cap in daily_caps.items():
            # gather daily totals for category
            cat_txs = sorted((tx for tx in transactions if tx.category == category), key=lambda t: t.date)
            day_totals = {}
            for tx in cat_txs:
                key = tx.date
                day_totals[key] = day_totals.get(key, 0.0) + tx.amount

            # check if consecutive overspend >= 3
            sorted_dates = sorted(day_totals)
            consec = 0
            prev_date = None
            for d in sorted_dates:
                if day_totals[d] > cap:
                    if prev_date and d == prev_date + datetime.timedelta(days=1):
                        consec += 1
                    else:
                        consec = 1
                    if consec >= 3:
                        alerts.append(f"{category} exceeded daily cap {cap:.2f} for {consec} consecutive days ending {d}.")
                else:
                    consec = 0
                prev_date = d

    # dedupe
    unique_alerts = []
    for a in alerts:
        if a not in unique_alerts:
            unique_alerts.append(a)

    return unique_alerts