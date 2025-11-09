"""Custom exceptions for AI Forum"""


class AIForumException(Exception):
    """Base exception for all AI Forum errors"""
    pass


class NotFoundError(AIForumException):
    """Resource not found in database"""
    pass


class AuthenticationError(AIForumException):
    """Authentication failed (invalid API key, expired challenge, etc.)"""
    pass


class ValidationError(AIForumException):
    """Input validation failed"""
    pass


class ChallengeExpiredError(AuthenticationError):
    """Challenge has expired"""
    pass


class InvalidChallengeResponseError(AuthenticationError):
    """Challenge response is incorrect"""
    pass


class DuplicateError(AIForumException):
    """Attempted to create duplicate resource"""
    pass
