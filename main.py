import sys
import os
import signal
import argparse
import threading
import subprocess
import time

from src.configuration.config import load_all_configs, save_all_configs
from src.db.database_backup import run_backup_service, start_service, stop_service

PID_FILE = "backup_service.pid"


def start_in_background():
    process = subprocess.Popen([sys.executable, *sys.argv[:-1], "--start"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with open(PID_FILE, "w") as pid_file:
        pid_file.write(str(process.pid))
    print(f"Backup service started in the background with PID: {process.pid}")


def stop_background_service():
    try:
        with open(PID_FILE, "r") as pid_file:
            pid = int(pid_file.read().strip())
        os.kill(pid, signal.SIGTERM)
        os.remove(PID_FILE)
        print("Backup service stopped.")
    except FileNotFoundError:
        print("PID file not found. Is the service running in the background?")
    except ProcessLookupError:
        print("No such process found. It may have already been stopped.")
    except Exception as e:
        print(f"Error stopping the service: {e}")

def save_parsed_args(args):
    configs = load_all_configs()
    if args.api_url:
        configs["api"]["url"] = args.api_url
    if args.api_key:
        configs["api"]["api_key"] = args.api_key
    if args.interval_minutes:
        configs["backup"]["interval_minutes"] = int(args.interval_minutes)
    if args.db_host:
        configs["db"]["host"] = args.db_host
    if args.db_port:
        configs["db"]["port"] = args.db_port
    if args.db_name:
        configs["db"]["dbname"] = args.db_name
    if args.db_user:
        configs["db"]["user"] = args.db_user
    if args.db_password:
        configs["db"]["password"] = args.db_password
    if args.db_type:
        configs["db"]["type"] = args.db_type
    if args.backup_path:
        configs["backup"]["backup_path"] = args.backup_path
    if args.max_backup_files:
        configs["backup"]["max_backup_files"] = int(args.max_backup_files)

    save_all_configs(configs)

def main():
    parser = argparse.ArgumentParser(description="Database Backup Service")
    parser.add_argument('--start', action='store_true', help="Start the backup service.")
    parser.add_argument('--stop', action='store_true', help="Stop the backup service.")
    parser.add_argument('--background', action='store_true', help="Run the service in the background.")
    parser.add_argument("--api_url", help="API URL to send the backups to.")
    parser.add_argument("--api_key", help="API Key for authentication.")
    parser.add_argument("--interval_minutes", type=int, help="Interval in minutes for the backup service.")
    parser.add_argument("--db_host", help="Database host.")
    parser.add_argument("--db_port", help="Database port.")
    parser.add_argument("--db_name", help="Database name.")
    parser.add_argument("--db_user", help="Database username.")
    parser.add_argument("--db_password", help="Database password.")
    parser.add_argument("--db_type", help="Database type. Only 'PostgreSQL' is supported for now.")
    parser.add_argument("--backup_path", help="Path to store the backups.")
    parser.add_argument("--max_backup_files", type=int, help="Maximum number of backup files to keep.")


    args = parser.parse_args()

    if args.background:
        start_in_background()
        return

    if args.stop:
        stop_background_service()
        return

    save_parsed_args(args)
    configs = load_all_configs()

    if args.start:
        start_service()
        send_to_api = bool(configs["api"]["url"] and configs["api"]["api_key"])

        backup_thread = threading.Thread(target=run_backup_service, args=(send_to_api,), daemon=True)
        backup_thread.start()
        print("Backup service started in console mode. Press Ctrl+C to stop.")
        try:
            while backup_thread.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            print("Stopping backup service...")
            stop_service()


if __name__ == '__main__':
    main()
