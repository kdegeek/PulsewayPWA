# backend/app/exceptions.py

class AppException(Exception):
    """Base class for application-specific exceptions."""
    def __init__(self, detail: str = "An application error occurred.", status_code: int = 500):
        self.detail = detail
        self.status_code = status_code
        super().__init__(self.detail)

class DatabaseError(AppException):
    """Raised when a database operation fails."""
    def __init__(self, detail: str = "A database error occurred.", status_code: int = 500):
        super().__init__(detail, status_code)

class ExternalAPIError(AppException):
    """Raised when an external API call fails."""
    def __init__(self, detail: str = "An external API error occurred.", status_code: int = 502): # 502 Bad Gateway is often appropriate
        super().__init__(detail, status_code)

class AuthenticationError(AppException):
    """Raised for authentication or authorization failures not directly handled by HTTPExceptions."""
    def __init__(self, detail: str = "Authentication failed.", status_code: int = 401):
        super().__init__(detail, status_code)

class NotFoundError(AppException):
    """Raised when a resource is not found."""
    def __init__(self, detail: str = "Resource not found.", status_code: int = 404):
        super().__init__(detail, status_code)

class BusinessLogicError(AppException):
    """Raised for errors in business logic that don't fit other categories."""
    def __init__(self, detail: str = "A business logic error occurred.", status_code: int = 400): # Often a 400 Bad Request
        super().__init__(detail, status_code)
