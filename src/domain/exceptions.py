"""Domain exceptions for the Personal Semantic Engine."""

from uuid import UUID


class DomainError(Exception):
    """Base exception for domain layer errors."""

    pass


class ThoughtNotFoundError(DomainError):
    """Raised when a thought cannot be found."""

    def __init__(self, thought_id: UUID):
        super().__init__(f"Thought with ID {thought_id} not found")
        self.thought_id = thought_id


class UserNotFoundError(DomainError):
    """Raised when a user cannot be found."""

    def __init__(self, user_id: UUID = None, email: str = None):
        if user_id:
            super().__init__(f"User with ID {user_id} not found")
            self.user_id = user_id
        elif email:
            super().__init__(f"User with email {email} not found")
            self.email = email
        else:
            super().__init__("User not found")


class EntityExtractionError(DomainError):
    """Raised when entity extraction fails."""

    def __init__(self, message: str):
        super().__init__(f"Entity extraction failed: {message}")


class EmbeddingError(DomainError):
    """Raised when embedding generation fails."""

    def __init__(self, message: str):
        super().__init__(f"Embedding generation failed: {message}")


class VectorStoreError(DomainError):
    """Raised when vector storage or retrieval fails."""

    def __init__(self, message: str):
        super().__init__(f"Vector store operation failed: {message}")


class AuthenticationError(DomainError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message)


class SearchError(DomainError):
    """Raised when search operations fail."""

    def __init__(self, message: str):
        super().__init__(f"Search operation failed: {message}")


class SearchQueryError(DomainError):
    """Raised when search query parsing or validation fails."""

    def __init__(self, message: str):
        super().__init__(f"Search query error: {message}")


class SearchIndexError(DomainError):
    """Raised when search indexing operations fail."""

    def __init__(self, message: str):
        super().__init__(f"Search indexing failed: {message}")


class SearchRankingError(DomainError):
    """Raised when search result ranking fails."""

    def __init__(self, message: str):
        super().__init__(f"Search ranking failed: {message}")


class UserAlreadyExistsError(DomainError):
    """Raised when attempting to create a user that already exists."""

    def __init__(self, email: str):
        super().__init__(f"User with email {email} already exists")
        self.email = email


class UserRegistrationError(DomainError):
    """Raised when user registration fails."""

    def __init__(self, message: str):
        super().__init__(f"User registration failed: {message}")


class UserManagementError(DomainError):
    """Raised when user management operations fail."""

    def __init__(self, message: str):
        super().__init__(f"User management operation failed: {message}")


class TokenError(DomainError):
    """Raised when token operations fail."""

    def __init__(self, message: str):
        super().__init__(f"Token operation failed: {message}")


class InvalidTokenError(TokenError):
    """Raised when a token is invalid or expired."""

    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message)


class TimelineError(DomainError):
    """Raised when timeline operations fail."""

    def __init__(self, message: str):
        super().__init__(f"Timeline operation failed: {message}")


class TimelineQueryError(DomainError):
    """Raised when timeline query parsing or validation fails."""

    def __init__(self, message: str):
        super().__init__(f"Timeline query error: {message}")


class TimelineGroupingError(DomainError):
    """Raised when timeline entry grouping fails."""

    def __init__(self, message: str):
        super().__init__(f"Timeline grouping failed: {message}")
