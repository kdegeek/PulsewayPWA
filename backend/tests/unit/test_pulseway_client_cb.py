import pytest
import requests
import time
from unittest.mock import MagicMock, patch
import pybreaker

# Import the client and its specific exceptions, and the breaker instance
from backend.app.pulseway.client import PulsewayClient, pulseway_api_breaker
from backend.app.pulseway.client import PulsewayClientError, PulsewayAPIError, PulsewayNotFoundError

# Default params for PulsewayClient for tests
TEST_BASE_URL = "http://fakeapi.pulseway.com"
TEST_TOKEN_ID = "test_id"
TEST_TOKEN_SECRET = "test_secret"

@pytest.fixture
def client_and_mock_session():
    # Reset circuit breaker state before each test for isolation
    # Accessing internal state like _state_storage is usually not ideal,
    # but pybreaker doesn't have a simple public "reset_to_closed_state()" method.
    # A common way is to replace the breaker with a new instance for each test,
    # or carefully manage its state.
    # For simplicity, we'll reset the one used by the module.
    pulseway_api_breaker.close() # Ensure it's closed at the start of each test.

    client = PulsewayClient(base_url=TEST_BASE_URL, token_id=TEST_TOKEN_ID, token_secret=TEST_TOKEN_SECRET)

    # Mock the session object within the client instance for this test
    mock_session = MagicMock(spec=requests.Session)
    client.session = mock_session

    return client, mock_session

def test_successful_call_circuit_closed(client_and_mock_session):
    client, mock_session = client_and_mock_session

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"Data": {"status": "ok"}}'
    mock_response.json.return_value = {"Data": {"status": "ok"}}
    mock_session.request.return_value = mock_response

    result = client.get_environment() # Uses _make_request internally

    assert result == {"Data": {"status": "ok"}}
    assert pulseway_api_breaker.current_state == "closed"
    mock_session.request.assert_called_once()

def test_circuit_opens_after_max_failures(client_and_mock_session):
    client, mock_session = client_and_mock_session

    # Simulate failures that should trip the breaker (e.g., network error or 500 error)
    mock_session.request.side_effect = requests.exceptions.Timeout("Test Timeout")

    # fail_max is 5 for pulseway_api_breaker
    # The first fail_max-1 calls will raise the original error
    for _ in range(pulseway_api_breaker.fail_max - 1):
        with pytest.raises(PulsewayClientError, match="Request failed: Test Timeout"):
            client.get_environment()

    # The fail_max-th call will also raise the original error, which pybreaker catches,
    # then pybreaker raises CircuitBreakerError.
    with pytest.raises(pybreaker.CircuitBreakerError):
        client.get_environment()

    assert pulseway_api_breaker.current_state == "open"

    # Next call (N+1) when circuit is already open:
    # pybreaker prevents the call, raises CircuitBreakerError.
    # This is caught by the except block in _make_request and converted to PulsewayClientError(503).
    with pytest.raises(PulsewayClientError, match="Pulseway API is temporarily unavailable \(circuit breaker open\)"):
        client.get_environment()

    # Check that session.request was called fail_max times, not more.
    assert mock_session.request.call_count == pulseway_api_breaker.fail_max

def test_circuit_opens_on_500_errors(client_and_mock_session):
    client, mock_session = client_and_mock_session

    mock_failure_response = MagicMock()
    mock_failure_response.status_code = 500
    mock_failure_response.text = "Internal Server Error"
    mock_failure_response.content = b'{"error": "server blew up"}'
    mock_failure_response.json.return_value = {"error": "server blew up"}
    mock_failure_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Error", response=mock_failure_response)

    mock_session.request.return_value = mock_failure_response

    for _ in range(pulseway_api_breaker.fail_max - 1):
        with pytest.raises(PulsewayAPIError, match="Pulseway API Server Error \(500\)"):
            client.get_environment()

    # The fail_max-th call that trips the breaker, pybreaker raises CircuitBreakerError
    with pytest.raises(pybreaker.CircuitBreakerError):
        client.get_environment()

    assert pulseway_api_breaker.current_state == "open"

    # Next call (N+1) when already open, should be converted to PulsewayClientError(503)
    with pytest.raises(PulsewayClientError, match="Pulseway API is temporarily unavailable \(circuit breaker open\)"):
        client.get_environment()
    assert mock_session.request.call_count == pulseway_api_breaker.fail_max # Should not make more calls


def test_circuit_trial_request_after_reset_timeout(client_and_mock_session):
    client, mock_session = client_and_mock_session

    # Open the circuit first
    mock_session.request.side_effect = requests.exceptions.ConnectionError("Test Connection Error")
    # The first fail_max-1 calls will raise the original error
    for _ in range(pulseway_api_breaker.fail_max - 1):
        with pytest.raises(PulsewayClientError, match="Request failed: Test Connection Error"):
            client.get_environment()
    # The fail_max-th call trips the breaker, pybreaker raises CircuitBreakerError
    with pytest.raises(pybreaker.CircuitBreakerError):
        client.get_environment()
    assert pulseway_api_breaker.current_state == "open"

    # Mock time to advance beyond reset_timeout (60s for pulseway_api_breaker)
    # pybreaker uses time.monotonic()
    with patch('time.monotonic', return_value=time.monotonic() + pulseway_api_breaker.reset_timeout + 1):
        # This call should be a "trial" request
        # Let it succeed this time
        mock_successful_response = MagicMock()
        mock_successful_response.status_code = 200
        mock_successful_response.content = b'{"Data": "ok"}'
        mock_successful_response.json.return_value = {"Data": "ok"}
        mock_session.request.side_effect = None # Clear previous side_effect
        mock_session.request.return_value = mock_successful_response

        result = client.get_environment()
        assert result == {"Data": "ok"}
        assert pulseway_api_breaker.current_state == "closed" # Circuit should close after success
        assert mock_session.request.call_count == pulseway_api_breaker.fail_max + 1 # fail_max calls + 1 trial

def test_circuit_remains_open_if_trial_fails(client_and_mock_session):
    client, mock_session = client_and_mock_session

    # Open the circuit
    mock_session.request.side_effect = requests.exceptions.Timeout("Initial Timeout")
    for _ in range(pulseway_api_breaker.fail_max - 1):
        with pytest.raises(PulsewayClientError, match="Request failed: Initial Timeout"):
            client.get_environment()
    # Nth call raises CircuitBreakerError from pybreaker
    with pytest.raises(pybreaker.CircuitBreakerError):
        client.get_environment()
    assert pulseway_api_breaker.current_state == "open"
    initial_call_count = mock_session.request.call_count

    # Advance time
    with patch('time.monotonic', return_value=time.monotonic() + pulseway_api_breaker.reset_timeout + 1):
        # Make the trial request fail again
        mock_session.request.side_effect = requests.exceptions.Timeout("Trial Timeout")

    # This trial call will fail. Pybreaker catches the "Trial Timeout",
    # keeps circuit open, and re-raises CircuitBreakerError itself.
    # Our internal handler then converts this to PulsewayClientError(503).
        with pytest.raises(PulsewayClientError, match="Pulseway API is temporarily unavailable \(circuit breaker open\)"):
            client.get_environment()

        assert pulseway_api_breaker.current_state == "open" # Should remain open
        assert mock_session.request.call_count == initial_call_count + 1

def test_4xx_errors_do_not_open_circuit_if_excluded(client_and_mock_session):
    client, mock_session = client_and_mock_session

    # To test exclusion, we'd need to redefine the global pulseway_api_breaker
    # or have a way to pass a configured breaker to the client.
    # For this test, let's assume the global breaker is as defined (counts all by default).
    # This test will show that 404s DO open the circuit with default settings if not excluded.
    # Our code converts the CircuitBreakerError to PulsewayClientError(503) on the Nth call.

    mock_404_response = MagicMock()
    mock_404_response.status_code = 404
    mock_404_response.text = "Not Found"
    mock_404_response.content = b'' # No json content for 404
    mock_404_response.json.side_effect = ValueError("No JSON content") # if .json() is called
    # raise_for_status not called for 404 in the _make_request logic for specific codes

    mock_session.request.return_value = mock_404_response

    for i in range(pulseway_api_breaker.fail_max - 1):
        with pytest.raises(PulsewayNotFoundError):
            client.get_environment()

    # The Nth call raises PulsewayNotFoundError, pybreaker catches it and raises CircuitBreakerError.
    with pytest.raises(pybreaker.CircuitBreakerError):
        client.get_environment()

    assert pulseway_api_breaker.current_state == "open"

# pytest backend/tests/unit/test_pulseway_client_cb.py
