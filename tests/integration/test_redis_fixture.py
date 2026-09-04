"""Test to check if redis fixture works."""
from __future__ import annotations

import pytest


def test_redis_fixture(redis_container):
    """Just check that we get the redis fixture."""
    print("Type of redis_container:", type(redis_container))
    print("Redis container:", redis_container)