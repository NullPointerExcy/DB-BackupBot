import json
import os

CONFIG_DIR = os.path.dirname(__file__)


def load_config(filename):
    file_path = os.path.join(CONFIG_DIR, filename)
    with open(file_path, 'r') as file:
        return json.load(file)


def save_config(filename, data):
    file_path = os.path.join(CONFIG_DIR, filename)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)


def load_all_configs():
    db_config = load_config('db_config.json')
    backup_config = load_config('backup_config.json')
    api_config = load_config('api_config.json')
    ssh_config = load_config('ssh_config.json')
    return {"db": db_config, "backup": backup_config, "api": api_config, "ssh": ssh_config}


def save_all_configs(configs):
    save_config('db_config.json', configs['db'])
    save_config('backup_config.json', configs['backup'])
    save_config('api_config.json', configs['api'])
    save_config('ssh_config.json', configs['ssh'])
