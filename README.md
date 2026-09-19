# Fleet Manager

A fleet management system that automates the setup and health monitoring of a mixed fleet of Linux and Windows servers. Built with a central FastAPI orchestrator, PostgreSQL for inventory tracking, and Docker Compose for environment management.

## What This Project Does

In production environments, teams manage dozens or hundreds of servers running different operating systems. Manually configuring each one and checking its health is tedious and error-prone. This project solves that by providing a single API that can:

- Register servers into a central inventory.
- Trigger automated setup scripts on any registered server.
- Collect real-time health metrics from any server on demand.

The orchestrator determines whether a target is Linux or Windows, picks the correct script (Bash or PowerShell), and executes it remotely inside the target container using `docker exec`. All of this is defined in Docker Compose so the entire environment can be reproduced with one command.

## Architecture

```
                          +---------------------+
                          |   User / Admin      |
                          |   (curl, Postman)   |
                          +---------+-----------+
                                    |
                               HTTP API Calls
                                    |
                          +---------v-----------+
                          |   Orchestrator API  |
                          |   (FastAPI, :8000)  |
                          +---------+-----------+
                           |                  |
                    docker exec          docker exec
                           |                  |
              +------------v---+    +---------v----------+
              | Linux Target   |    | Windows Target     |
              | (Ubuntu)       |    | (Server Core 2022) |
              | setup.sh       |    | setup.ps1          |
              | health_check.sh|    | health_check.ps1   |
              +----------------+    +--------------------+

              +--------------------------------------------+
              |            PostgreSQL Database              |
              |        (Server inventory storage)           |
              +--------------------------------------------+
```

All four services run inside a shared Docker network and communicate using container names as hostnames.

## Project Structure

```
fleet-manager/
├── docker-compose.yml        # Defines all 4 services with health checks
├── Dockerfile                # Builds the orchestrator image
├── .env                      # Active environment variables (not committed)
├── .env.example              # Template with placeholder values
├── .gitignore                # Git exclusions
├── submission.json           # Container name mapping for evaluation
├── requirements.txt          # Python dependencies
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI application and all route handlers
│   ├── database.py           # SQLAlchemy engine, session factory, dependency
│   ├── models.py             # Server ORM model
│   └── schemas.py            # Pydantic request/response schemas
└── scripts/
    ├── setup.sh              # Linux server setup (Bash)
    ├── health_check.sh       # Linux health metrics collector (Bash)
    ├── setup.ps1             # Windows server setup (PowerShell)
    └── health_check.ps1      # Windows health metrics collector (PowerShell)
```

## Prerequisites

- Docker and Docker Compose installed.
- For Windows target containers: Docker Desktop must be switched to Windows container mode on a Windows 10/11 Pro or Windows Server host.
- Git (for version control).

## Getting Started

1. Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/fleet-manager.git
cd fleet-manager
```

2. Create the environment file from the template:

```bash
cp .env.example .env
```

Edit `.env` if you want to change the default database credentials. The defaults work out of the box for local development.

3. Build and start all services:

```bash
docker-compose up --build -d
```

4. Wait about 30 seconds for health checks to pass, then verify:

```bash
docker-compose ps
```

All four services should show a healthy status.

## API Reference

The orchestrator runs on port 8000. All endpoints accept and return JSON.

### Health Probe

```
GET /health
```

Returns `{"status": "ok"}`. Used internally by Docker for container health checks.

### Register a Server

```
POST /api/servers
Content-Type: application/json

{
  "hostname": "linux-srv",
  "os_type": "linux",
  "container_name": "linux-target"
}
```

`os_type` must be either `linux` or `windows`.

Returns `201 Created` with the server record including its assigned `id`.

### List All Servers

```
GET /api/servers
```

Returns `200 OK` with an array of all registered server objects.

### Trigger Setup

```
POST /api/servers/{id}/setup
```

Runs the setup script on the target container. For Linux targets it executes `setup.sh`; for Windows targets it executes `setup.ps1`.

Returns `200 OK` on success:

```json
{
  "status": "success",
  "message": "Setup script executed successfully for server linux-srv"
}
```

### Get Health Metrics

```
GET /api/servers/{id}/health
```

Runs the health check script on the target and returns its JSON output directly.

Linux response example:

```json
{
  "os": "linux",
  "hostname": "abc123",
  "uptime_seconds": 84200,
  "cpu_usage_percent": 12.5,
  "memory_free_mb": 1024,
  "disk_free_root_gb": 38
}
```

Windows response example:

```json
{
  "os": "windows",
  "hostname": "WIN-SERVER",
  "uptime_seconds": 172800,
  "cpu_usage_percent": 8.3,
  "memory_free_mb": 2048,
  "disk_free_c_drive_gb": 45.2
}
```

### Error Responses

| Scenario | Status Code | Response Body |
|----------|-------------|---------------|
| Server ID not found | 404 | `{"status": "error", "message": "Server not found"}` |
| Script execution failure | 500 | `{"status": "error", "message": "<error details>"}` |
| Script timeout | 500 | `{"status": "error", "message": "<timeout details>"}` |
| Invalid JSON from script | 500 | `{"status": "error", "message": "<parse error details>"}` |

## What the Scripts Do

### Linux Setup (setup.sh)

- Updates package lists and installs `nginx`.
- Writes a timestamped entry to `/var/log/setup.log`.
- Creates a system user named `appadmin` (skips if it already exists).

The script is idempotent and safe to run multiple times.

### Linux Health Check (health_check.sh)

- Reads hostname from the `hostname` command.
- Parses uptime from `/proc/uptime`.
- Computes CPU usage by sampling `/proc/stat` twice, one second apart, and calculating the delta.
- Reads available memory from `free -m`.
- Reads free disk space on the root partition from `df`.
- Outputs everything as a single line of JSON.

### Windows Setup (setup.ps1)

- Creates the `C:\CompanyData` directory if it does not exist.
- Writes "Initial setup complete." to `C:\CompanyData\status.txt`.
- Creates a local user named `svcaccount` (skips if it already exists).

### Windows Health Check (health_check.ps1)

- Collects hostname from `$env:COMPUTERNAME`.
- Calculates uptime from the last boot time via `Win32_OperatingSystem`.
- Reads CPU load from `Win32_Processor`.
- Reads free physical memory from `Win32_OperatingSystem`.
- Reads free disk space on C: from `Get-Volume`.
- Outputs compressed JSON via `ConvertTo-Json -Compress`.

## Testing

After starting the environment, run through these steps to verify everything works:

```bash
# Register both servers
curl -X POST http://localhost:8000/api/servers \
  -H "Content-Type: application/json" \
  -d '{"hostname":"linux-srv","os_type":"linux","container_name":"linux-target"}'

curl -X POST http://localhost:8000/api/servers \
  -H "Content-Type: application/json" \
  -d '{"hostname":"windows-srv","os_type":"windows","container_name":"windows-target"}'

# List servers
curl http://localhost:8000/api/servers

# Run setup on both
curl -X POST http://localhost:8000/api/servers/1/setup
curl -X POST http://localhost:8000/api/servers/2/setup

# Check health on both
curl http://localhost:8000/api/servers/1/health
curl http://localhost:8000/api/servers/2/health

# Verify error handling
curl http://localhost:8000/api/servers/9999/health
```

To manually verify setup results inside the containers:

```bash
# Linux
docker exec linux-target dpkg -l | grep nginx
docker exec linux-target cat /var/log/setup.log
docker exec linux-target id appadmin

# Windows
docker exec windows-target powershell -Command "Test-Path C:\CompanyData"
docker exec windows-target powershell -Command "Get-Content C:\CompanyData\status.txt"
docker exec windows-target powershell -Command "Get-LocalUser -Name svcaccount"
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| POSTGRES_USER | Database username | fleet_user |
| POSTGRES_PASSWORD | Database password | changeme |
| POSTGRES_DB | Database name | fleet_db |
| DATABASE_URL | Full connection string | postgresql://fleet_user:changeme@db:5432/fleet_db |

## Limitations

- `docker exec` is used instead of SSH or Ansible. This works within the containerized setup but would not scale to production infrastructure.
- Docker Desktop cannot run Linux and Windows containers simultaneously in standard mode. The Windows target requires the daemon to be switched to Windows container mode.
- Health check data is not persisted. Each call runs the script fresh and returns the current snapshot.

## Future Improvements

- Add API authentication to prevent unauthorized access.
- Store health check results in the database to track historical trends.
- Add a lightweight dashboard to visualize server status.
- Replace `docker exec` with SSH-based execution for use outside of Docker.
- Add webhook or email notifications when health metrics exceed defined thresholds.

## License

This project is for educational purposes.
