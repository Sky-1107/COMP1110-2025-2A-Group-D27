import os
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from data_loader import load_transactions, save_transactions, load_budget_rules, save_budget_rules, load_categories, save_categories, load_recurring_rules, save_recurring_rules, generate_new_transaction_id, parse_csv_content, validate_csv_file_upload
from budget_core import DEFAULT_CATEGORIES, Transaction, BudgetRule, RecurringRule, validate_transaction, spending_by_category, spending_by_period, top_categories, spending_trend, check_alerts, monthly_spending_trend, validate_categories
from recurring_handler import process_recurring_transactions
from export_utils import export_csv, export_pdf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

TRANSACTIONS_FILE = os.path.join(DATA_DIR, 'transactions.csv')
BUDGET_RULES_FILE = os.path.join(DATA_DIR, 'budget_rules.json')
CATEGORIES_FILE = os.path.join(DATA_DIR, 'categories.json')
RECURRING_RULES_FILE = os.path.join(DATA_DIR, 'recurring_rules.json')

app = Flask(__name__)
app.secret_key = 'change_me_please_for_production'
app.jinja_env.globals.update(zip=zip)

def ensure_data_files():
    '''
    Create the data files if they do not exist.
    '''

    # Create the target directory if it does not exist.
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(CATEGORIES_FILE):
        save_categories(DEFAULT_CATEGORIES, CATEGORIES_FILE)

    if not os.path.exists(BUDGET_RULES_FILE):
        default_rules = [
            BudgetRule(category='Food', period='daily', threshold=50.0, alert_type='exceed'),
            BudgetRule(category='Transport', period='weekly', threshold=150.0, alert_type='exceed'),
            BudgetRule(category='Shopping', period='monthly', threshold=500.0, alert_type='exceed'),
            BudgetRule(category='Food', period='percentage', threshold=30.0, alert_type='percentage'),
        ]
        save_budget_rules(default_rules, BUDGET_RULES_FILE)

    if not os.path.exists(TRANSACTIONS_FILE):
        save_transactions([], TRANSACTIONS_FILE)

    if not os.path.exists(RECURRING_RULES_FILE):
        save_recurring_rules([], RECURRING_RULES_FILE)


def add_recurring_transactions(transactions):
    new_recurring = process_recurring_transactions(DATA_DIR, transactions)
    if new_recurring:
        transactions.extend(new_recurring)
        save_transactions(transactions, TRANSACTIONS_FILE)
        flash(f'Added {len(new_recurring)} recurring transactions.', 'info')
    return transactions


@app.route('/')
def index():
    ensure_data_files()
    categories = load_categories(CATEGORIES_FILE)
    rules = load_budget_rules(BUDGET_RULES_FILE)
    transactions = load_transactions(TRANSACTIONS_FILE)
    
    # Process recurring transactions
    transactions = add_recurring_transactions(transactions)
    
    stats_total = sum(tx.amount for tx in transactions)
    stats_by_category = spending_by_category(transactions)
    top_cats = top_categories(transactions, n=5)
    trend = spending_trend(transactions, n=7)
    alerts = check_alerts(transactions, rules, categories)
    recent = sorted(transactions, key=lambda tx: tx.date, reverse=True)[:10]
    return render_template('index.html', total=stats_total, by_category=stats_by_category, top_categories=top_cats, trend=trend, alerts=alerts, recent=recent)


@app.route('/add', methods=['GET'])
def add_transaction_form():
    ensure_data_files()
    categories = load_categories(CATEGORIES_FILE)
    return render_template('add_transaction.html', categories=categories)


@app.route('/add', methods=['POST'])
def add_transaction():
    ensure_data_files()
    categories = load_categories(CATEGORIES_FILE)
    date_input = request.form.get('date', '').strip()
    amount_input = request.form.get('amount', '').strip()
    category = request.form.get('category', '').strip()
    description = request.form.get('description', '').strip()

    errors = validate_transaction(date_input, amount_input, category, categories, description)
    if errors:
        for err in errors:
            flash(err, 'error')
        return render_template('add_transaction.html', categories=categories, prev=request.form)

    transactions = load_transactions(TRANSACTIONS_FILE)
    new_id = generate_new_transaction_id(transactions)
    new_tx = Transaction(
        date = datetime.datetime.strptime(date_input, '%Y-%m-%d').date(),
        amount = float(amount_input),
        category = category,
        description = description,
        notes = request.form.get('notes', '').strip(),
        id = new_id
    )
    transactions.append(new_tx)

    try:
        save_transactions(transactions, TRANSACTIONS_FILE)
        flash('Transaction added successfully.', 'success')
    except Exception as e:
        flash(f'Could not save transaction: {e}', 'error')

    return redirect(url_for('index'))


@app.route('/edit/<int:txn_id>', methods=['GET'])
def edit_transaction_form(txn_id):
    ensure_data_files()
    categories = load_categories(CATEGORIES_FILE)
    transactions = load_transactions(TRANSACTIONS_FILE)
    tx = next((t for t in transactions if t.id == txn_id), None)
    if not tx:
        flash('Transaction not found.', 'error')
        return redirect(url_for('manage_transactions'))
    return render_template('edit_transaction.html', transaction=tx, categories=categories)


@app.route('/edit/<int:txn_id>', methods=['POST'])
def edit_transaction(txn_id):
    ensure_data_files()
    categories = load_categories(CATEGORIES_FILE)
    transactions = load_transactions(TRANSACTIONS_FILE)
    tx = next((t for t in transactions if t.id == txn_id), None)
    if not tx:
        flash('Transaction not found.', 'error')
        return redirect(url_for('manage_transactions'))
    
    date_input = request.form.get('date', '').strip()
    amount_input = request.form.get('amount', '').strip()
    category = request.form.get('category', '').strip()
    description = request.form.get('description', '').strip()

    errors = validate_transaction(date_input, amount_input, category, categories, description)
    if errors:
        for err in errors:
            flash(err, 'error')
        return render_template('edit_transaction.html', transaction=tx, categories=categories, prev=request.form)

    # Update transaction
    tx.date = datetime.datetime.strptime(date_input, '%Y-%m-%d').date()
    tx.amount = float(amount_input)
    tx.category = category
    tx.description = description
    tx.notes = request.form.get('notes', '').strip()

    try:
        save_transactions(transactions, TRANSACTIONS_FILE)
        flash('Transaction updated successfully.', 'success')
    except Exception as e:
        flash(f'Could not save transaction: {e}', 'error')

    return redirect(url_for('manage_transactions'))


@app.route('/delete/<int:txn_id>', methods=['GET'])
def delete_transaction(txn_id):
    ensure_data_files()
    transactions = load_transactions(TRANSACTIONS_FILE)
    transactions = [t for t in transactions if t.id != txn_id]
    try:
        save_transactions(transactions, TRANSACTIONS_FILE)
        flash('Transaction deleted successfully.', 'success')
    except Exception as e:
        flash(f'Could not delete transaction: {e}', 'error')
    return redirect(url_for('manage_transactions'))


@app.route('/transactions', methods=['GET'])
def manage_transactions():
    ensure_data_files()
    categories = load_categories(CATEGORIES_FILE)
    transactions = load_transactions(TRANSACTIONS_FILE)
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    filter_category = request.args.get('category', '').strip()

    filtered = transactions
    if start_date:
        try:
            sd = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            filtered = [t for t in filtered if t.date >= sd]
        except ValueError:
            flash('Invalid start date filter', 'error')
    if end_date:
        try:
            ed = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            filtered = [t for t in filtered if t.date <= ed]
        except ValueError:
            flash('Invalid end date filter', 'error')

    if filter_category:
        filtered = [t for t in filtered if t.category == filter_category]

    filtered = sorted(filtered, key=lambda tx: tx.date, reverse=True)
    
    # Get imported IDs from session and clear them
    imported_ids = session.pop('imported_ids', [])
    
    return render_template('manage_transactions.html', transactions=filtered, categories=categories, filters={'start_date': start_date, 'end_date': end_date, 'category': filter_category}, imported_ids=imported_ids)


@app.route('/transactions/import', methods=['POST'])
def import_transactions():
    ensure_data_files()
    # file field expected to be named 'csv_file'
    uploaded = request.files.get('csv_file')
    if not uploaded:
        flash('No file uploaded.', 'error')
        return redirect(url_for('manage_transactions'))

    filename = uploaded.filename or ''
    if not filename.lower().endswith('.csv'):
        flash('Only CSV files are accepted. Please rename or export your file with a .csv extension.', 'error')
        return redirect(url_for('manage_transactions'))

    # Read file bytes
    try:
        raw = uploaded.read()
    except Exception as e:
        flash(f'Could not read uploaded file: {str(e)}', 'error')
        return redirect(url_for('manage_transactions'))

    # Validate file content (encoding, binary type, size, etc.)
    validation_error, decoded_content = validate_csv_file_upload(raw)
    if validation_error:
        flash(validation_error, 'error')
        return redirect(url_for('manage_transactions'))
    
    content = decoded_content
    
    # Parse CSV content
    categories = load_categories(CATEGORIES_FILE)
    valid_rows, row_errors = parse_csv_content(content, categories)

    imported = 0
    imported_ids = []
    transactions = load_transactions(TRANSACTIONS_FILE)
    for row in valid_rows:
        new_id = generate_new_transaction_id(transactions)
        tx = Transaction(date=row['date'], amount=row['amount'], category=row['category'], description=row['description'], notes=row.get('notes', ''), id=new_id)
        transactions.append(tx)
        imported_ids.append(new_id)
        imported += 1

    try:
        if imported:
            save_transactions(transactions, TRANSACTIONS_FILE)
    except Exception as e:
        flash(f'Could not save imported transactions: {e}', 'error')
        return redirect(url_for('manage_transactions'))

    rejected = len(row_errors)
    flash(f'Imported {imported} transactions; {rejected} rows rejected.', 'info')

    # show up to 5 representative error messages
    for err in row_errors[:5]:
        flash(f"Row {err.get('row')}: {'; '.join(err.get('errors', []))}", 'error')

    # Store imported IDs in session for highlighting
    session['imported_ids'] = imported_ids
    session.modified = True

    return redirect(url_for('manage_transactions'))


@app.route('/summaries', methods=['GET'])
def summaries():
    ensure_data_files()
    transactions = load_transactions(TRANSACTIONS_FILE)
    by_cat = spending_by_category(transactions)
    by_day = spending_by_period(transactions, 'daily')
    by_week = spending_by_period(transactions, 'weekly')
    by_month = spending_by_period(transactions, 'monthly')
    top_cats = top_categories(transactions, n=5)
    trend = spending_trend(transactions, n=30)
    months, monthly_values = monthly_spending_trend(transactions)
    return render_template('summaries.html', by_category=by_cat, by_day=by_day, by_week=by_week, by_month=by_month, top_categories=top_cats, trend=trend, months=months, monthly_values=monthly_values)


@app.route('/alerts', methods=['GET'])
def alerts_page():
    ensure_data_files()
    categories = load_categories(CATEGORIES_FILE)
    rules = load_budget_rules(BUDGET_RULES_FILE)
    transactions = load_transactions(TRANSACTIONS_FILE)
    alerts = check_alerts(transactions, rules, categories)
    return render_template('alerts.html', alerts=alerts)


@app.route('/settings', methods=['GET'])
def settings():
    ensure_data_files()
    categories = load_categories(CATEGORIES_FILE)
    rules = load_budget_rules(BUDGET_RULES_FILE)
    recurring_rules = load_recurring_rules(RECURRING_RULES_FILE)
    return render_template('settings.html', categories=categories, rules=rules, recurring_rules=recurring_rules)


@app.route('/settings', methods=['POST'])
def settings_save():
    ensure_data_files()
    categories_input = request.form.get('categories', '').strip()
    rules_input = request.form.get('rules', '').strip()
    recurring_input = request.form.get('recurring_rules', '').strip()

    if categories_input:
        categories = [c.strip() for c in categories_input.split(',') if c.strip()]
        if categories:
            if validate_categories(categories):
                save_categories(categories, CATEGORIES_FILE)
                flash('Categories updated', 'success')
            else:
                flash('No valid categories provided; ensure all category names are non-empty.', 'error')
        else:
            flash('No valid categories provided', 'error')

    # rules_text area (optional): each line category,period,threshold,alert_type
    if rules_input:
        new_rules = []
        rule_errors = []
        for line in rules_input.splitlines():
            parts = [p.strip() for p in line.split(',')]
            if len(parts) != 4:
                continue
            cat, period, thr, atype = parts
            try:
                thr_val = float(thr)
            except ValueError:
                continue
            try:
                new_rules.append(BudgetRule(category=cat, period=period, threshold=thr_val, alert_type=atype))
            except ValueError as e:
                rule_errors.append(f"Rule '{line}' skipped: {e}")
        if new_rules:
            save_budget_rules(new_rules, BUDGET_RULES_FILE)
            flash('Budget rules updated', 'success')
        else:
            flash('No valid budget rules parsed', 'error')
        # show up to 5 representative rule errors
        for err in rule_errors[:5]:
            flash(err, 'error')

    # recurring rules: each line name,category,amount,description,frequency,start_date,end_date
    if recurring_input:
        new_recurring = []
        recurring_errors = []
        for line in recurring_input.splitlines():
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 7:
                continue
            name, cat, amt, desc, freq, start, end = parts[:7]
            try:
                amt_val = float(amt)
                start_date = datetime.datetime.strptime(start, '%Y-%m-%d').date()
                end_date = datetime.datetime.strptime(end, '%Y-%m-%d').date() if end else None
            except ValueError:
                continue
            try:
                new_recurring.append(RecurringRule(name=name, category=cat, amount=amt_val, description=desc, frequency=freq, start_date=start_date, end_date=end_date))
            except ValueError as e:
                recurring_errors.append(f"Recurring '{line}' skipped: {e}")
        if new_recurring:
            # Save the recurring rules first
            save_recurring_rules(new_recurring, RECURRING_RULES_FILE)
            flash('Recurring rules updated', 'success')

            # Then process the recurring rules (including the new ones)
            transactions = load_transactions(TRANSACTIONS_FILE)
            add_recurring_transactions(transactions)
        else:
            flash('No valid recurring rules parsed', 'error')
        for err in recurring_errors[:5]:
            flash(err, 'error')

    return redirect(url_for('settings'))


@app.route('/export/csv', methods=['GET'])
def export_csv_route():
    ensure_data_files()
    transactions = load_transactions(TRANSACTIONS_FILE)
    return export_csv(transactions)


@app.route('/export/pdf', methods=['GET'])
def export_pdf_route():
    ensure_data_files()
    transactions = load_transactions(TRANSACTIONS_FILE)
    return export_pdf(transactions)


if __name__ == '__main__':
    ensure_data_files()
    app.run(debug = True, host = '0.0.0.0', port = 5001)