"""
Named startup / runtime errors for required third-party source keys.

Missing keys must FAIL LOUD — never silently skip the source.
"""


class MissingSynapseApiTokenError(RuntimeError):
    """SYNAPSE_API_TOKEN is not configured."""


def validate_required_source_keys(*, require: bool) -> None:
    """
    Raise named errors when required keys are absent.

    Called at app startup when running in production (or when
    LENA_REQUIRE_SOURCE_KEYS=1). Development/tests may omit keys; the
    individual source modules still raise these errors at query time
    instead of returning empty results silently.
    """
    if not require:
        return

    from app.core.config import settings

    if not settings.synapse_api_token:
        raise MissingSynapseApiTokenError(
            "SYNAPSE_API_TOKEN is required. Refusing to start — "
            "set the environment variable (fail-loud source policy)."
        )
