"""Engine package.

Importing this package populates the topic registry, so any consumer that
imports ``gca.engine`` gets the full drill topic list.
"""

from __future__ import annotations

from gca.engine import topics as _topics  # noqa: F401  (populates the registry)
