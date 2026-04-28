import csv
import json
import os
import datetime
from typing import List
from budget_core import Transaction, BudgetRule, RecurringRule, DEFAULT_CATEGORIES


def parse_date(s: str):
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def load_transactions(filepath: str) -> List[Transaction]:
    transactions = []
    if not os.path.exists(filepath):
        return transactions
    try:
        with open(filepath, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row:
                    continue
                date = parse_date(row.get('date', ''))
                amount = None
                try:
                    amount = float(row.get('amount', '0'))
                except ValueError:
                    continue
                category = row.get('category', 'Other').strip()
                description = row.get('description', '').strip()
                notes = row.get('notes', '').strip()
                id_val = 0
                try:
                    id_val = int(row.get('id', '0'))
                except ValueError:
                    pass
                if date is None or amount is None:
                    continue
                transactions.append(Transaction(date=date, amount=amount, category=category, description=description, notes=notes, id=id_val))
    except Exception:
        return []
    return transactions


def save_transactions(transactions: List[Transaction], filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'date', 'amount', 'category', 'description', 'notes'])
        for tx in transactions:
            writer.writerow([tx.id, tx.date.strftime('%Y-%m-%d'), f"{tx.amount:.2f}", tx.category, tx.description, tx.notes])


def load_budget_rules(filepath: str) -> List[BudgetRule]:
    rules = []
    if not os.path.exists(filepath):
        return rules
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            for item in data:
                if not isinstance(item, dict):
                    continue
                category = item.get('category', '').strip()
                period = item.get('period', '').strip().lower()
                try:
                    threshold = float(item.get('threshold', 0))
                except (ValueError, TypeError):
                    continue
                alert_type = item.get('alert_type', '').strip().lower()
                if category and period and alert_type:
                    rules.append(BudgetRule(category=category, period=period, threshold=threshold, alert_type=alert_type))
    except Exception:
        return []
    return rules


def save_budget_rules(rules: List[BudgetRule], filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    data = []
    for r in rules:
        data.append({
            'category': r.category,
            'period': r.period,
            'threshold': r.threshold,
            'alert_type': r.alert_type,
        })
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def load_categories(filepath: str) -> List[str]:
    if not os.path.exists(filepath):
        return DEFAULT_CATEGORIES.copy()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
    except Exception:
        return DEFAULT_CATEGORIES.copy()
    return DEFAULT_CATEGORIES.copy()


def save_categories(categories: List[str], filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(categories, f, indent=2)


def load_recurring_rules(filepath: str) -> List[RecurringRule]:
    rules = []
    if not os.path.exists(filepath):
        return rules
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            for item in data:
                if not isinstance(item, dict):
                    continue
                name = item.get('name', '').strip()
                category = item.get('category', '').strip()
                try:
                    amount = float(item.get('amount', 0))
                except (ValueError, TypeError):
                    continue
                description = item.get('description', '').strip()
                frequency = item.get('frequency', '').strip().lower()
                start_date = parse_date(item.get('start_date', ''))
                end_date_str = item.get('end_date', None)
                end_date = parse_date(end_date_str) if end_date_str else None
                last_generated = parse_date(item.get('last_generated_date', '')) if item.get('last_generated_date') else None
                if name and category and amount and description and frequency and start_date:
                    rules.append(RecurringRule(name=name, category=category, amount=amount, description=description, frequency=frequency, start_date=start_date, end_date=end_date, last_generated_date=last_generated))
    except Exception:
        return []
    return rules


def save_recurring_rules(rules: List[RecurringRule], filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    data = []
    for r in rules:
        data.append({
            'name': r.name,
            'category': r.category,
            'amount': r.amount,
            'description': r.description,
            'frequency': r.frequency,
            'start_date': r.start_date.strftime('%Y-%m-%d') if r.start_date else None,
            'end_date': r.end_date.strftime('%Y-%m-%d') if r.end_date else None,
            'last_generated_date': r.last_generated_date.strftime('%Y-%m-%d') if r.last_generated_date else None,
        })
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def generate_new_transaction_id(transactions: List[Transaction]) -> int:
    if not transactions:
        return 1
    return max(tx.id for tx in transactions) + 1


def parse_csv_content(content: str, categories: List[str]):
    """
    Parse CSV content string for import.
    Returns a tuple (valid_rows, errors) where valid_rows is a list of dicts
    with keys: date (date), amount (float), category, description, notes
    and errors is a list of dicts: {row: int, errors: [messages]}
    Expected columns: date, amount, category, description, notes(optional)
    Date format: YYYY-MM-DD
    """
    valid = []
    errors = []
    if not content:
        return valid, errors
    try:
        # csv module expects a file-like, so splitlines and use DictReader
        lines = content.splitlines()
        reader = csv.DictReader(lines)
    except Exception as e:
        errors.append({'row': 0, 'errors': [f'Could not parse CSV: {e}']})
        return valid, errors

    for idx, row in enumerate(reader, start=2):
        # start=2 to account for header row as row 1
        row_errors = []
        if not row:
            continue
        date_s = (row.get('date') or '').strip()
        amount_s = (row.get('amount') or '').strip()
        category = (row.get('category') or '').strip()
        description = (row.get('description') or '').strip()
        notes = (row.get('notes') or '').strip()

        # date
        date_val = parse_date(date_s)
        if date_val is None:
            row_errors.append('Invalid or missing date (YYYY-MM-DD).')
        else:
            if date_val > datetime.date.today():
                row_errors.append('Date cannot be in the future.')

        # amount
        try:
            amount_val = float(amount_s)
            if amount_val < 0:
                row_errors.append('Amount must be non-negative.')
        except Exception:
            amount_val = None
            row_errors.append('Invalid or missing amount.')

        # category
        if not category:
            row_errors.append('Missing category.')
        elif category not in categories:
            row_errors.append('Unknown category.')

        # description
        if not description:
            row_errors.append('Description is required.')

        if row_errors:
            errors.append({'row': idx, 'errors': row_errors})
        else:
            valid.append({'date': date_val, 'amount': amount_val, 'category': category, 'description': description, 'notes': notes})

    return valid, errors
