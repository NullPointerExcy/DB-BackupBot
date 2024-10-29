import os
import schedule
import time
import psycopg2
import subprocess
import requests
from datetime import datetime
from src.configuration.config import load_all_configs

configs = load_all_configs()
DB_CONFIG = configs["db"]
BACKUP_CONFIG = configs["backup"]
API_CONFIG = configs["api"]

service_running = True


def create_db_dump():
    dump_path = os.path.join(
        BACKUP_CONFIG['backup_path'],
        f"{DB_CONFIG['dbname']}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    )
    delete_old_backups()

    pg_dump_command = [
        "pg_dump",
        "-h", DB_CONFIG["host"],
        "-p", str(DB_CONFIG["port"]),
        "-U", DB_CONFIG["user"],
        "-F", "c",
        "-d", DB_CONFIG["dbname"],
        "-f", dump_path
    ]

    try:
        env = os.environ.copy()
        env["PGPASSWORD"] = DB_CONFIG["password"]

        subprocess.run(pg_dump_command, env=env, check=True)
        print(f"Successfully created backup: {dump_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error while creating backup: {e}")

    return dump_path


def delete_old_backups():
    backup_files = sorted(
        [f for f in os.listdir(BACKUP_CONFIG["backup_path"]) if f.endswith(".sql")],
        key=lambda f: os.path.getctime(os.path.join(BACKUP_CONFIG["backup_path"], f))
    )
    # Delete the oldest files if the number of files exceeds the limit (max_backup_files)
    backup_files_to_delete = backup_files[:-BACKUP_CONFIG["max_backup_files"]]
    for file in backup_files_to_delete:
        os.remove(os.path.join(BACKUP_CONFIG["backup_path"], file))
        print(f"Deleted old backup: {file}")


def send_backup_to_api(dump_path):
    with open(dump_path, 'rb') as f:
        try:
            response = requests.post(
                API_CONFIG['url'],
                headers={'Authorization': f"Bearer {API_CONFIG['api_key']}"},
                files={'file': f}
            )
            if response.status_code == 200:
                print("Backup successfully sent to the API.")
            else:
                print(f"Error while sending the backup to the API: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"API-Connection error: {e}")


def scheduled_backup(send_to_api=False):
    dump_path = create_db_dump()
    if send_to_api:
        send_backup_to_api(dump_path)


def start_service():
    global service_running
    service_running = True


def stop_service():
    global service_running
    service_running = False


def run_backup_service(send_to_api=False):
    global DB_CONFIG, BACKUP_CONFIG, API_CONFIG, configs, service_running
    configs = load_all_configs()
    DB_CONFIG = configs["db"]
    BACKUP_CONFIG = configs["backup"]
    API_CONFIG = configs["api"]

    schedule.every(BACKUP_CONFIG["interval_minutes"]).minutes.do(scheduled_backup, send_to_api=send_to_api)

    print(f"Starting scheduled backups every {BACKUP_CONFIG['interval_minutes']} minutes.")
    while service_running:
        schedule.run_pending()
        time.sleep(1)
