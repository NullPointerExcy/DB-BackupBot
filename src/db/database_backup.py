import os
from typing import Dict

import schedule
import time
import paramiko
import os
import subprocess
import requests
from datetime import datetime
from src.configuration.config import load_all_configs

configs = load_all_configs()
DB_CONFIG = configs["db"]
BACKUP_CONFIG = configs["backup"]
API_CONFIG = configs["api"]
SSH_CONFIG = configs["ssh"]

service_running = True


def create_db_dump():
    """
    Creates a backup of the database using pg_dump.
    :return:
    """
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
    """
    Deletes old backup files if the number of files exceeds the limit specified in the configuration.
    :return:
    """
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
    """
    Sends a backup file to an API endpoint using a POST request.
    :param dump_path: Path to the backup file.
    :return:
    """
    with open(dump_path, 'rb') as f:
        try:
            headers = {}
            if API_CONFIG.get('api_key'):
                headers['Authorization'] = f"Bearer {API_CONFIG['api_key']}"

            response = requests.post(
                API_CONFIG['url'],
                headers=headers,
                files={'file': f}
            )

            if response.status_code == 200:
                print("Backup successfully sent to the API.")
            else:
                print(f"Error while sending the backup to the API: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"API-Connection error: {e}")


def save_backup_to_server(dump_path: str):
    """
    Uploads a backup file to a remote server via SCP using SSH.
    :param dump_path: Path to the local backup file.
    :raises Exception: If the connection fails or the file upload encounters an issue.
    """
    # Initialize SSH client
    global sftp
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    remote_path = SSH_CONFIG["server_folder_path"]

    try:
        ssh.connect(
            hostname=SSH_CONFIG["host"],
            port=SSH_CONFIG.get("port", 22),
            username=SSH_CONFIG["username"],
            # Use private key for authentication
            key_filename=SSH_CONFIG["private_key_path"]
        )
        sftp = ssh.open_sftp()
        dir_path = SSH_CONFIG["server_folder_path"]
        try:
            sftp.stat(dir_path)
        except FileNotFoundError:
            sftp.mkdir(dir_path)

        # Add / if the remote path does not end with /
        if not remote_path.endswith("/"):
            remote_path += "/"
        # Get the filename from the dump path and add it to the remote path
        remote_path += os.path.basename(dump_path)
        print(remote_path)
        sftp.put(dump_path, remote_path)
        print(f"Backup successfully saved on the server at: {remote_path}")

    except Exception as e:
        print(f"Error uploading backup: {e}")
    finally:
        sftp.close()
        ssh.close()


def scheduled_backup(send_to_api=False, send_to_server=False):
    dump_path = create_db_dump()
    if send_to_api:
        send_backup_to_api(dump_path)
    if send_to_server:
        save_backup_to_server(dump_path)


def start_service():
    global service_running
    service_running = True


def stop_service():
    global service_running
    service_running = False


def run_backup_service(send_to_api=False, send_to_server=False):
    global DB_CONFIG, BACKUP_CONFIG, API_CONFIG, SSH_CONFIG, configs, service_running
    configs = load_all_configs()
    DB_CONFIG = configs["db"]
    BACKUP_CONFIG = configs["backup"]
    API_CONFIG = configs["api"]
    SSH_CONFIG = configs["ssh"]

    schedule.every(BACKUP_CONFIG["interval_minutes"]).minutes.do(scheduled_backup, send_to_api=send_to_api, send_to_server=send_to_server)

    print(f"Starting scheduled backups every {BACKUP_CONFIG['interval_minutes']} minutes.")
    while service_running:
        schedule.run_pending()
        time.sleep(1)
