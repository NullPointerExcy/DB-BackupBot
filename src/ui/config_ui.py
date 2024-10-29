import sys
import threading
import time

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog,
    QLineEdit, QComboBox, QProgressBar, QSpinBox, QColorDialog, QSlider, QHBoxLayout, QGroupBox
)
from src.configuration.config import load_all_configs, save_all_configs
from src.db.database_backup import run_backup_service, start_service, stop_service

db_types = ["PostgreSQL"]


class ConfigUI(QWidget):
    def __init__(self):
        super().__init__()
        self.configs = load_all_configs()
        self.backup_thread = None
        self.service_running = False
        self.backup_interval = self.configs["backup"]["interval_minutes"] * 60
        if self.backup_interval <= 0:
            self.backup_interval = 60
        self.remaining_time = self.backup_interval
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("DB Auto-Backup-Tool")
        self.setGeometry(100, 100, 400, 200)
        main_layout = QVBoxLayout()

        self.db_type_input = QComboBox()
        self.db_type_input.addItems(db_types)
        self.db_type_input.setCurrentText(self.configs["db"]["type"])
        self.db_type_input.currentTextChanged.connect(self.db_type_changed)

        self.interval_input = QSpinBox()
        self.interval_input.setValue(self.configs["backup"]["interval_minutes"])
        self.interval_input.valueChanged.connect(self.interval_changed)

        self.backup_path_input = QLineEdit(self.configs["backup"]["backup_path"])
        self.backup_path_button = QPushButton("Select Backup Path")
        self.backup_path_button.clicked.connect(self.select_backup_path)

        self.browse_backup_path = QPushButton("Browse")
        self.browse_backup_path.clicked.connect(self.select_backup_path)

        backup_group = QGroupBox("Backup Configuration")
        backup_layout = QVBoxLayout()
        backup_layout.addWidget(QLabel("Backup Interval (minutes)"))
        backup_layout.addWidget(self.interval_input)
        backup_layout.addWidget(QLabel("Max Backups to Keep"))
        self.max_backups_input = QSpinBox()
        self.max_backups_input.setValue(self.configs["backup"]["max_backup_files"])
        self.max_backups_input.textChanged.connect(self.max_backups_changed)
        backup_layout.addWidget(self.max_backups_input)
        backup_layout.addWidget(QLabel("Backup Path"))
        backup_layout.addWidget(self.backup_path_input)
        backup_layout.addWidget(self.browse_backup_path)
        backup_group.setLayout(backup_layout)
        # username, password, host, port, dbname
        db_group = QGroupBox("Database Configuration")
        db_layout = QVBoxLayout()
        db_layout.addWidget(QLabel("Database Type"))
        db_layout.addWidget(self.db_type_input)
        db_layout.addWidget(QLabel("DB User"))
        self.db_user_input = QLineEdit(self.configs["db"]["user"])
        self.db_user_input.textChanged.connect(self.db_username_changed)
        db_layout.addWidget(self.db_user_input)
        db_layout.addWidget(QLabel("Password"))
        self.db_password_input = QLineEdit(self.configs["db"]["password"])
        self.db_password_input.textChanged.connect(self.db_password_changed)
        db_layout.addWidget(self.db_password_input)
        db_layout.addWidget(QLabel("Host"))
        self.db_host_input = QLineEdit(self.configs["db"]["host"])
        self.db_host_input.textChanged.connect(self.db_host_changed)
        db_layout.addWidget(self.db_host_input)
        db_layout.addWidget(QLabel("Port"))
        self.db_port_input = QLineEdit(self.configs["db"]["port"])
        self.db_port_input.textChanged.connect(self.db_port_changed)
        db_layout.addWidget(self.db_port_input)
        db_layout.addWidget(QLabel("Database Name"))
        self.db_name_input = QLineEdit(self.configs["db"]["dbname"])
        self.db_name_input.textChanged.connect(self.db_name_changed)
        db_layout.addWidget(self.db_name_input)
        db_group.setLayout(db_layout)

        api_group = QGroupBox("API Configuration")
        api_layout = QVBoxLayout()
        self.api_url_input = QLineEdit(self.configs["api"]["url"])
        self.api_url_input.textChanged.connect(self.api_url_changed)
        self.api_token_input = QLineEdit(self.configs["api"]["api_key"])
        self.api_token_input.textChanged.connect(self.api_token_changed)

        api_layout.addWidget(QLabel("API URL"))
        api_layout.addWidget(self.api_url_input)
        api_layout.addWidget(QLabel("API Token"))
        api_layout.addWidget(self.api_token_input)
        api_group.setLayout(api_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        self.start_button = QPushButton("Start Backup Service")
        self.start_button.clicked.connect(self.toggle_service)
        self.start_button.setEnabled(self.can_start_service())

        self.interval_input.move(20, 20)
        self.api_url_input.move(20, 60)
        self.start_button.move(20, 100)

        main_layout.addWidget(db_group)
        main_layout.addWidget(backup_group)
        main_layout.addWidget(api_group)

        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.start_button)

        self.setLayout(main_layout)

    def can_start_service(self) -> bool:
        return all([
            self.configs["db"]["type"],
            self.configs["db"]["user"],
            self.configs["db"]["password"],
            self.configs["db"]["host"],
            self.configs["db"]["port"],
            self.configs["db"]["dbname"],
            self.configs["backup"]["interval_minutes"],
            self.configs["backup"]["backup_path"]
        ])

    def max_backups_changed(self, value):
        self.configs["backup"]["max_backup_files"] = int(value)
        save_all_configs(self.configs)
        self.update_start_button_state()

    def update_progress_bar(self):
        if self.remaining_time > 0:
            self.remaining_time -= 1
            progress = ((self.backup_interval - self.remaining_time) / self.backup_interval) * 100
            self.progress_bar.setValue(int(progress))
        else:
            self.progress_bar.setValue(100)
            self.remaining_time = self.backup_interval
            self.progress_bar.setValue(0)

    def interval_changed(self, value):
        self.configs["backup"]["interval_minutes"] = int(value)
        save_all_configs(self.configs)
        self.update_start_button_state()

    def api_url_changed(self, text):
        self.configs["api"]["url"] = text
        save_all_configs(self.configs)
        self.update_start_button_state()

    def api_token_changed(self, text):
        self.configs["api"]["api_key"] = text
        save_all_configs(self.configs)
        self.update_start_button_state()

    def db_username_changed(self, text):
        self.configs["db"]["user"] = text
        save_all_configs(self.configs)
        self.update_start_button_state()

    def db_password_changed(self, text):
        self.configs["db"]["password"] = text
        save_all_configs(self.configs)
        self.update_start_button_state()

    def db_host_changed(self, text):
        self.configs["db"]["host"] = text
        save_all_configs(self.configs)
        self.update_start_button_state()

    def db_port_changed(self, text):
        self.configs["db"]["port"] = text
        save_all_configs(self.configs)
        self.update_start_button_state()

    def db_name_changed(self, text):
        self.configs["db"]["dbname"] = text
        save_all_configs(self.configs)
        self.update_start_button_state()

    def update_start_button_state(self):
        self.start_button.setEnabled(self.can_start_service())

    def db_type_changed(self, text):
        self.configs["db"]["type"] = text
        save_all_configs(self.configs)
        self.update_start_button_state()

    def toggle_service(self):
        if not self.service_running:
            self.start_service()
        else:
            self.stop_service()

    def start_service(self):
        self.service_running = True
        start_service()
        self.start_button.setText("Stop Backup Service")
        self.backup_thread = threading.Thread(target=self.run_backup_service_ui)
        self.backup_thread.start()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress_bar)
        self.timer.start(1000)

    def stop_service(self):
        self.service_running = False
        stop_service()
        self.timer.stop()
        self.progress_bar.setValue(0)
        self.remaining_time = self.configs["backup"]["interval_minutes"] * 60
        self.start_button.setText("Start Backup Service")
        if self.backup_thread:
            self.backup_thread.join()
            self.backup_thread = None
        print("Backup service stopped.")

    def select_backup_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Backup Path")
        self.backup_path_input.setText(path)
        self.configs["backup"]["backup_path"] = path
        save_all_configs(self.configs)
        self.update_start_button_state()

    def select_backup_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Backup Path")
        self.backup_path_input.setText(path)
        self.configs["backup"]["backup_path"] = path
        save_all_configs(self.configs)
        self.update_start_button_state()

    def closeEvent(self, event):
        """Stop the backup service when the window is closed."""
        self.stop_service()
        event.accept()

    def run_backup_service_ui(self):
        send_to_api: bool = self.api_url_input.text() and self.api_token_input.text()
        run_backup_service(send_to_api=send_to_api)


if __name__ == '__main__':
    app = QApplication([])
    app.setStyle("Fusion")
    window = ConfigUI()
    window.show()
    sys.exit(app.exec())
