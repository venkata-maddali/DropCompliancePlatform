import argparse
import os
from dotenv import load_dotenv

from drop_compliance_tool.database import init_db
from drop_compliance_tool.workflow import (
    get_config,
    import_raw_emails,
    process_failure_report,
    run_cycle,
)

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description='DROP compliance workflow tool')
    subparsers = parser.add_subparsers(dest='command', required=True)

    subparsers.add_parser('init-db', help='Initialize MySQL schema').set_defaults(func=handle_init_db)

    import_cmd = subparsers.add_parser('import-raw-emails', help='Import raw emails from a CSV file')
    import_cmd.add_argument('--input-csv', required=True)
    import_cmd.set_defaults(func=handle_import_raw_emails)

    run_cmd = subparsers.add_parser('run-cycle', help='Run a full DROP cycle')
    run_cmd.add_argument('--cycle-date', default=None)
    run_cmd.add_argument('--output-dir', default=os.getenv('OUTPUT_DIR', './output'))
    run_cmd.set_defaults(func=handle_run_cycle)

    amend_cmd = subparsers.add_parser('process-amendment', help='Process a DROP failure report')
    amend_cmd.add_argument('--run-id', type=int, required=True)
    amend_cmd.add_argument('--report-csv', required=True)
    amend_cmd.set_defaults(func=handle_process_amendment)

    config_cmd = subparsers.add_parser('show-config', help='Show the current environment-based configuration')
    config_cmd.set_defaults(func=handle_show_config)

    args = parser.parse_args()
    args.func(args)


def handle_init_db(_args):
    init_db()
    print('Database initialized')


def handle_import_raw_emails(args):
    import_raw_emails(args.input_csv)
    print(f'Imported raw emails from {args.input_csv}')


def handle_run_cycle(args):
    config = get_config()
    run_id, output_path = run_cycle(
        args.cycle_date,
        args.output_dir or config['output_dir'],
        config['base_url'],
        config['api_key'],
        config['timeout'],
        config['download_endpoint'],
        config['upload_endpoint'],
        config['hash_mode'],
        config['update_existing_records'],
    )
    print(f'Completed run {run_id}; wrote {output_path}')


def handle_process_amendment(args):
    process_failure_report(args.run_id, args.report_csv)
    print(f'Processed amendment report {args.report_csv}')


def handle_show_config(_args):
    config = get_config()
    for key, value in config.items():
        print(f'{key}={value}')


if __name__ == '__main__':
    main()
