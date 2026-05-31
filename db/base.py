"""Shared SQLAlchemy declarative base.

Kept in its own module so that ORM models and the engine setup can both import
it without creating circular import dependencies.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
