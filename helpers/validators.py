from fastapi import HTTPException

def validate_required_field(value: str, field_name: str):
    """
    Ensures a required string field is not empty/whitespace.
    """
    if not value or not value.strip():
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} is required"
        )
    return value
