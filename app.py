from datetime import date, datetime
from flask import Flask, flash, redirect, render_template, request, url_for
from os import makedirs, path
from typing import Any, List

DATA_DIR = 'data'
TRANSACTIONS_FILE = path.join(DATA_DIR, 'transactions.csv')
BUDGET_RULES_FILE = path.join(DATA_DIR, 'budget_rules.json')
CATEGORIES_FILE = path.join(DATA_DIR, 'categories.json')
RECURRING_RULES_FILE = path.join(DATA_DIR, 'recurring_rules.json')

app = Flask(__name__)
app.secret_key = 'change_me_please_for_production'

def ensure_data_files():
    '''
    Create the data files if they do not exist.
    '''

    # Create the target directory if it does not exist.
    makedirs(DATA_DIR, exist_ok=True)

    # Functions are to be imported from `data_loader.py`.
    if not path.exists(CATEGORIES_FILE):
        # Expected: fill in categories.json with default categories
        pass

    if not path.exists(BUDGET_RULES_FILE):
        # Expected: fill in budget_rules.json with default rules
        pass

    if not path.exists(TRANSACTIONS_FILE):
        # Expected: fill in transactions.csv with header row (no transaction yet)
        pass

    if not path.exists(RECURRING_RULES_FILE):
        # Expected: create recurring_rules.json (default: no recurring rules)
        pass

@app.route('/')
def index():
    ensure_data_files()
    categories: List[str]
    rules: List[Any]        # dataclass to be defined in budget_core.py
    transactions: List[Any] # dataclass to be defined in budget_core.py
    
    # To be adjusted with respect to the content of index.html

    return render_template('index.html')

@app.route('/add', methods=['GET'])
def add_transaction_form():
    ensure_data_files()
    categories: List[str]
    return render_template('add_transaction.html', categories=categories)

@app.route('/add', methods=['POST'])
def add_transaction():
    ensure_data_files()
    categories: List[str]
    date_input = request.form.get('date', '').strip()
    amount_input = request.form.get('amount', '').strip()
    category = request.form.get('category', '').strip()
    description = request.form.get('description', '').strip()
    notes = request.form.get('notes', '').strip()

    errors = []

    # Date validation
    try:
        date_val = datetime.strptime(date_input, '%Y-%m-%d').date()
        if date_val > date.today():
            errors.append('Date cannot be in the future.')
    except ValueError:
        errors.append('Invalid date format. Use YYYY-MM-DD.')

    # Amount validation
    # (Is it possible to prohibit the input of negative sign before the POST?)
    try:
        amount_val = float(amount_input)
        if amount_val < 0:
            errors.append('Amount must be non-negative.')
    except ValueError:
        errors.append('Invalid amount.')

    # Category validation
    if category not in categories:
        errors.append('Category must be one of the allowed categories.')

    # Description validation
    if not description:
        errors.append('Description is required.')

    if errors:
        for err in errors:
            # The function flash() require a secret key
            flash(err, 'error')
        return render_template('add_transaction.html', categories=categories, prev=request.form)

    transactions: List[Any]
    new_tx: Any             # dataclass to be defined in budget_core.py
    transactions.append(new_tx)

    try:
        # Expected: function_to_save_transaction(transactions, TRANSACTIONS_FILE)
        flash('Transaction added successfully.', 'success')
    except Exception as e:
        flash(f'Could not save transaction: {e}', 'error')

    return redirect(url_for('index'))

@app.route('/settings', methods=['GET'])
def settings():
    ensure_data_files()
    categories: List[str]
    rules: List[Any]
    recurring_rules: List[Any]
    return render_template('settings.html', categories=categories, rules=rules, recurring_rules=recurring_rules)

if __name__ == '__main__':
    app.run(debug = True)