import subprocess
import datetime
import os


class DatabaseBackup:
    def __init__(self, db_type, host, port, username, password, db_name, backup_dir="./backups"):
        self.db_type = db_type
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.db_name = db_name
        self.backup_dir = backup_dir

        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

    def get_backup_command(self):
        pass

    def run_backup(self):
        pass
