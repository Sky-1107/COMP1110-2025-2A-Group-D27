# Personal Budget and Spending Assistant

A Flask-based web app for logging and summarizing expenditure, checking budget rules, and surfacing rule-based alerts. Includes transaction editing/deletion, charts, export to CSV/PDF, and automatic recurring transactions. Use server-side rendering (HTML + Jinja2, minimal JavaScript for charts) and store all data in files (`CSV`/`JSON`).

CSV Import
----------

The app supports importing transactions from a CSV file via the Manage Transactions page. Required columns:

- `date` (YYYY-MM-DD)
- `amount` (numeric, non-negative)
- `category` (must match an existing category)
- `description` (text)
- `notes` (optional)

Example CSV:

date,amount,category,description,notes
2025-04-01,12.50,Food,Coffee,Late afternoon
2025-04-02,45.00,Transport,Taxi,

The importer validates each row independently: valid rows are imported, invalid rows are rejected with per-row error messages.
