from sqlalchemy import Column, Integer, String

from app.database import Base


class Server(Base):
    """ORM model representing a managed server in the fleet."""

    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, nullable=False)
    os_type = Column(String, nullable=False)
    container_name = Column(String, nullable=False)
