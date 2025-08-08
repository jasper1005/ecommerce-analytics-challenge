import sqlite3
import os
from config import DB_PATH

def get_connection():
    """Obtaining database path"""
    return sqlite3.connect(DB_PATH)

def database_exists():
    """Checking if the database file exists""" 
    return os.path.exists(DB_PATH)

def get_transaction_count():
    """Obtaining the count of processed transactions"""
    conn = get_connection()
    count = conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0]
    conn.close()
    return count

def clear_transactions():
    """Clearing existing transaction data"""
    conn = get_connection()
    conn.execute('DELETE FROM transactions')
    conn.commit()
    conn.close()

def insert_many_transactions(records):
    """Inserting multiple transaction records"""
    conn = get_connection()
    cursor = conn.cursor()
    
    for record in records:
        cursor.execute('''
            INSERT INTO transactions (
                transaction_id, customer_id, amount, currency,
                original_timestamp, original_timezone, processed_timestamp,
                processed_timezone, status, product_category, data_quality_flags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record['transaction_id'], record['customer_id'], record['amount'],
            record['currency'], record['original_timestamp'], record['original_timezone'],
            record['processed_timestamp'], record['processed_timezone'],
            record['status'], record['product_category'], record['data_quality_flags']
        ))
    
    conn.commit()
    conn.close()

def update_quality_summary(stats):
    """Updating data quality summary""" 
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM data_quality_summary')
    cursor.execute('''
        INSERT INTO data_quality_summary (
            total_records, invalid_dates, missing_timezones, 
            duplicate_transactions, out_of_order_records
        ) VALUES (?, ?, ?, ?, ?)
    ''', (
        stats['total_processed'],
        stats['invalid_dates'],
        stats['missing_timezones'],
        stats['duplicate_transactions'],
        0
    ))
    
    conn.commit()
    conn.close()

def get_quality_summary():
    """Retrieving data quality summary"""
    conn = get_connection()
    
    quality_data = conn.execute('''
        SELECT total_records, invalid_dates, missing_timezones, 
               duplicate_transactions, out_of_order_records
        FROM data_quality_summary
        ORDER BY last_updated DESC
        LIMIT 1
    ''').fetchone()
    
    processed_count = conn.execute('''
        SELECT COUNT(*) FROM transactions WHERE processed_timestamp IS NOT NULL
    ''').fetchone()[0]
    
    conn.close()
    return quality_data, processed_count