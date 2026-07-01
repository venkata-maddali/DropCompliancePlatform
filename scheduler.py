import os
import time
from datetime import datetime
from dotenv import load_dotenv

from drop_compliance_tool.workflow import get_config, run_cycle, schedule_next_run

load_dotenv()


def run_scheduler(interval_days: int = 30, max_runs: int = 1):
    config = get_config()
    next_run = datetime.now()
    runs = 0
    while runs < max_runs:
        if datetime.now() >= next_run:
            run_cycle(
                None,
                config['output_dir'],
                config['base_url'],
                config['api_key'],
                config['timeout'],
                config['download_endpoint'],
                config['upload_endpoint'],
                config['hash_mode'],
                config['update_existing_records'],
            )
            runs += 1
            next_run = schedule_next_run(interval_days)
        time.sleep(60)


if __name__ == '__main__':
    run_scheduler(int(os.getenv('SCHEDULE_INTERVAL_DAYS', '30')), int(os.getenv('SCHEDULE_MAX_RUNS', '1')))
