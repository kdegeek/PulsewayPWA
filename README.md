# Pulseway Project

This repository contains the backend and frontend components for a Pulseway monitoring dashboard and management tool.

## Project Structure

The repository is organized as follows:

- `/backend`: Contains the Python FastAPI backend application, including API endpoints, services, and database models.
  - `/backend/app`: The main application code.
- `/frontend`: Contains the frontend application files (HTML, TSX, PWA assets).
- `/docs`: Contains detailed documentation, including the original project READMEs and architecture descriptions.
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
    Edit the `.env` file with your details.

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

## Detailed Documentation

For more detailed information on the backend API, PWA frontend, architecture, and CLI usage, please refer to the documents in the `/docs` directory:
- `docs/readme_documentation.md` (Original comprehensive backend README)
- `docs/complete-project-structure.md` (Original PWA structure and details)
- `docs/docker-configuration.md` (Original Docker setup notes)

## CLI Tool

The backend includes a CLI tool (`cli_tool.py`) for various operations. To use it, you can run commands within the running Docker container for the backend service.

The service name in `docker-compose.yml` is `pulseway-backend`.
The `Dockerfile` copies the local `./backend/` directory to `/app/` inside the container. Thus, the script located at `./backend/app/cli_tool.py` locally will be at `/app/app/cli_tool.py` inside the container.
The `WORKDIR` in the Docker container is set to `/app`.

Therefore, the command to execute the CLI tool is:
```bash
docker-compose exec pulseway-backend python app/cli_tool.py [COMMANDS]
```
Example: List devices
```bash
docker-compose exec pulseway-backend python app/cli_tool.py devices list
```

## Frontend

The frontend application is located in the `/frontend` directory. It includes HTML files, a TSX file (likely for a React-based PWA), and PWA assets like `pwa-manifest.json` and `pwa-service-worker.js`.
(Further setup and build instructions for the frontend would depend on its specific technologies, e.g., Node.js, npm/yarn, and how it's intended to be served - either by the Python backend or a separate web server).
