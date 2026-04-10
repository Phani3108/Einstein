"""Connector package — imports trigger self-registration with ConnectorRegistry."""

from src.infrastructure.connectors.registry import ConnectorRegistry  # noqa: F401

try:
    from src.infrastructure.connectors import gmail_connector  # noqa: F401
except Exception:
    pass

try:
    from src.infrastructure.connectors import outlook_connector  # noqa: F401
except Exception:
    pass

try:
    from src.infrastructure.connectors import slack_connector  # noqa: F401
except Exception:
    pass

try:
    from src.infrastructure.connectors import jira_connector  # noqa: F401
except Exception:
    pass

try:
    from src.infrastructure.connectors import github_connector  # noqa: F401
except Exception:
    pass

try:
    from src.infrastructure.connectors import zoom_connector  # noqa: F401
except Exception:
    pass

try:
    from src.infrastructure.connectors import linear_connector  # noqa: F401
except Exception:
    pass

try:
    from src.infrastructure.connectors import telegram_connector  # noqa: F401
except Exception:
    pass
