"""Topic registry aggregation."""

from __future__ import annotations

from gca.engine.generate import REGISTRY, Topic

from gca.engine.topics import combi, expand, exponents, factoring, foundations, rational, words

for _module in (foundations, exponents, expand, factoring, rational, combi, words):
    for _topic in _module.TOPICS:
        REGISTRY[_topic.id] = _topic

__all__ = ["Topic"]
