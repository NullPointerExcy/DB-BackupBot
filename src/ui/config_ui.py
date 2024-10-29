import sys
import threading
import time

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog,
    QLineEdit, QComboBox, QProgressBar, QSpinBox, QColorDialog, QSlider, QHBoxLayout, QGroupBox, QCheckBox
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
        self.setGeometry(100, 100, 600, 400)

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
        self.browse_backup_path = QPushButton("Select Backup Path")
        self.browse_backup_path.clicked.connect(self.select_backup_path)
        self.max_backups_input = QSpinBox()
        self.max_backups_input.setValue(self.configs["backup"]["max_backup_files"])
        self.max_backups_input.textChanged.connect(self.max_backups_changed)
        self.db_user_input = QLineEdit(self.configs["db"]["user"])
        self.db_user_input.textChanged.connect(self.db_username_changed)
        self.db_password_input = QLineEdit(self.configs["db"]["password"])
        self.db_password_input.textChanged.connect(self.db_password_changed)
        self.db_host_input = QLineEdit(self.configs["db"]["host"])
        self.db_host_input.textChanged.connect(self.db_host_changed)
        self.db_port_input = QLineEdit(self.configs["db"]["port"])
        self.db_port_input.textChanged.connect(self.db_port_changed)
        self.db_name_input = QLineEdit(self.configs["db"]["dbname"])
        self.db_name_input.textChanged.connect(self.db_name_changed)

        self.api_checkbox = QCheckBox("Use API")
        self.api_checkbox.stateChanged.connect(self.use_api_changed)
        self.api_url_input = QLineEdit(self.configs["api"]["url"])
        self.api_url_input.textChanged.connect(self.api_url_changed)
        self.api_token_input = QLineEdit(self.configs["api"]["api_key"])
        self.api_token_input.textChanged.connect(self.api_token_changed)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        self.ssh_checkbox = QCheckBox("Use SSH")
        self.ssh_checkbox.setChecked(self.configs["ssh"]["use_ssh"])
        self.ssh_checkbox.stateChanged.connect(self.use_ssh_changed)
        self.ssh_host_input = QLineEdit(self.configs["ssh"]["host"])
        self.ssh_host_input.textChanged.connect(self.ssh_host_changed)
        self.ssh_port_input = QLineEdit(str(self.configs["ssh"]["port"]))
        self.ssh_port_input.textChanged.connect(self.ssh_port_changed)
        self.ssh_user_input = QLineEdit(self.configs["ssh"]["username"])
        self.ssh_user_input.textChanged.connect(self.ssh_user_changed)
        self.ssh_key_input = QLineEdit(self.configs["ssh"]["private_key_path"])
        self.ssh_key_input.textChanged.connect(self.ssh_key_changed)
        self.ssh_key_button = QPushButton("Select Private Key")
        self.ssh_key_button.clicked.connect(self.select_ssh_key)
        self.ssh_server_save_path = QLineEdit(self.configs["ssh"]["server_folder_path"])
        self.ssh_server_save_path.textChanged.connect(self.change_ssh_server_save_path)

        self.start_button = QPushButton("Start Backup Service")
        self.start_button.clicked.connect(self.toggle_service)
        self.start_button.setEnabled(self.can_start_service())

        self.interval_input.move(20, 20)
        self.api_url_input.move(20, 60)
        self.start_button.move(20, 100)

        backup_group = QGroupBox("Backup Configuration")
        backup_layout = QVBoxLayout()

        # Horizontal layout for labels and input fields
        backup_inputs_layout = QHBoxLayout()
        backup_inputs_layout.addWidget(QLabel("Backup Interval (minutes)"))
        backup_inputs_layout.addWidget(self.interval_input)
        backup_inputs_layout.addWidget(QLabel("Max Backups to Keep"))
        backup_inputs_layout.addWidget(self.max_backups_input)
        backup_inputs_layout.addWidget(QLabel("Backup Path"))
        backup_inputs_layout.addWidget(self.backup_path_input)

        # Vertical layout for "Browse" button
        backup_buttons_layout = QVBoxLayout()
        backup_buttons_layout.addWidget(self.browse_backup_path)

        # Add horizontal inputs and vertical buttons to the main backup layout
        backup_layout.addLayout(backup_inputs_layout)
        backup_layout.addLayout(backup_buttons_layout)
        backup_group.setLayout(backup_layout)

        # Database Configuration Section
        db_group = QGroupBox("Database Configuration")
        db_layout = QVBoxLayout()

        # Horizontal layout for database labels and inputs
        db_inputs_layout = QHBoxLayout()
        db_inputs_layout.addWidget(QLabel("Database Type"))
        db_inputs_layout.addWidget(self.db_type_input)
        db_inputs_layout.addWidget(QLabel("DB User"))
        db_inputs_layout.addWidget(self.db_user_input)
        db_inputs_layout.addWidget(QLabel("Password"))
        db_inputs_layout.addWidget(self.db_password_input)
        db_inputs_layout.addWidget(QLabel("Host"))
        db_inputs_layout.addWidget(self.db_host_input)
        db_inputs_layout.addWidget(QLabel("Port"))
        db_inputs_layout.addWidget(self.db_port_input)
        db_inputs_layout.addWidget(QLabel("Database Name"))
        db_inputs_layout.addWidget(self.db_name_input)

        # Add the horizontal inputs layout to the database configuration
        db_layout.addLayout(db_inputs_layout)
        db_group.setLayout(db_layout)

        # API Configuration Section
        api_group = QGroupBox("API Configuration")
        api_layout = QVBoxLayout()
        api_layout.addWidget(self.api_checkbox)

        # Horizontal layout for API inputs
        api_inputs_layout = QHBoxLayout()
        api_inputs_layout.addWidget(QLabel("API URL"))
        api_inputs_layout.addWidget(self.api_url_input)
        api_inputs_layout.addWidget(QLabel("API Token"))
        api_inputs_layout.addWidget(self.api_token_input)
        api_layout.addLayout(api_inputs_layout)
        api_group.setLayout(api_layout)

        # SSH Configuration Section with horizontal layout for inputs and button below
        ssh_group = QGroupBox("SSH Configuration")
        ssh_layout = QVBoxLayout()
        ssh_layout.addWidget(self.ssh_checkbox)

        # Horizontal layout for SSH inputs
        ssh_inputs_layout = QHBoxLayout()
        ssh_inputs_layout.addWidget(QLabel("SSH Host"))
        ssh_inputs_layout.addWidget(self.ssh_host_input)
        ssh_inputs_layout.addWidget(QLabel("SSH Port"))
        ssh_inputs_layout.addWidget(self.ssh_port_input)
        ssh_inputs_layout.addWidget(QLabel("SSH User"))
        ssh_inputs_layout.addWidget(self.ssh_user_input)
        ssh_inputs_layout.addWidget(QLabel("SSH Private Key Path"))
        ssh_inputs_layout.addWidget(self.ssh_key_input)

        # Vertical layout for "Select Private Key" button
        ssh_buttons_layout = QVBoxLayout()
        ssh_buttons_layout.addWidget(self.ssh_key_button)
        ssh_buttons_layout.addWidget(QLabel("Server Save Path"))
        ssh_buttons_layout.addWidget(self.ssh_server_save_path)

        # Add horizontal inputs and vertical button to the main SSH layout
        ssh_layout.addLayout(ssh_inputs_layout)
        ssh_layout.addLayout(ssh_buttons_layout)
        ssh_group.setLayout(ssh_layout)

        # Main Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(db_group)
        main_layout.addWidget(backup_group)
        main_layout.addWidget(api_group)
        main_layout.addWidget(ssh_group)
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

    def use_ssh_changed(self, state):
        # state is 2 when checked, 0 when unchecked
        self.configs["ssh"]["use_ssh"] = state == 2
        save_all_configs(self.configs)
        self.update_start_button_state()

    def use_api_changed(self, state):
        self.configs["api"]["use_api"] = state == 2
        save_all_configs(self.configs)
        self.update_start_button_state()

    def ssh_host_changed(self, text):
        self.configs["ssh"]["host"] = text
        save_all_configs(self.configs)
        self.update_start_button_state()

    def ssh_port_changed(self, value):
        self.configs["ssh"]["port"] = int(value)
        save_all_configs(self.configs)
        self.update_start_button_state()

    def ssh_user_changed(self, text):
        self.configs["ssh"]["user"] = text
        save_all_configs(self.configs)
        self.update_start_button_state()

    def ssh_key_changed(self, text):
        self.configs["ssh"]["private_key_path"] = text
        save_all_configs(self.configs)
        self.update_start_button_state()

    def select_ssh_key(self):
        path = QFileDialog.getOpenFileName(self, "Select SSH Private Key")[0]
        self.ssh_key_input.setText(path)
        self.configs["ssh"]["private_key_path"] = path
        save_all_configs(self.configs)
        self.update_start_button_state()

    def change_ssh_server_save_path(self, text):
        self.configs["ssh"]["server_folder_path"] = text
        save_all_configs(self.configs)
        self.update_start_button_state()

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
        run_backup_service(send_to_api=self.configs["api"]["use_api"], send_to_server=self.configs["ssh"]["use_ssh"])


if __name__ == '__main__':
    app = QApplication([])
    app.setStyle("Fusion")
    window = ConfigUI()
    window.show()
    sys.exit(app.exec())
