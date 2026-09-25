"""
Input validation and sanitization utilities.
"""
from pydantic import BaseModel, validator

class SecureBaseModel(BaseModel):
    """
    Base model with strict validation and sanitization.
    """
    class Config:
        # Enforce strict validation (e.g., forbid extra fields)
        extra = "forbid"
        # Use enum values only if defined
        use_enum_values = True
        # Validate assignment
        validate_assignment = True
        # Strip whitespace from strings
        anystr_strip_whitespace = True

    @validator("*", pre=True)
    def strip_whitespace(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value