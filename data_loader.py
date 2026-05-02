import csv
import json
import os
import datetime
from typing import List, Tuple, Dict
from budget_core import DEFAULT_CATEGORIES, Transaction, BudgetRule, RecurringRule, validate_transaction


def parse_date(s: str):
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _detect_binary_file_type(file_bytes: bytes) -> str:
    """
    Detect common binary file types by their magic bytes (file signatures).
    Returns the detected file type name, or None if appears to be text.
    """

    if len(file_bytes) < 4:
        return None
    
    # Common binary file signatures
    signatures = {
        b'%PDF': 'PDF',
        b'PK\x03\x04': 'ZIP/Excel',  # ZIP format (used by modern Excel)
        b'\xd0\xcf\x11\xe0': 'OLE2/Word/Excel',  # OLE2 format (older Office)
        b'\xff\xd8\xff': 'JPEG Image',
        b'\x89PNG': 'PNG Image',
        b'GIF8': 'GIF Image',
        b'BM': 'BMP Image',
        b'RIFF': 'WAV/RIFF',
        b'\x1f\x8b': 'GZIP',
        b'7z\xbc\xaf': '7-Zip',
    }
    
    for sig_bytes, file_type in signatures.items():
        if file_bytes.startswith(sig_bytes):
            return file_type
    
    return None


def validate_csv_file_upload(file_bytes: bytes) -> Tuple[str | None, str | None]:
    """
    Validate an uploaded file for CSV compatibility.
    Returns (error_message, None) on error, or (None, decoded_content) on success.
    
    Checks for:
    1. Binary file signatures
    2. Valid UTF-8 encoding
    3. Reasonable file size
    """
    
    # Check file size (prevent huge uploads)
    if len(file_bytes) == 0:
        return "File is empty.", None
    
    if len(file_bytes) > 10_000_000:  # 10 MB limit
        return "File is too large (maximum 10 MB).", None
    
    # Check for binary file signatures
    detected_type = _detect_binary_file_type(file_bytes)
    if detected_type:
        return (
            f"Invalid file type detected ({detected_type}). "
            "Please upload a standard text-based CSV file, not a renamed PDF, Excel workbook, or other binary document.",
            None
        )
    
    # Try to decode with UTF-8
    try:
        # First try UTF-8 with BOM stripping
        content = file_bytes.decode('utf-8-sig')
        return None, content
    except UnicodeDecodeError:
        pass
    
    # Try common alternative encodings
    for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
        try:
            content = file_bytes.decode(encoding)
            # Basic sanity check: should have some comma separators and newlines
            if ',' in content or '\n' in content:
                return None, content
        except (UnicodeDecodeError, LookupError):
            continue
    
    # If all decoding attempts failed
    return (
        "Could not read file. Please ensure it is a valid CSV saved with UTF-8 encoding "
        "(standard Excel CSV export).",
        None
    )


def _validate_quote_structure(lines: List[str]) -> List[Dict]:
    """
    Validate that quotes are properly balanced in each line.
    Returns list of error dicts if issues found, empty list if valid.
    """

    errors = []
    
    for line_idx, line in enumerate(lines, start=1):
        # Skip empty rows and header row
        if not line or line_idx == 1:
            continue
        
        # Track quote state to detect unclosed quotes
        in_quotes = False
        i = 0
        while i < len(line):
            char = line[i]
            if char == '"':
                # Check if it's an escaped quote (double quote)
                if i + 1 < len(line) and line[i + 1] == '"':
                    i += 2  # Skip both quotes
                    continue
                else:
                    in_quotes = not in_quotes
            i += 1
        
        if in_quotes:
            errors.append({
                'row': line_idx,
                'errors': ['Unclosed quote detected. Row may have malformed quotes or may span multiple lines.']
            })
    
    return errors


def parse_csv_content(content: str, categories: List[str]) -> Tuple[List[Dict], List[Dict]]:
    """
    Parse CSV content string for import.
    Returns a tuple (valid_rows, errors) where valid_rows is a list of dicts
    with keys: date (date), amount (float), category, description, notes
    and errors is a list of dicts: {row: int, errors: [messages]}
    Expected columns: date, amount, category, description, notes(optional)
    Date format: YYYY-MM-DD
    """

    if not content:
        return [], []
    
    valid = []
    errors = []
    
    try:
        # Parse CSV with strict quote handling
        lines = content.splitlines()
        
        # Validate encoding and quote structure before parsing
        quote_validation_errors = _validate_quote_structure(lines)
        if quote_validation_errors:
            for error_info in quote_validation_errors:
                errors.append(error_info)
            return valid, errors
        
        # Use strict CSV reader
        reader = csv.DictReader(lines, quoting=csv.QUOTE_ALL, strict=True)
        
        # Get expected columns from header
        if not reader.fieldnames:
            errors.append({'row': 1, 'errors': ['CSV file is empty or has no header row.']})
            return valid, errors
        
        # 'notes' and 'id' are optional
        required_columns = {'date', 'amount', 'category', 'description'}
        
        # Check if all required columns are present
        if not required_columns.issubset(set(reader.fieldnames)):
            missing = required_columns - set(reader.fieldnames)
            errors.append({'row': 1, 'errors': [f'Missing required columns: {", ".join(sorted(missing))}']})
            return valid, errors
        
        expected_column_count = len(reader.fieldnames)
        
        for idx, row in enumerate(reader, start=2):
            if not row:
                continue

            row_errors = []
            
            # Validate column count (strict schema width)
            if len(row) != expected_column_count:
                row_errors.append(f'Expected {expected_column_count} columns, found {len(row)}.')
                errors.append({'row': idx, 'errors': row_errors})
                continue
            
            date_s = row.get('date', '').strip()
            amount_s = row.get('amount', '').strip()
            category = row.get('category', '').strip()
            description = row.get('description', '').strip()

            row_errors += validate_transaction(date_s, amount_s, category, categories, description)
            # Check for unclosed quotes or newlines in fields
            for field_name in ['date', 'amount', 'category', 'description', 'notes']:
                field_value = row.get(field_name, '')
                if field_value and '\n' in field_value:
                    row_errors.append(f'Field "{field_name}" contains illegal newline character (unclosed quote?)')

            if row_errors:
                errors.append({'row': idx, 'errors': row_errors})
            else:
                valid.append({
                    'date': datetime.datetime.strptime(date_s, '%Y-%m-%d').date(),
                    'amount': float(amount_s),
                    'category': category,
                    'description': description,
                    'notes': row.get('notes', '').strip(),
                    'id': row.get('id', '0')
                })

    except csv.Error as e:
        errors.append({'row': 0, 'errors': [f'CSV parsing error: {str(e)}']})
    except Exception as e:
        errors.append({'row': 0, 'errors': [f'Unexpected error parsing CSV: {str(e)}']})
    
    return valid, errors


def load_transactions(filepath: str) -> List[Transaction]:
    """Load and return transactions from CSV file with strict validation."""
    if not os.path.exists(filepath):
        return []  
    
    transactions = []
    try:
        with open(filepath, newline='', encoding='utf-8') as f:
            file_content = f.read()
    except (UnicodeDecodeError, IOError):
        return []
    
    # Parse CSV
    valid_rows, _ = parse_csv_content(file_content, DEFAULT_CATEGORIES)
    
    # Convert valid rows to Transaction objects
    for row in valid_rows:
        try:
            temp_id = row.get('id')
            id_val = int(temp_id) if temp_id else 0
        except (ValueError, TypeError):
            id_val = 0
        
        transactions.append(Transaction(
            date=row['date'],
            amount=row['amount'],
            category=row['category'],
            description=row['description'],
            notes=row.get('notes', ''),
            id=id_val
        ))
    
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
                return [temp for x in data if (temp := str(x).strip())]
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
                end_date_str = item.get('end_date')
                end_date = parse_date(end_date_str) if end_date_str else None
                last_generated_str = item.get('last_generated_date')
                last_generated = parse_date(last_generated_str) if last_generated_str else None
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
    """Generate a new unique transaction ID."""
    if not transactions:
        return 1
    return max(tx.id for tx in transactions) + 1