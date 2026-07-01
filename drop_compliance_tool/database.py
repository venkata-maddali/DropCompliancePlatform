import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('MYSQL_DB', 'drop_compliance'),
        'autocommit': True,
    }
    if os.getenv('MYSQL_SSL_DISABLED', 'true').lower() == 'true':
        config['ssl_disabled'] = True
    return mysql.connector.connect(**config)


def init_db():
    with open('schema.sql', 'r', encoding='utf-8') as handle:
        schema_sql = handle.read()
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for statement in schema_sql.split(';'):
                stmt = statement.strip()
                if stmt:
                    cursor.execute(stmt)
    finally:
        conn.close()


def fetch_hashes():
    conn = get_db_connection()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute('SELECT email_hash, deleted_at, opted_out_at FROM raw_emails')
            return cursor.fetchall()
    finally:
        conn.close()


def insert_raw_email(email, deleted=False, opted_out=False, email_hash=None):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            resolved_hash = email_hash or hash_email(email)
            cursor.execute(
                """
                INSERT INTO raw_emails (email, email_hash, deleted_at, opted_out_at)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE email=%s, deleted_at=%s, opted_out_at=%s, updated_at=CURRENT_TIMESTAMP
                """,
                (
                    email,
                    resolved_hash,
                    None if not deleted else '1970-01-01 00:00:00',
                    None if not opted_out else '1970-01-01 00:00:00',
                    email,
                    None if not deleted else '1970-01-01 00:00:00',
                    None if not opted_out else '1970-01-01 00:00:00',
                ),
            )
    finally:
        conn.close()


def update_existing_record_status(email_hash, deleted=False, opted_out=False, cycle_date=None, status=None):
    update_existing_record_statuses([(email_hash, deleted, opted_out, cycle_date, status)])


def update_existing_record_statuses(records):
    if not records:
        return
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                UPDATE raw_emails
                SET deleted_at = CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE deleted_at END,
                    opted_out_at = CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE opted_out_at END,
                    last_drop_cycle_date = %s,
                    last_drop_status = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE email_hash = %s
                """,
                [
                    (deleted, opted_out, cycle_date, status, email_hash)
                    for email_hash, deleted, opted_out, cycle_date, status in records
                ],
            )
    finally:
        conn.close()


def create_run(cycle_date, source_file_name, output_file_name=None):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO drop_cycle_runs (cycle_date, source_file_name, output_file_name, total_records, matched_records)
                VALUES (%s, %s, %s, 0, 0)
                """,
                (cycle_date, source_file_name, output_file_name),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def update_run(run_id, **values):
    if not values:
        return
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            assignments = ', '.join(f'{key} = %s' for key in values.keys())
            cursor.execute(f'UPDATE drop_cycle_runs SET {assignments} WHERE id = %s', list(values.values()) + [run_id])
    finally:
        conn.close()


def insert_result(run_id, drop_id, status, source_hash):
    insert_results_batch(run_id, [(drop_id, status, source_hash)])


def insert_results_batch(run_id, rows):
    if not rows:
        return
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO drop_results (run_id, drop_id, status, source_hash)
                VALUES (%s, %s, %s, %s)
                """,
                [(run_id, drop_id, status, source_hash) for drop_id, status, source_hash in rows],
            )
    finally:
        conn.close()


def insert_amendment(run_id, drop_id, original_status, corrected_status, reason):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO drop_amendments (run_id, drop_id, original_status, corrected_status, reason)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (run_id, drop_id, original_status, corrected_status, reason),
            )
    finally:
        conn.close()


def hash_email(email):
    import hashlib
    return hashlib.sha256(email.strip().lower().encode('utf-8')).hexdigest()
