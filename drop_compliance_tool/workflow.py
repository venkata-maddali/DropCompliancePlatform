import base64
import csv
import hashlib
import os
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path
import requests

try:
    from .database import (
        create_run,
        fetch_hashes,
        insert_amendment,
        insert_raw_email,
        insert_results_batch,
        update_existing_record_statuses,
        update_run,
    )
except ImportError:  # pragma: no cover - allows running as a script
    from database import (
        create_run,
        fetch_hashes,
        insert_amendment,
        insert_raw_email,
        insert_results_batch,
        update_existing_record_statuses,
        update_run,
    )


def build_drop_url(base_url: str, endpoint: str) -> str:
    return f'{base_url.rstrip("/")}/{endpoint.lstrip("/")}'


def get_config():
    return {
        'base_url': os.getenv('DROP_BASE_URL', ''),
        'api_key': os.getenv('DROP_API_KEY', ''),
        'timeout': int(os.getenv('DROP_TIMEOUT', '30')),
        'output_dir': os.getenv('OUTPUT_DIR', './output'),
        'hash_algorithm': os.getenv('HASH_ALGORITHM', 'sha256'),
        'hash_mode': os.getenv('HASH_MODE', 'hex'),
        'download_endpoint': os.getenv('DROP_DOWNLOAD_ENDPOINT', '/download/data'),
        'upload_endpoint': os.getenv('DROP_UPLOAD_ENDPOINT', '/download/upload'),
        'amend_endpoint': os.getenv('DROP_AMEND_ENDPOINT', '/download/amend'),
        'update_existing_records': os.getenv('UPDATE_EXISTING_RECORDS', 'true').lower() == 'true',
    }


def normalize_hash(value: str, mode: str = 'hex') -> str:
    normalized = (value or '').strip()
    if not normalized:
        return ''
    if mode == 'base64-unhex':
        candidate = normalized.lower()
        try:
            decoded = bytes.fromhex(candidate)
            return base64.b64encode(decoded).decode('ascii').strip()
        except ValueError:
            return candidate
    return normalized.lower()


def hash_email(email: str, mode: str = 'hex') -> str:
    raw = email.strip().lower().encode('utf-8')
    digest = hashlib.sha256(raw).digest()
    if mode == 'base64-unhex':
        return base64.b64encode(digest).decode('ascii').strip()
    return digest.hex()


def resolve_status(deleted: bool, opted_out: bool) -> str:
    if deleted:
        return 'deleted'
    if opted_out:
        return 'opted_out'
    return 'not_found'


def parse_bool(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {'1', 'true', 'yes', 'y'}


def chunked(iterable, size):
    if size <= 0:
        raise ValueError('size must be greater than zero')
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def import_raw_emails(input_csv: str):
    config = get_config()
    with open(input_csv, 'r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            email = (row.get('email') or '').strip()
            if not email:
                continue
            insert_raw_email(
                email,
                deleted=parse_bool(row.get('deleted')),
                opted_out=parse_bool(row.get('opted_out')),
                email_hash=hash_email(email, mode=config['hash_mode']),
            )


def download_drop_data(base_url: str, api_key: str, timeout: int, output_dir: str, cycle_date: str, endpoint: str = '/download/data'):
    url = build_drop_url(base_url, endpoint)
    response = requests.get(url, headers={'Authorization': f'Bearer {api_key}'}, timeout=timeout)
    response.raise_for_status()
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    zip_path = target_dir / f'{cycle_date}.zip'
    with open(zip_path, 'wb') as handle:
        handle.write(response.content)
    return zip_path


def extract_drop_csv(zip_path: Path, output_dir: Path, cycle_date: str):
    with zipfile.ZipFile(zip_path, 'r') as archive:
        csv_name = next(name for name in archive.namelist() if name.lower().endswith('.csv'))
        archive.extract(csv_name, path=output_dir)
        extracted_path = output_dir / csv_name
        target_path = output_dir / f'{cycle_date}.csv'
        extracted_path.rename(target_path)
        return target_path


def process_drop_csv(source_csv: str, run_id: int, output_dir: str, update_existing_records: bool = True, hash_mode: str = 'hex', batch_size: int = 1000):
    hashes = {}
    for item in fetch_hashes():
        record = {'deleted': item['deleted_at'] is not None, 'opted_out': item['opted_out_at'] is not None}
        for candidate in {item['email_hash'], normalize_hash(item['email_hash'], mode='hex'), normalize_hash(item['email_hash'], mode='base64-unhex')}:
            if candidate:
                hashes[candidate] = record
    source_path = Path(source_csv)
    output_path = source_path
    temp_output_path = source_path.with_suffix('.processed.csv')
    batch_size = max(1, int(batch_size))
    with open(source_path, 'r', encoding='utf-8-sig', newline='') as handle, open(temp_output_path, 'w', encoding='utf-8', newline='') as out_handle:
        reader = csv.DictReader(handle)
        writer = csv.DictWriter(out_handle, fieldnames=['DropID', 'Status'])
        writer.writeheader()
        matched = 0
        total = 0
        status_counts = {'deleted': 0, 'opted_out': 0, 'not_found': 0}
        pending_results = []
        pending_updates = []
        pending_rows = []
        for row in reader:
            total += 1
            drop_id = (row.get('DropID') or '').strip()
            hash_email_value = (row.get('HashEmail') or '').strip()
            if not drop_id or not hash_email_value:
                continue
            normalized_hash = normalize_hash(hash_email_value, mode=hash_mode)
            record = hashes.get(normalized_hash)
            if record:
                matched += 1
                status = resolve_status(record['deleted'], record['opted_out'])
                if update_existing_records and status in {'deleted', 'opted_out'}:
                    pending_updates.append((normalized_hash, status == 'deleted', status == 'opted_out', source_path.stem, status))
            else:
                status = 'not_found'
            pending_rows.append({'DropID': drop_id, 'Status': status})
            pending_results.append((drop_id, status, hash_email_value))
            status_counts[status] += 1
            if len(pending_results) >= batch_size:
                writer.writerows(pending_rows)
                pending_rows.clear()
                insert_results_batch(run_id, pending_results)
                pending_results.clear()
                if pending_updates:
                    update_existing_record_statuses(pending_updates)
                    pending_updates.clear()
        if pending_rows:
            writer.writerows(pending_rows)
        if pending_results:
            insert_results_batch(run_id, pending_results)
        if pending_updates:
            update_existing_record_statuses(pending_updates)
    temp_output_path.replace(output_path)
    return output_path, total, matched, status_counts


def upload_results(output_path: Path, base_url: str, api_key: str, timeout: int, endpoint: str = '/download/upload'):
    response = requests.post(
        build_drop_url(base_url, endpoint),
        headers={'Authorization': f'Bearer {api_key}'},
        files={'file': (output_path.name, output_path.read_bytes(), 'text/csv')},
        timeout=timeout,
    )
    response.raise_for_status()
    return response


def process_failure_report(run_id: int, report_csv: str):
    with open(report_csv, 'r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            drop_id = (row.get('DropID') or '').strip()
            original_status = (row.get('OriginalStatus') or '').strip() or 'not_found'
            corrected_status = (row.get('CorrectedStatus') or '').strip() or 'not_found'
            reason = (row.get('Reason') or '').strip() or 'reported_by_drop'
            insert_amendment(run_id, drop_id, original_status, corrected_status, reason)


def run_cycle(cycle_date: str, output_dir: str, base_url: str, api_key: str, timeout: int, download_endpoint: str = '/download/data', upload_endpoint: str = '/download/upload', hash_mode: str = 'hex', update_existing_records: bool = True):
    cycle_date_value = cycle_date or date.today().strftime('%Y-%m-%d')
    source_zip = download_drop_data(base_url, api_key, timeout, output_dir, cycle_date_value, endpoint=download_endpoint)
    source_csv = extract_drop_csv(source_zip, Path(output_dir), cycle_date_value)
    run_id = create_run(cycle_date_value, source_csv.name)
    output_path, total, matched, status_counts = process_drop_csv(str(source_csv), run_id, output_dir, update_existing_records=update_existing_records, hash_mode=hash_mode)
    update_run(run_id, output_file_name=output_path.name, total_records=total, matched_records=matched, status_counts=str(status_counts))
    upload_results(output_path, base_url, api_key, timeout, endpoint=upload_endpoint)
    return run_id, output_path


def schedule_next_run(interval_days: int = 30):
    return datetime.now() + timedelta(days=interval_days)
