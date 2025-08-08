import pandas as pd
import pytz
import json
import os
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from config import CSV_PATH, DUPLICATE_TIME_SECONDS
import database

# ---------------- Vaildating Parameters ----------------
def validate_date(date_str):
    """Vaildating Date Format YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except (ValueError, TypeError):
        return False

def validate_timezone(tz_str):
    """Vaildating Timezone"""
    if not tz_str:
        return True
    try:
        pytz.timezone(tz_str)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False

def safe_string(value):
    """Safe String Conversion"""
    #  Check if the value is None or NaN
    if pd.isna(value) or value is None:
        return ''
    return str(value).strip()  

# ---------------- Time Processing ----------------
def parse_timestamp(timestamp_str, timezone_str=None, dst_check=False):
    """
    Analyze the timestamp (UTC time, list of issues)
    """
    issues = []
    timestamp_str = safe_string(timestamp_str)
    timezone_str = safe_string(timezone_str)
    
    # Assuming UTC if no timezone is provided
    if not timezone_str:
        issues.append('missing_timezone')

    if not timestamp_str:
        return None, ['empty_timestamp']
    
    try:
        # Processing UTC Tag
        if timestamp_str.endswith('Z'):
            dt = date_parser.parse(timestamp_str.replace('Z', '+00:00'))
            return dt.astimezone(pytz.UTC), issues
        
        # Analyze timestamp
        dt = date_parser.parse(timestamp_str)
        
        # Process timezone if provided
        if timezone_str:
            try:
                tz = pytz.timezone(timezone_str)
                try:
                    dt_localized = tz.localize(dt,is_dst=None)
                except pytz.exceptions.NonExistentTimeError:
                    dt_localized = tz.localize(dt)
                except pytz.exceptions.AmbiguousTimeError:
                    dt_localized = tz.localize(dt, is_dst=dst_check)
                
                return dt_localized.astimezone(pytz.UTC), issues
                
            except pytz.exceptions.UnknownTimeZoneError:
                issues.append('invalid_timezone')
        
        utc_dt = pytz.UTC.localize(dt) if dt.tzinfo is None else dt.astimezone(pytz.UTC)
        return utc_dt, issues
        
    except (ValueError, TypeError):
        return None, ['invalid_date_format']

def convert_timezone(utc_dt, target_timezone):
    """Conversion of UTC to Target Timezone"""
    if not target_timezone or target_timezone == 'UTC':
        return utc_dt
    
    try:
        tz = pytz.timezone(target_timezone)
        return utc_dt.astimezone(tz)
    except pytz.exceptions.UnknownTimeZoneError:
        return utc_dt

def get_period_bounds(period_str):
    """Obtaining the period between Start Date and End Date (YYYY-MM -> YYYY-MM-DD)"""
    period_date = datetime.strptime(period_str, '%Y-%m')
    start_date = period_date.strftime('%Y-%m-01')
    
    # Calculate end date as the last day of the month
    next_month = period_date.replace(day=28) + timedelta(days=4)
    end_date = (next_month.replace(day=1) - timedelta(days=1)).strftime('%Y-%m-%d')
    
    return start_date, end_date

# ---------------- Data Handling ----------------
def is_duplicate(new_record, existing_records, new_dt):
    """Checking for duplicate transactions"""
    if not new_dt:
        return False
        
    for existing in existing_records:
        if (existing['customer_id'] == new_record['customer_id'] and
            existing['amount'] == new_record['amount'] and
            existing['processed_timestamp']):
            
            existing_dt = datetime.fromisoformat(existing['processed_timestamp'].replace('Z', '+00:00'))
            time_diff = abs((new_dt - existing_dt).total_seconds())
            
            if time_diff <= DUPLICATE_TIME_SECONDS:
                return True
    
    return False

def process_csv_data():
    """Processing CSV Data"""
    print("Start processing CSV Data...")
    if not os.path.exists(CSV_PATH):
        print(f"CSV file not found: {CSV_PATH}")
        return
    
    # Read CSV
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} rows of raw data from CSV")
    
    # Cleaning Existing Transactions
    database.clear_transactions()
    
    # Statistics for information
    stats = {
        'total_processed': 0,
        'invalid_dates': 0,
        'missing_timezones': 0,
        'duplicate_transactions': 0,
    }
    
    processed_records = []
    
    # Handling each row in the DataFrame
    for _, row in df.iterrows():
        stats['total_processed'] += 1
        dst_check = False

        # Validating required fields
        if 'dst' in row['transaction_id'].lower():
            dst_check = True

        # Analyze timestamp
        parsed_dt, issues = parse_timestamp(
            row['timestamp'], 
            row.get('timezone', ''),
            dst_check
        )
        
        # Skip invalid records
        if 'invalid_date_format' in issues:
            stats['invalid_dates'] += 1
            continue
        if 'missing_timezone' in issues:
            stats['missing_timezones'] += 1
        
        # Creating Processed Record
        record = {
            'transaction_id': str(row['transaction_id']),
            'customer_id': str(row['customer_id']),
            'amount': float(row['amount']),
            'currency': str(row['currency']),
            'original_timestamp': str(row['timestamp']),
            'original_timezone': safe_string(row.get('timezone', '')),
            'processed_timestamp': parsed_dt.isoformat() if parsed_dt else None,
            'processed_timezone': 'UTC',
            'status': str(row['status']),
            'product_category': str(row['product_category']),
            'data_quality_flags': json.dumps({'issues': issues}),
            'created_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Checking for duplicates
        if is_duplicate(record, processed_records, parsed_dt):
            stats['duplicate_transactions'] += 1
            continue
        
        processed_records.append(record)
    # Inserting processed records into the database
    database.insert_many_transactions(processed_records)
    
    # Updating data quality summary
    database.update_quality_summary(stats)
    
    print(f"Process Completed：{len(processed_records)} rows of vaild transactions")
    print(f"Skip Invaild Date：{stats['invalid_dates']} rows")
    print(f"Skip Duplicated Records：{stats['duplicate_transactions']} rows")
    print(f"Missing Timezone：{stats['missing_timezones']} rows")