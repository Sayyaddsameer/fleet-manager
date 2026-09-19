import json
import logging
import subprocess
from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Server
from app.schemas import ErrorResponse, ServerCreate, ServerResponse, SetupResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
    yield


app = FastAPI(
    title="Fleet Manager Orchestrator",
    description="Central API for managing and monitoring a mixed fleet of Linux and Windows servers.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health endpoint (used by Docker health check)
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    """Simple liveness probe for the orchestrator itself."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Server registration and listing
# ---------------------------------------------------------------------------

@app.post("/api/servers", response_model=ServerResponse, status_code=201)
def register_server(server_data: ServerCreate, db: Session = Depends(get_db)):
    """Register a new server in the fleet inventory."""
    new_server = Server(
        hostname=server_data.hostname,
        os_type=server_data.os_type,
        container_name=server_data.container_name,
    )
    db.add(new_server)
    db.commit()
    db.refresh(new_server)
    return new_server


@app.get("/api/servers", response_model=List[ServerResponse])
def list_servers(db: Session = Depends(get_db)):
    """List all registered servers from the fleet inventory."""
    servers = db.query(Server).all()
    return servers


# ---------------------------------------------------------------------------
# Helper: look up a server or raise 404
# ---------------------------------------------------------------------------

def _get_server_or_404(server_id: int, db: Session) -> Server:
    """Retrieve a server by its primary key, raising HTTP 404 if not found."""
    server = db.query(Server).filter(Server.id == server_id).first()
    if server is None:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "message": "Server not found"},
        )
    return server


# ---------------------------------------------------------------------------
# Helper: execute a script inside a target container via docker exec
# ---------------------------------------------------------------------------

def _run_script_on_container(container_name: str, os_type: str, script_name: str) -> subprocess.CompletedProcess:
    """
    Build and run a docker exec command to execute the given script
    inside the specified container.

    For linux containers the command is:
        docker exec <container> bash /scripts/<script_name>

    For windows containers:
        docker exec <container> powershell -File C:\\scripts\\<script_name>
    """
    if os_type == "linux":
        command = [
            "docker", "exec", container_name,
            "bash", f"/scripts/{script_name}",
        ]
    else:
        command = [
            "docker", "exec", container_name,
            "powershell", "-File", f"C:\\scripts\\{script_name}",
        ]

    logger.info("Executing command: %s", " ".join(command))

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return result


# ---------------------------------------------------------------------------
# Setup endpoint
# ---------------------------------------------------------------------------

@app.post(
    "/api/servers/{server_id}/setup",
    response_model=SetupResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def trigger_setup(server_id: int, db: Session = Depends(get_db)):
    """
    Trigger the setup script on the target server.

    Determines the correct script based on the server's OS type and
    executes it inside the corresponding container using docker exec.
    """
    server = _get_server_or_404(server_id, db)

    script_name = "setup.sh" if server.os_type == "linux" else "setup.ps1"

    try:
        result = _run_script_on_container(
            container_name=server.container_name,
            os_type=server.os_type,
            script_name=script_name,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Setup script timed out for server {server.hostname}",
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Failed to execute setup script: {str(exc)}",
            },
        )

    if result.returncode != 0:
        error_output = result.stderr.strip() if result.stderr else result.stdout.strip()
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Setup script failed for server {server.hostname}: {error_output}",
            },
        )

    return SetupResponse(
        status="success",
        message=f"Setup script executed successfully for server {server.hostname}",
    )


# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------

@app.get(
    "/api/servers/{server_id}/health",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_server_health(server_id: int, db: Session = Depends(get_db)):
    """
    Run the health check script on the target server and return its
    JSON output directly.

    The health check script is expected to print a single line of valid
    JSON to standard output.
    """
    server = _get_server_or_404(server_id, db)

    script_name = "health_check.sh" if server.os_type == "linux" else "health_check.ps1"

    try:
        result = _run_script_on_container(
            container_name=server.container_name,
            os_type=server.os_type,
            script_name=script_name,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Health check script timed out for server {server.hostname}",
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Failed to execute health check script: {str(exc)}",
            },
        )

    if result.returncode != 0:
        error_output = result.stderr.strip() if result.stderr else result.stdout.strip()
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Health check script failed for server {server.hostname}: {error_output}",
            },
        )

    # Parse the script's stdout as JSON and return it directly
    stdout = result.stdout.strip()
    try:
        health_data = json.loads(stdout)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Health check output is not valid JSON: {stdout[:500]}",
            },
        )

    return health_data
