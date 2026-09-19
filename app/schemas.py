from typing import Literal

from pydantic import BaseModel, ConfigDict


class ServerCreate(BaseModel):
    """Schema for the request body when registering a new server."""

    hostname: str
    os_type: Literal["linux", "windows"]
    container_name: str


class ServerResponse(BaseModel):
    """Schema for the response when returning server data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    hostname: str
    os_type: str
    container_name: str


class SetupResponse(BaseModel):
    """Schema for the response after running a setup script."""

    status: str
    message: str


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    status: str
    message: str
