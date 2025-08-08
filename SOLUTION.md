# E-commerce Analytics API Solution

**Candidate:** Jasper Cheng (Ching Yat Cheng)  
**Time Spent:** 7 hours   
**Language/Framework:** Python/Flask

## Quick Start

```bash
# Setup instructions specific to your solution
pip install -r requirements.txt
python setup_db.py
python app/app.py

# Or for Node.js:
# npm install
# npm start
```

**API Base URL:** `http://localhost:5000`

## Implementation Decisions

### 1. Date/Time Handling Strategy

**Missing Timezones:**
- [*] Assumed UTC
- [ ] Inferred from business hours  
- [ ] Skipped records
- [ ] Other: ___________

**Rationale:** 
    Because current fields don’t reliably reveal origin timezone and the missing share is material, I standardize to UTC to avoid DST ambiguity and ensure reproducible analytics, while labeling and monitoring missing_timezone. If higher precision is needed, I will apply a business-hours–based inference to propose an inferred_timezone with confidence; low-confidence cases remain UTC.

**DST Transitions:**
- **Spring Forward:** 
    If pytz.NonExistentTimeError occurs, we treat it as non-DST (is_dst=False). 
    If the wall-clock time still doesn’t exist, we shift forward to the next valid instant (e.g., +1h) and tag the record.

                except pytz.exceptions.NonExistentTimeError:
                    dt_localized = tz.localize(dt)

- **Fall Back:**
    If pytz.AmbiguousTimeError occurs, we resolve to the DST occurrence (is_dst=True). 
    We pre-compute dst_check from transaction_id (e.g., IDs marked “DST”), but the resolution rule for overlap is to pick the DST side.

                except pytz.exceptions.AmbiguousTimeError:
                    dt_localized = tz.localize(dt, is_dst=True)

**Date Format Parsing:**
- Library used: 
    python-dateutil (dateutil.parser) for flexible string (Accept Multiple Date Time Format)
    datetime parsing; pytz for timezone/DST localization & conversions. (IANA time zone database)

- Fallback strategy:
    Empty timestamp → return None, issues ['empty_timestamp'].
    Unparseable date (ValueError/TypeError) → return None, issues ['invalid_date_format'].
    Unknown timezone → add invalid_timezone, treat datetime as UTC/naive and return UTC.
    Missing timezone → add missing_timezone, assume UTC.
    Naive datetimes → assume UTC (pytz.UTC.localize(dt)).

### 2. Data Quality Approach

**Duplicate Detection:**
- Strategy: 
    Exact match on (customer_id, amount) + rolling time-window on processed_timestamp (all times normalized to UTC). 
    Ignore records without timestamps
    compute absolute time diff; mark duplicate on first hit.

- Threshold: 
    60 seconds tolerance — due to multiple systems, batch arrivals

**Invalid Data:**
- Invalid dates: 
    Skip (return None; add invalid_date_format)
- Invalid timezones: [Assume UTC, error, etc.]
- Negative amounts: [Skip, error, abs value]

**Records processed:** 5005 out of 5006 total
**Records skipped:** 1

### 3. API Design Choices

**Timezone Parameter:**
- Default: UTC
- Validation:
    Uses pytz.timezone() to validate timezone names in processors.validate_timezone()

**Error Responses:**
- Format: 
    {
        "error": "Error Type",
        "message": "Detailed error message", 
        "code": 400,
        "timestamp": "2024-01-15T10:30:00Z"
    }

- HTTP Status Codes:
    400 Bad Request: Invalid parameters (dates, timezones, missing required fields)
    404 Not Found: No data quality summary found, endpoint not found
    500 Internal Server Error: Database errors, processing failures

**Performance Optimizations:**
- Database indexing: NA
- Query optimization: NA
- Caching: NA
- Proposed Optimizations:
    Pagination with Offset
    - Add Limit to retrict the number of records user can extract
    - Add offset for user to control the start point of their call

## API Documentation

### Endpoints Implemented

- [x] `GET /api/sales/daily`
- [x] `GET /api/sales/hourly` 
- [x] `GET /api/sales/compare`
- [x] `GET /api/data-quality`
- [ ] Additional endpoints: ___________

### Example Requests

```bash
# Daily sales
curl "http://localhost:5000/api/sales/daily?start_date=2024-01-01&end_date=2024-01-31&timezone=America/New_York"

# Hourly breakdown
curl "http://localhost:5000/api/sales/hourly?date=2024-01-15&timezone=UTC"

# Period comparison
curl "http://localhost:5000/api/sales/compare?period1=2024-01&period2=2024-02"

# Data quality report
curl "http://localhost:5000/api/data-quality"
```

## Testing

### How to Test

```bash
# Run unit tests (if implemented)
python -m pytest -vv -ra tests/test.py

# Manual testing
python test_script.py

# API testing
    # Check Health First: 
    curl "http://localhost:5000/health"
    # Check Basic Function
    curl "http://localhost:5000/api/sales/daily?start_date=2024-01-01&end_date=2024-01-31"
    # Run Unit Test
    python -m pytest -vv -ra tests/test.py
    # Try add more cases if need to:
    python test_script.py

```

### Edge Cases Handled

- [x] DST spring forward (non-existent time)
- [x] DST fall back (ambiguous time)  
- [x] Missing timezone information
- [x] Multiple date formats
- [x] Invalid dates
- [x] Duplicate transactions
- [x] Cross-timezone queries
- [ ] Other: ___________

### Known Issues

1. **Issue:** Memory consumption scales with dataset size
   **Impact:** Large date ranges (>6 months) may cause high memory usage as all matching records are loaded into pandas DataFrame
   **Workaround:** Use smaller date ranges (≤3 months) or restart application if memory issues occur

   **Issue:** No pagination support for large result sets
   **Impact:** API responses can become very large for extensive date ranges, potentially causing timeouts
   **Workaround:** Break large queries into smaller date ranges manually

   **Issue:** No input validation for amount ranges
   **Impact:** Extremely large amounts or negative values might affect calculations but are currently processed
   **Workaround:** Business logic assumes data has been pre-validated

2. **Performance:** 
    - Large datasets show noticeable response delays (2-5 seconds) due to client-side aggregation
    - No query result caching (create materialized view) - identical requests always hit the database
    - No connection pooling - each request creates new database connection

## Architecture

### Database Schema

[Describe any changes to the provided schema]

### Code Structure

```
my-solution/
├── app/
    ├── app.py                 # Main Flask application with API routes
    ├── config.py              # Configuration settings (DB paths, API settings)
    ├── database.py            # Database connection and operations
    ├── processors.py          # Data processing and date/time handling
└── tests/
    ├── test.py        # API tests
```

## Time Allocation

- **Data exploration/understanding:** 1 hours
- **Date/time handling logic:** 1.5 hours  
- **API implementation:** 2 hours
- **Testing and debugging:** 1.5 hours
- **Documentation:** 1 hours

**Total:** 7 hours

## Reflection

### What Went Well
- Comprehensive date/time handling: Successfully implemented robust timestamp parsing with python-dateutil that handles multiple formats (ISO, US, UK formats) and timezone conversions using pytz
- DST edge case handling: Properly addressed both spring forward (non-existent times) and fall back (ambiguous times) scenarios with configurable dst_check parameter
- Clean code architecture: Well-structured separation of concerns with database.py for data operations, processors.py for business logic, and config.py for settings
- Data quality tracking: Implemented comprehensive data quality monitoring with JSON flags tracking issues like missing timezones, invalid dates, and duplicates

### What Was Challenging  
- DST transitions complexity: Initially struggled with pytz.exceptions.NonExistentTimeError and AmbiguousTimeError during daylight saving transitions. 
    Solved by implementing dst_check parameter based on transaction_id string and using localize() with is_dst flag
- Timezone validation: Ensuring robust timezone name validation while providing meaningful error messages. 
    Used pytz.timezone() with proper exception handling

### What You'd Do Differently
- Implement pagination: Add LIMIT/OFFSET parameters to handle large date ranges without memory issues
- Query caching: Implement Redis or in-memory caching for frequently accessed data like daily summaries
- Async processing: Consider using FastAPI with async/await for better I/O performance
- More granular error handling: Distinguish between different types of date parsing errors for better debugging

### Production Considerations
- Monitoring and logging
    Set up alerting for high error rates or performance degradation
    Log data quality issues and processing statistics
- Authentication/authorization:
    Add role-based access control (RBAC) for different user types
    API key management for external integrations
    OAuth2 integration for enterprise SSO
- Rate limiting
    Different rate limits for different endpoints based on computational cost
    Graceful degradation when limits are exceeded
    Rate limit headers in API responses
- Database connection pooling
    Replace SQLite with PostgreSQL for production workloads
    Implement connection pooling with SQLAlchemy or asyncpg
- Error tracking
    Integrate Sentry or similar service for error monitoring
    Structured error logging with context information
- Deployment strategy
    Infrastructure as Code (Terraform/CloudFormation)
    Automated CI/CD pipeline with testing and security scans
    Health checks and readiness probes
    Horizontal auto-scaling based on CPU/memory metrics

---

*Thank you for reviewing my solution!*
