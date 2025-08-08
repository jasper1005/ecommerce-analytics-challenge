# Importing necessary modules
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import logging
from datetime import datetime

# Importing self-defined modules
import config
import database
import processors

# Setting up Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ---------------- API Routing ----------------

@app.route('/api/sales/daily', methods=['GET'])
def daily_sales():
    """Daily sales data"""
    try:
        # obtaining query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        timezone_str = request.args.get('timezone', 'UTC')
        
        # validating parameters
        if not start_date or not end_date:
            return jsonify({
                'error': 'Missing parameters',
                'message': 'Required start_date and end_date ( In YYYY-MM-DD format)',
                'code': 400,
                'timestamp':datetime.utcnow().isoformat() + 'Z'
            }), 400
        
        if not processors.validate_date(start_date) or not processors.validate_date(end_date):
            return jsonify({
                'error': 'Invalid date format',
                'message': 'start_date must be in YYYY-MM-DD format',
                'code': 400,
                'timestamp':datetime.utcnow().isoformat() + 'Z'
            }), 400
        
        if not processors.validate_timezone(timezone_str):
            return jsonify({
                'error': 'Timezone invalid',
                'message': 'Please provide a valid timezone name',
                'code': 400,
                'timestamp':datetime.utcnow().isoformat() + 'Z'
            }), 400
        
        # Querying the database
        conn = database.get_connection()
        query = '''
            SELECT processed_timestamp, amount
            FROM transactions
            WHERE processed_timestamp IS NOT NULL
            AND status = 'completed'
            AND DATE(processed_timestamp) BETWEEN ? AND ?
            ORDER BY processed_timestamp
        '''
        
        df = pd.read_sql_query(query, conn, params=[start_date, end_date])
        conn.close()
        
        if df.empty:
            return jsonify({
                'data': [],
                'timezone': timezone_str,
                'period': f"{start_date} To {end_date}",
                'summary': {'total_sales': 0, 'total_transactions': 0, 'average_daily_sales': 0}
            })
        
        # Processing daily sales data
        df['processed_timestamp'] = pd.to_datetime(df['processed_timestamp'])
        df['target_date'] = df['processed_timestamp'].apply(
            lambda x: processors.convert_timezone(x, timezone_str).date()
        )
        
        # Grouping by date and calculating sales
        grouped = df.groupby('target_date').agg({
            'amount': ['sum', 'count', 'mean']
        }).round(2)
        
        daily_data = []
        for date, row in grouped.iterrows():
            daily_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'total_sales': float(row[('amount', 'sum')]),
                'transaction_count': int(row[('amount', 'count')]),
                'average_order_value': float(row[('amount', 'mean')])
            })
        
        # Sorting the data by date
        total_sales = sum(day['total_sales'] for day in daily_data)
        total_transactions = sum(day['transaction_count'] for day in daily_data)
        avg_daily_sales = total_sales / len(daily_data) if daily_data else 0
        
        return jsonify({
            'data': daily_data,
            'timezone': timezone_str,
            'period': f"{start_date} To {end_date}",
            'summary': {
                'total_sales': round(total_sales, 2),
                'total_transactions': total_transactions,
                'average_daily_sales': round(avg_daily_sales, 2)
            }
        })
        
    except Exception as e:
        logger.error(f"Daily Sales Error: {e}")
        return jsonify({'error': 'Server Internal Error'}), 500

@app.route('/api/sales/hourly', methods=['GET'])
def hourly_sales():
    """Hourly sales data"""
    try:
        date_str = request.args.get('date')
        timezone_str = request.args.get('timezone', 'UTC')
        
        if not date_str:
            return jsonify({
                'error': 'Missing Parameters',
                'message': 'Required date parameter (YYYY-MM-DD Format)',
                'code': 400,
                'timestamp':datetime.utcnow().isoformat() + 'Z'
            }), 400
        
        if not processors.validate_date(date_str) or not processors.validate_timezone(timezone_str):
            return jsonify({'error': 'Parameter Format Error'}), 400
        
        # Querying the database
        conn = database.get_connection()
        query = '''
            SELECT processed_timestamp, amount
            FROM transactions
            WHERE processed_timestamp IS NOT NULL
            AND status = 'completed'
            AND DATE(processed_timestamp) = ?
        '''
        
        df = pd.read_sql_query(query, conn, params=[date_str])
        conn.close()
        
        if df.empty:
            return jsonify({'data': [], 'timezone': timezone_str, 'date': date_str})
        
        # Processing hourly sales data
        df['processed_timestamp'] = pd.to_datetime(df['processed_timestamp'])
        df['target_hour'] = df['processed_timestamp'].apply(
            lambda x: processors.convert_timezone(x, timezone_str).replace(
                minute=0, second=0, microsecond=0
            )
        )
        
        grouped = df.groupby('target_hour').agg({
            'amount': ['sum', 'count']
        }).round(2)
        
        hourly_data = []
        for hour, row in grouped.iterrows():
            hourly_data.append({
                'hour': hour.strftime('%Y-%m-%d %H:%M:%S'),
                'total_sales': float(row[('amount', 'sum')]),
                'transaction_count': int(row[('amount', 'count')])
            })
        
        hourly_data.sort(key=lambda x: x['hour'])
        
        return jsonify({
            'data': hourly_data,
            'timezone': timezone_str,
            'date': date_str
        })
        
    except Exception as e:
        logger.error(f"Hourly Sales API Error: {e}")
        return jsonify({'error': 'Server Internal Error'}), 500

@app.route('/api/sales/compare', methods=['GET'])
def compare_periods():
    """Compararison of sales between two periods"""
    try:
        period1 = request.args.get('period1')  # YYYY-MM
        period2 = request.args.get('period2')  # YYYY-MM
        
        if not period1 or not period2:
            return jsonify({
                'error': 'Missing Parameters',
                'message': 'Required period1 and period2 (YYYY-MM Format)'
            }), 400
        
        # validating period format
        try:
            p1_start, p1_end = processors.get_period_bounds(period1)
            p2_start, p2_end = processors.get_period_bounds(period2)
        except ValueError:
            return jsonify({'error': 'Period Format Invaild，should in YYYY-MM'}), 400
        
        # Quering the data between two periods
        conn = database.get_connection()
        query = '''
            SELECT 
                CASE 
                    WHEN DATE(processed_timestamp) BETWEEN ? AND ? THEN 'period1'
                    WHEN DATE(processed_timestamp) BETWEEN ? AND ? THEN 'period2'
                END as period,
                SUM(amount) as total_sales,
                COUNT(*) as transaction_count
            FROM transactions
            WHERE processed_timestamp IS NOT NULL
            AND status = 'completed'
            AND (DATE(processed_timestamp) BETWEEN ? AND ? 
                 OR DATE(processed_timestamp) BETWEEN ? AND ?)
            GROUP BY period
        '''
        
        results = conn.execute(query, [
            p1_start, p1_end, p2_start, p2_end,
            p1_start, p1_end, p2_start, p2_end
        ]).fetchall()
        conn.close()
        
        # Processing results
        period_data = {}
        for row in results:
            period_data[row[0]] = {
                'total_sales': float(row[1]),
                'transaction_count': int(row[2])
            }
        
        # Calculating growth percentages
        p1_sales = period_data.get('period1', {}).get('total_sales', 0)
        p2_sales = period_data.get('period2', {}).get('total_sales', 0)
        p1_count = period_data.get('period1', {}).get('transaction_count', 0)
        p2_count = period_data.get('period2', {}).get('transaction_count', 0)
        
        sales_change = ((p2_sales - p1_sales) / p1_sales * 100) if p1_sales > 0 else 0
        count_change = ((p2_count - p1_count) / p1_count * 100) if p1_count > 0 else 0
        
        return jsonify({
            'period1': {
                'start': p1_start, 'end': p1_end,
                'total_sales': p1_sales, 'transaction_count': p1_count
            },
            'period2': {
                'start': p2_start, 'end': p2_end,
                'total_sales': p2_sales, 'transaction_count': p2_count
            },
            'growth': {
                'sales_change_percent': round(sales_change, 2),
                'transaction_change_percent': round(count_change, 2)
            }
        })
        
    except Exception as e:
        logger.error(f"Comparison of sales between two periods Error: {e}")
        return jsonify({'error': 'Server Internal Error'}), 500

@app.route('/api/data-quality', methods=['GET'])
def data_quality_report():
    """Data quality report"""
    try:
        quality_data, processed_count = database.get_quality_summary()
        
        if not quality_data:
            return jsonify({
                'error': 'No data quality summary found',
                'message': 'Please ensure data has been processed'
            }), 404
        
        # quality_data = [total, invalid_dates, missing_timezones, duplicate_txns, out_of_order]
        keys = ['invalid_dates', 'missing_timezones', 'duplicate_transactions', 'out_of_order_records']
        counts = dict(zip(keys, quality_data[1:5]))
        issues_found = {k: int(v) for k, v in counts.items() if v and int(v) != 0}

        resolutions = {
            'invalid_dates': "Excluded from analysis",
            'missing_timezones': "Assumed UTC based on server logs",
            'duplicate_transactions': "Kept latest timestamp version",
            'out_of_order_records': "Reordered by actual transaction time"
        }
        resolution_summary = {k: resolutions[k] for k in issues_found.keys()}

        return jsonify({
            'total_records': quality_data[0],
            'processed_records': processed_count,
            'issues_found': {
                'invalid_dates': quality_data[1],
                'missing_timezones': quality_data[2],
                'duplicate_transactions': quality_data[3],
                'out_of_order_records': quality_data[4]
            },
            'resolution_summary': resolution_summary
        })
        
    except Exception as e:
        logger.error(f"Data Quality API Error: {e}")
        return jsonify({'error': 'Server Internal Error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'Normal',
        'timestamp': datetime.utcnow().isoformat(),
        'database_available': database.database_exists()
    })

# ---------------- Error Handling ----------------

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Page Not Found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Server Internal Error'}), 500

# ---------------- Main Application ----------------

if __name__ == '__main__':
    # Check if database exists
    if not database.database_exists():
        logger.error("Cannot find database file, please run 'python setup_db.py' first")
        exit(1)
    
    # Check if there are processed transactions
    if database.get_transaction_count() == 0:
        logger.info("No processed transactions found, starting to process CSV...")
        processors.process_csv_data()

    logger.info("Starting E-commerce Analytics API")
    logger.info(f"API Address: http://{config.HOST}:{config.PORT}")
    logger.info(f"Health Check: http://{config.HOST}:{config.PORT}/health")
    
    app.json.sort_keys = False
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)
    