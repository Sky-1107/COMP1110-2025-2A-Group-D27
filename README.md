# Personal Budget and Spending Assistant

A Flask-based web app for logging and summarizing expenditure, checking budget rules, and surfacing rule-based alerts. Includes transaction editing/deletion, charts, export to CSV/PDF, and automatic recurring transactions. Uses server-side rendering (HTML + Jinja2, minimal JavaScript for charts) and stores all data in files (`CSV`/`JSON`).

## Features

- Add, edit, and delete transactions via forms
- Manage all transactions with filters and edit/delete buttons
- Summary statistics by category/day/week/month
- Trend reports (7/30 days, monthly line chart)
- Pie chart for category spending, line chart for monthly trends
- Rule-based alerts (daily, weekly, monthly, percentage, uncategorized, consecutive overspend)
- Import transactions from CSV
- Export transactions to CSV and PDF
- Automatic generation of recurring transactions (e.g., subscriptions)
- Settings to edit categories, budget rules, and recurring rules
- Case studies for testing scenarios

## Installation

1. Create a virtual environment (recommended):

```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python app.py
```

4. Open browser:

- `http://localhost:5000`

## Usage

- **Home**: Overview with total spending, recent transactions, alerts
- **Add Transaction**: Form to add new transactions
- **Manage Transaction**: List transactions with filters, edit/delete links
- **Summaries**: Tables and charts (pie for categories, line for monthly trend), export buttons
- **Alerts**: List of current budget alerts
- **Settings**: Edit categories, budget rules, recurring rules

Recurring transactions are generated automatically on app startup.

## File Structure

- `app.py`: Flask app routes and UI logic
- `budget_core.py`: Data models, summaries, alert logic
- `data_loader.py`: CSV/JSON file read/write helpers
- `export_utils.py`: Functions for CSV/PDF export
- `recurring_handler.py`: Logic for generating recurring transactions
- `test_data_generator.py`: Generate synthetic transactions for testing
- `requirements.txt`: Flask, reportlab dependencies
- `data/`: Sample data files
  - `transactions.csv` - transaction history (with id)
  - `budget_rules.json` - active budget rules
  - `categories.json` - allowed categories
  - `recurring_rules.json` - recurring transaction rules
- `templates/`: Jinja2 HTML templates
- `static/`: CSS files
- `case_studies/`: Sample inputs for case studies

## Client-side Libraries

- Chart.js (CDN): For pie and line charts
- Loaded via CDN, no installation needed

## Assumptions

- No user authentication
- File-based storage (CSV/JSON)
- Category must be in the allowed list in `/add` (uncategorized flagged by alerts)
- Dates in YYYY-MM-DD format
- Dates cannot be in future
- Amounts in HKD
- Amounts are non-negative
- Recurring transactions generated on app startup
- `templates/`: Jinja2 templates
- `static/style.css`: CSS styling
- `case_studies/`: 4 scenario data sets + docs

## Data formats

### `budget_rules.json`

JSON array of objects with:

- `category`: string
- `period`: `daily`, `weekly`, `monthly`, `percentage`
- `threshold`: number
- `alert_type`: `exceed` or `percentage`

### `categories.json`

JSON array of string categories.

### `recurring_rules.json`

JSON array of objects with:

- `name`: string
- `category`: string
- `amount`: number
- `description`: string
- `frequency`: `daily`, `weekly`, `monthly`, `yearly`
- `start_date`: strin (in the form `YYYY-MM-DD`)
- `end_date`: string (in the form `YYYY-MM-DD`) or `null`
- `last_generate_date`: string (in the form `YYYY-MM-DD`) or `null`

### `transactions.csv`

CSV header: `date,amount,category,description,notes`
Date format: `YYYY-MM-DD`, amounts in HK$, category string.

## Transaction Import from CSV

Transactions import from a CSV file is supported via the Manage Transactions page. Required columns:

- `date` (YYYY-MM-DD)
- `amount` (numeric, non-negative)
- `category` (must match an existing category)
- `description` (text)
- `notes` (optional)

Example CSV:

```csv
date,amount,category,description,notes
2025-04-01,12.50,Food,Coffee,Late afternoon
2025-04-02,45.00,Transport,Taxi,
```

## Case Studies

At `case_studies/`:

- `case1_*`: daily food budget
- `case2_*`: monthly transport budget
- `case3_*`: entertainment subscription creep
- `case4_*`: uncategorized warning

To run a case study:

1. Copy `case_studies/caseX_transactions.csv` -> `data/transactions.csv`
2. Copy `case_studies/caseX_recurring_rules.json` -> `data/recurring_rules.json`
3. Copy `case_studies/caseX_rules.json` -> `data/budget_rules.json`
4. Restart the app and review the alerts/summaries.

## Error handling

- Missing or malformed files load default content
- Invalid form input displays flash errors and re-renders form
- Invalid row in imported CSV triggers per-row error messages
- File write errors flash messages

## Testing

- run `python test_data_generator.py` to generate sample transactions in `data/transactions.csv`
