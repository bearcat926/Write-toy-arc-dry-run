from pydantic import BaseModel, Field
from datetime import datetime, timezone


class SchemaVersioned(BaseModel):
    schema_version: str = "1.0"


class Timestamped(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
