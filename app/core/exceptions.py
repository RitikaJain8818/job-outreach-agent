from __future__ import annotations


class OutreachAgentError(Exception):
    """Base exception for all application errors."""


class ConfigurationError(OutreachAgentError):
    """Raised when required configuration is missing or invalid."""


class DatabaseError(OutreachAgentError):
    """Raised on unrecoverable database operation failures."""


class LLMProviderError(OutreachAgentError):
    """Raised when an LLM provider call fails."""


class GmailError(OutreachAgentError):
    """Raised when a Gmail API operation fails."""


class GmailAuthError(GmailError):
    """Raised when Gmail authentication fails or credentials are missing."""


class GmailRateLimitError(GmailError):
    """Raised when Gmail API rate limit is hit (429). Caller should retry with backoff."""


class OutreachError(OutreachAgentError):
    """Raised during outreach pipeline failures (send, follow-up, etc.)."""


class AgentError(OutreachAgentError):
    """Raised when an agent encounters an unrecoverable error."""


class ContactNotFoundError(OutreachAgentError):
    """Raised when a referenced contact does not exist."""


class CompanyNotFoundError(OutreachAgentError):
    """Raised when a referenced company does not exist."""


class CampaignNotFoundError(OutreachAgentError):
    """Raised when a referenced campaign does not exist."""


class DuplicateTargetError(OutreachAgentError):
    """Raised when a contact is added to a campaign more than once."""
