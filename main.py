import sys
import os
import signal
import argparse
import threading
import subprocess
from src.configuration.config import load_all_configs
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


def main():
    parser = argparse.ArgumentParser(description="Database Backup Service")
    parser.add_argument('--start', action='store_true', help="Start the backup service.")
    parser.add_argument('--stop', action='store_true', help="Stop the backup service.")
    parser.add_argument('--background', action='store_true', help="Run the service in the background.")

    args = parser.parse_args()

    if args.background:
        start_in_background()
        return

    if args.stop:
        stop_background_service()
        return

    configs = load_all_configs()

    if args.start:
        start_service()
        send_to_api = bool(configs["api"]["url"] and configs["api"]["api_key"])
        backup_thread = threading.Thread(target=run_backup_service, args=(send_to_api,))
        backup_thread.start()
        print("Backup service started in console mode. Press Ctrl+C to stop.")
        try:
            backup_thread.join()
        except KeyboardInterrupt:
            stop_service()
            print("Backup service stopped.")


if __name__ == '__main__':
    main()
