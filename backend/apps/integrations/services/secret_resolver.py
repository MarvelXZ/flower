from typing import Protocol

from django.conf import settings


class SecretNotFound(LookupError):
    """Raised when a secret reference cannot be resolved."""


class SecretResolver(Protocol):
    def resolve_secret(self, secret_reference: str) -> str:
        """Resolve a secret reference into a secret value."""


class SettingsSecretResolver:
    """Test/dev resolver backed by Django settings.

    Production should replace this with Vault, KMS, or a cloud secret manager.
    """

    def resolve_secret(self, secret_reference: str) -> str:
        expected_reference = getattr(settings, "B2B_TEST_SECRET_REFERENCE", "")
        if secret_reference == expected_reference:
            secret = getattr(settings, "B2B_TEST_SHARED_SECRET", "")
            if secret:
                return secret

        secrets = getattr(settings, "B2B_TEST_SECRETS", {}) or {}
        if secret_reference in secrets and secrets[secret_reference]:
            return secrets[secret_reference]

        raise SecretNotFound("Secret reference could not be resolved.")


class InMemorySecretResolver:
    """Unit-test resolver backed by an in-memory mapping."""

    def __init__(self, secrets: dict[str, str]):
        self.secrets = dict(secrets)

    def resolve_secret(self, secret_reference: str) -> str:
        try:
            secret = self.secrets[secret_reference]
        except KeyError as exc:
            raise SecretNotFound("Secret reference could not be resolved.") from exc
        if not secret:
            raise SecretNotFound("Secret reference could not be resolved.")
        return secret


def resolve_secret(secret_reference: str, resolver: SecretResolver | None = None) -> str:
    active_resolver = resolver or SettingsSecretResolver()
    return active_resolver.resolve_secret(secret_reference)
