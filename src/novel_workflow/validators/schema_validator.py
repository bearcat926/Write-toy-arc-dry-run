from ..config import SUPPORTED_SCHEMA_VERSIONS


class SchemaValidator:
    def validate(self, data: dict) -> bool:
        version = data.get("schema_version")
        if version is None:
            raise ValueError("MISSING_SCHEMA_VERSION")
        if version not in SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError(f"UNKNOWN_SCHEMA_VERSION: {version}")
        return True
