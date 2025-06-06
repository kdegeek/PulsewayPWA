import pytest
from backend.app.exceptions import (
    AppException,
    DatabaseError,
    ExternalAPIError,
    AuthenticationError,
    NotFoundError,
    BusinessLogicError
)

def test_app_exception_defaults():
    """Test AppException default values."""
    exc = AppException()
    assert exc.detail == "An application error occurred."
    assert exc.status_code == 500
    assert isinstance(exc, Exception)

def test_app_exception_custom_message_and_code():
    """Test AppException with custom detail and status_code."""
    custom_detail = "Custom error detail"
    custom_code = 418
    exc = AppException(detail=custom_detail, status_code=custom_code)
    assert exc.detail == custom_detail
    assert exc.status_code == custom_code

@pytest.mark.parametrize("exc_class, default_detail, default_code", [
    (DatabaseError, "A database error occurred.", 500),
    (ExternalAPIError, "An external API error occurred.", 502),
    (AuthenticationError, "Authentication failed.", 401),
    (NotFoundError, "Resource not found.", 404),
    (BusinessLogicError, "A business logic error occurred.", 400),
])
def test_specific_exception_defaults(exc_class, default_detail, default_code):
    """Test default values for specific exception classes."""
    exc = exc_class()
    assert exc.detail == default_detail
    assert exc.status_code == default_code
    assert isinstance(exc, AppException) # Check inheritance

@pytest.mark.parametrize("exc_class", [
    DatabaseError, ExternalAPIError, AuthenticationError, NotFoundError, BusinessLogicError
])
def test_specific_exception_custom_message_and_code(exc_class):
    """Test specific exception classes with custom detail and status_code."""
    custom_detail = "Specific custom error"
    custom_code = 422 # Unprocessable Entity, as an example

    exc = exc_class(detail=custom_detail, status_code=custom_code)
    assert exc.detail == custom_detail
    assert exc.status_code == custom_code
    assert isinstance(exc, AppException)

def test_exception_inheritance():
    """Explicitly check inheritance for all custom exceptions."""
    assert issubclass(DatabaseError, AppException)
    assert issubclass(ExternalAPIError, AppException)
    assert issubclass(AuthenticationError, AppException)
    assert issubclass(NotFoundError, AppException)
    assert issubclass(BusinessLogicError, AppException)
    assert not issubclass(AppException, DatabaseError) # Ensure base is not subclass

# Example of raising and catching (more for demonstrating usage, but good for sanity check)
def some_function_that_raises(error_type, detail, code):
    raise error_type(detail=detail, status_code=code)

def test_raising_specific_exception():
    detail = "Test Detail"
    code = 403
    with pytest.raises(AuthenticationError) as excinfo:
        some_function_that_raises(AuthenticationError, detail, code)

    assert excinfo.value.detail == detail
    assert excinfo.value.status_code == code

# pytest backend/tests/unit/test_exceptions.py
