"""Utilities for configuring Flask runtime environment variables.

This helper aligns the default host and port used by the ``flask run``
command with the values expected by hosting providers such as Railway.
By default the Flask CLI listens on ``127.0.0.1:5000``, which prevents
external connections when deployed. Railway exposes the application
through the port specified in the ``PORT`` environment variable, so we
mirror that value into ``FLASK_RUN_PORT`` and force the host to
``0.0.0.0`` when they are not explicitly configured.
"""

from __future__ import annotations

import os

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
PORT_ENV_NAME = "PORT"
FLASK_HOST_ENV_NAME = "FLASK_RUN_HOST"
FLASK_PORT_ENV_NAME = "FLASK_RUN_PORT"


def configure_flask_environment(*, default_port: int = DEFAULT_PORT) -> int:
    """Ensure Flask binds to the externally visible host and port.

    Parameters
    ----------
    default_port:
        Port value used when the ``PORT`` environment variable is absent or
        malformed. The same value is also written to ``FLASK_RUN_PORT`` when
        it is not explicitly configured.

    Returns
    -------
    int
        The integer port that should be used by the application server.
    """

    raw_port = os.environ.get(PORT_ENV_NAME, "").strip()
    port = default_port

    if raw_port:
        try:
            port = int(raw_port)
        except ValueError:
            port = default_port
    else:
        os.environ.setdefault(PORT_ENV_NAME, str(default_port))

    os.environ.setdefault(FLASK_PORT_ENV_NAME, str(port))
    os.environ.setdefault(FLASK_HOST_ENV_NAME, DEFAULT_HOST)

    return port
