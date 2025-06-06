import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request
from unittest.mock import patch, MagicMock

# Import the main FastAPI app and custom exceptions
from backend.app.main import app as main_app # Use the actual app
from backend.app.exceptions import (
    AppException,
    DatabaseError,
    ExternalAPIError,
    AuthenticationError,
    NotFoundError,
    BusinessLogicError
)

# It's tricky to add routes to an existing app for testing without modifying the app itself.
# A common pattern is to create a new FastAPI instance for testing specific routes,
# but here we want to test the main_app's exception handlers.
# So, we can make the main_app importable and then add test routes to it for the test session.
# This is generally acceptable for integration testing of handlers.

# Test routes to raise specific exceptions
# These will be added to the app for testing purposes.

@main_app.get("/test_exc/database_error")
async def route_raises_database_error():
    raise DatabaseError(detail="Test DB Error", status_code=503)

@main_app.get("/test_exc/external_api_error")
async def route_raises_external_api_error():
    raise ExternalAPIError(detail="Test External API Error", status_code=504)

@main_app.get("/test_exc/authentication_error")
async def route_raises_authentication_error():
    raise AuthenticationError(detail="Test Auth Error", status_code=401)

@main_app.get("/test_exc/not_found_error")
async def route_raises_not_found_error():
    raise NotFoundError(detail="Test Not Found Error", status_code=404)

@main_app.get("/test_exc/business_logic_error")
async def route_raises_business_logic_error():
    raise BusinessLogicError(detail="Test Business Logic Error", status_code=400)

@main_app.get("/test_exc/app_exception_generic")
async def route_raises_app_exception_generic():
    raise AppException(detail="Generic App Test Error", status_code=418)


client = TestClient(main_app)

@pytest.mark.parametrize("path, expected_status, expected_detail, exception_class_to_raise", [
    ("/test_exc/database_error", 503, "Test DB Error", DatabaseError),
    ("/test_exc/external_api_error", 504, "Test External API Error", ExternalAPIError),
    ("/test_exc/authentication_error", 401, "Test Auth Error", AuthenticationError),
    ("/test_exc/not_found_error", 404, "Test Not Found Error", NotFoundError),
    ("/test_exc/business_logic_error", 400, "Test Business Logic Error", BusinessLogicError),
    ("/test_exc/app_exception_generic", 418, "Generic App Test Error", AppException),
])
@patch("backend.app.main.sentry_sdk.capture_exception") # Mock sentry capture
def test_custom_exception_handler(
    mock_sentry_capture: MagicMock,
    path: str,
    expected_status: int,
    expected_detail: str,
    exception_class_to_raise: type # Used to check type passed to Sentry
):
    # Check if SENTRY_DSN is mocked or set to avoid conditional sentry calls if necessary
    # For this test, we assume SENTRY_DSN might be set or mock is effective globally.
    # If Sentry init is conditional on SENTRY_DSN, mock os.getenv("SENTRY_DSN") to return a dummy DSN.
    with patch('backend.app.main.SENTRY_DSN', 'dummy-dsn-for-test'): # Ensure Sentry capture is attempted
        response = client.get(path, headers={"X-API-Key": "your-secret-key-here"})

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}

    # Verify Sentry was called
    assert mock_sentry_capture.called
    # Check that it was called with an instance of the expected exception class
    args, kwargs = mock_sentry_capture.call_args
    assert len(args) == 1
    captured_exc = args[0]
    assert isinstance(captured_exc, exception_class_to_raise)
    assert captured_exc.detail == expected_detail
    assert captured_exc.status_code == expected_status

# pytest backend/tests/integration/test_main_exception_handling.py
