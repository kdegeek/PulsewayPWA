# Pulseway Project

This repository contains the backend and frontend components for a Pulseway monitoring dashboard and management tool.

## Project Structure

The repository is organized as follows:

- `/backend`: Contains the Python FastAPI backend application.
  - `/backend/app`: Main application code.
  - `/backend/setup.py`: Optional script for first-time setup (directory creation, .env setup, DB schema initialization).
- `/frontend`: Contains static frontend application files (HTML, CSS, JS, PWA assets).
- `/scripts`: Contains utility shell scripts for managing the application (e.g., `start.sh`, `backup.sh`, `restore.sh`).
- `/docs`: Contains detailed documentation, including original project READMEs and architecture descriptions.
- `Dockerfile`, `Dockerfile.dev`: Docker configurations for production and development.
- `docker-compose.yml`, `docker-compose.dev.yml`: Docker Compose files for easy service management.
- `requirements.txt`: Python dependencies for the backend.
- `.env.example`: Example environment variables configuration.

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Pulseway API credentials

### Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Configure Environment Variables:**
    Copy the example environment file and fill in your Pulseway API credentials:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file with your Pulseway API credentials and any other necessary configurations (e.g., `DATABASE_URL` if not using the default).

3.  **Optional: Run First-Time Setup Script (Recommended before first `docker-compose up`):**
    This script helps create necessary directories (`data/`, `logs/`, `backups/` in the project root), copies `.env.example` to `.env` if it doesn't exist, and can initialize the database schema.
    ```bash
    # Ensure your .env file is configured, especially DATABASE_URL
    cd backend
    python setup.py
    cd ..
    ```
    *Database Initialization Note: When `backend/setup.py` initializes the database, it does so based on the `DATABASE_URL` in your `.env` file. If this URL points to a local file path (like the default `sqlite:///./data/pulseway.db`), the script will create/update the database file at `backend/data/pulseway.db` (relative to where `setup.py` is run). This local database can be used for development directly on the host.*
    *However, when running the application via `docker-compose`, the backend service uses a Docker named volume for database persistence (see "Database Persistence and Initialization (Docker)" below). The application itself (`backend/app/main.py`) will automatically create the schema in this volume on startup if needed. Thus, running `setup.py` for schema creation is primarily for non-Docker local development or pre-populating a local `data/` directory that might later be used to seed a volume.*

### Running the Application (Docker)

-   **For Production:**
    ```bash
    docker-compose up -d
    ```

-   **For Development:**
    This command starts the services defined in both `docker-compose.yml` and `docker-compose.dev.yml`, using the development Dockerfile (`Dockerfile.dev`) for the backend, which typically includes features like auto-reload.
    ```bash
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
    ```

The backend API will typically be available at `http://localhost:8000`. API documentation (Swagger UI) can be found at `http://localhost:8000/docs`.

#### Database Persistence and Initialization (Docker)

-   **Persistence:** The application uses a Docker named volume (defined as `pulseway_data` in `docker-compose.yml`, typically created with a project-specific prefix like `yourprojectfolder_pulseway_data`) to store the SQLite database (e.g., `pulseway.db`). This ensures your data persists across container restarts and updates.
-   **Schema Initialization:** The backend application (`backend/app/main.py`) automatically creates the necessary database tables (schema) within this Docker volume when the service starts if the database file or tables do not already exist. Manual database setup is generally not required when using Docker for deployment.
-   **`.env` Configuration:** Ensure your `.env` file is correctly configured, especially with `PULSEWAY_TOKEN_ID`, `PULSEWAY_TOKEN_SECRET`. The `DATABASE_URL` (if you override the default `sqlite:///./data/pulseway.db`) should point to a file path like `/app/data/your_db_name.db`, which corresponds to the `pulseway_data` volume mounted at `/app/data` inside the container.

## Detailed Documentation

For more detailed information on the backend API, PWA frontend, architecture, and CLI usage, please refer to the documents in the `/docs` directory:
- `docs/readme_documentation.md` (Original comprehensive backend README)
- `docs/complete-project-structure.md` (Original PWA structure and details)
- `docs/docker-configuration.md` (Original Docker setup notes)

## CLI Tool

The backend includes a CLI tool (`cli_tool.py`) for various operations. To use it, you can run commands within the running Docker container for the backend service.

The service name in `docker-compose.yml` is `pulseway-backend`.
The `Dockerfile` copies the local `./backend/` directory to `/app/` inside the container (e.g. `backend/app/cli_tool.py` becomes `/app/app/cli_tool.py`).
The `WORKDIR` in the Docker container is set to `/app`.

Therefore, the command to execute the CLI tool (run from the project root) is:
```bash
docker-compose exec pulseway-backend python app/cli_tool.py [COMMANDS]
```
Example: List devices
```bash
docker-compose exec pulseway-backend python app/cli_tool.py devices list
```

## Utility Scripts

The `scripts/` directory contains helper scripts for common operations:

-   `scripts/start.sh`: Starts the application services using `docker-compose`. Includes checks for `.env` and Docker.
    ```bash
    ./scripts/start.sh
    ```
-   `scripts/backup.sh`: Creates a compressed backup of the application data (from the Docker named volume `pulseway_data` and the `.env` file) into the `backups/` directory. These scripts now correctly target the Docker volume for database persistence.
    ```bash
    ./scripts/backup.sh
    ```
-   `scripts/restore.sh <backup_file_path>`: Restores application data (to the Docker named volume `pulseway_data` and the `.env` file) from a specified backup file. Stops services, extracts data, and restarts services.
    ```bash
    ./scripts/restore.sh backups/pulseway_backup_YYYYMMDD_HHMMSS.tar.gz
    ```
    *Ensure the scripts are executable: `chmod +x scripts/*.sh`*

## Testing

This project includes several types of tests to ensure code quality and functionality.

### Prerequisites for Running Tests

- **Python Environment**: Ensure Python is installed. It's recommended to use a virtual environment.
- **Install Dependencies**: From the project root directory, install necessary Python packages:
  ```bash
  pip install -r requirements.txt
  ```
  This file includes `pytest`, `pytest-asyncio` (for API integration tests), and `locust` (for load tests).
- **Docker**: For tests involving Docker (like backup/restore script tests), ensure Docker is installed and running.
- **Working Directory**: Most test commands below assume your current working directory is `backend/`.

### Unit Tests

Unit tests focus on individual components, primarily services. We use Python's `unittest` framework.

- **DeviceService Unit Tests**:
  These tests for `backend/app/services/device_service.py` are located in `backend/tests/unit/test_device_service.py`. They use extensive mocking for database and Pulseway client interactions.
  To run them, navigate to the `backend` directory and use:
  ```bash
  python -m unittest tests/unit/test_device_service.py
  ```
  Or, to discover and run all unit tests in the `tests/unit` directory:
  ```bash
  python -m unittest discover -s tests/unit -p "test_*.py"
  ```

### Integration Tests

Integration tests verify interactions between different parts of the application, such as API endpoints and the database, or external scripts and Docker. These tests typically use `pytest`.

- **Database Operations Tests**:
  Located in `backend/tests/integration/test_database_operations.py`, these tests verify CRUD operations and relationships for the SQLAlchemy models against an in-memory SQLite database.
  To run (assuming `pytest` is installed and you are in the `backend` directory):
  ```bash
  pytest tests/integration/test_database_operations.py
  ```

- **API Endpoint Tests**:
  These tests are in `backend/tests/integration/` with filenames like `test_api_devices.py`, `test_api_monitoring.py`, `test_api_scripts.py`, and `test_api_main.py`. They use FastAPI's `TestClient` to make requests to the API endpoints and verify responses against an in-memory SQLite database.
  To run all API integration tests (from the `backend` directory):
  ```bash
  pytest tests/integration/
  ```
  To run a specific file:
  ```bash
  pytest tests/integration/test_api_devices.py
  ```

- **Backup and Restore Script Tests**:
  The test script `backend/tests/integration/test_backup_restore_scripts.sh` verifies the functionality of `scripts/backup.sh` and `scripts/restore.sh`. This test involves Docker volume manipulation and requires Docker to be running.
  To run (from the `backend` directory):
  ```bash
  bash tests/integration/test_backup_restore_scripts.sh
  ```
  *Ensure this test script has execute permissions (`chmod +x tests/integration/test_backup_restore_scripts.sh`)*.

### Load Tests

Basic load testing is set up using Locust. The test definitions are in `backend/load_tests/locustfile.py`.

1.  **Install Locust**:
    Ensure Locust is installed (it's included in `requirements.txt`):
    ```bash
    pip install locust
    ```
2.  **Run Locust**:
    Navigate to the `backend` directory. You need to run the main application first, as Locust acts as a client.
    Start the backend application (e.g., using Docker as described in "Running the Application").
    Then, run Locust (from the `backend` directory):
    ```bash
    locust -f load_tests/locustfile.py --host=http://localhost:8000
    ```
    Open your web browser and go to `http://localhost:8089` (or the URL Locust provides) to start the test and view results.
    The `locustfile.py` is configured to use an API key for requests. Ensure the API key (`your-secret-key-here` by default in the locustfile, or one set via `PULSEWAY_API_KEY` environment variable if you modify the locustfile) is valid for your running backend instance.

## Frontend

The frontend application is located in the `/frontend` directory. It consists of static HTML, CSS, and JavaScript files, along with PWA assets (`pwa-manifest.json`, `pwa-service-worker.js`).

Currently, these static files are **not automatically served** by the FastAPI backend defined in `backend/app/main.py`.
To use the frontend:
- You might need to configure a separate web server (like Nginx) to serve the files from the `frontend/` directory.
- Or, for simple local viewing, you can open `frontend/index.html` directly in your browser (though API interactions might be limited by browser security policies if not served from the same origin as the backend).
- The file `backend/app/fastapi-pwa-integration.py` contains an alternative FastAPI setup that *does* include static file serving. This might be integrated into the main application in the future or used as a reference.

(Further setup and build instructions for the frontend would depend on its specific technologies and how it's intended to be served).
