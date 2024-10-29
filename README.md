# DB-BackupBot

A Python tool for automated database backups with optional cloud API integration.
> **Hint: Currently only PostgreSQL databases are supported. More are coming soon.**

## Usage

### Running the application
#### Using the Executable
Download or build the `.exe` file and execute it directly to launch the service with a GUI for configuration.

#### Running from Console
You can also start the service with specific configurations or in console mode:
```bash
python main.py --start [options]
```

## Command-Line Arguments
| Argument             | Type    | Default       | Description                                                                                             |
|----------------------|---------|---------------|---------------------------------------------------------------------------------------------------------|
| `--start`            | Flag    | `False`       | Starts the backup service in console mode.                                                              |
| `--stop`             | Flag    | `False`       | Stops the background backup service if it is running.                                                   |
| `--background`       | Flag    | `False`       | Starts the backup service in the background (detached from console).                                    |
| `--api_url`          | String  | None          | The API URL to which backups will be sent if enabled.                                                   |
| `--api_key`          | String  | None          | API key for authentication when sending backups to the API.                                             |
| `--interval_minutes` | Integer | 60            | Interval in minutes for scheduling backups.                                                             |
| `--db_host`          | String  | `localhost`   | Host of the database server.                                                                            |
| `--db_port`          | Integer | 5432          | Port number for the database connection.                                                                |
| `--db_name`          | String  | Required      | Name of the database to back up.                                                                        |
| `--db_user`          | String  | Required      | Username for the database authentication.                                                               |
| `--db_password`      | String  | Required      | Password for the database user.                                                                         |
| `--db_type`          | String  | `PostgreSQL`  | Type of database to back up (currently only PostgreSQL is supported).                                   |
| `--backup_path`      | String  | `./backups`   | Path where the backup files will be stored.                                                             |
| `--max_backup_files` | Integer | 5             | Maximum number of backup files to keep (older backups are deleted once the limit is exceeded).           |

## Example
### Starting the Backup Service in the Console
```bash
python main.py --start --db_name my_database --db_user my_user --db_password my_password --api_url https://my-api.com --api_key my_api_key
```

### Starting the Backup Service in the Background
```bash
python main.py --start --background
```

### Stopping the Backup Service
```bash
python main.py --stop
```

### Sending Backups to an API
```bash
python main.py --start --api_url "https://backup-api.example.com" --api_key "your_api_key_here"
```

## Notes
- Use `--background` to keep the service running independently of the terminal session.
- The service reads from JSON configuration files by default. Command-line arguments can override these settings and are saved for subsequent runs.