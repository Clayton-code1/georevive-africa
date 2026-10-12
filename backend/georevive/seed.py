"""Create the demo users (one per role). Passwords come from .env only."""

from __future__ import annotations

import os
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import User
from .security import hash_password

DEMO_USERS = [
    # username, display name, role, organisation, env var for password
    ("admin", "Platform Admin", "admin", "GeoRevive Africa", "GEOREVIVE_ADMIN_PASSWORD"),
    ("geologist", "Geoscience Lead", "geologist", "GeoRevive Africa", "GEOREVIVE_GEOLOGIST_PASSWORD"),
    ("analyst", "Data Analyst", "analyst", "GeoRevive Africa", "GEOREVIVE_ANALYST_PASSWORD"),
    ("investor", "Demo Investor", "investor", "Example Capital (demo account)", "GEOREVIVE_INVESTOR_PASSWORD"),
    ("miner", "Small-scale Miner", "miner", "Demo syndicate (demo account)", "GEOREVIVE_MINER_PASSWORD"),
]


def seed_users(db: Session) -> list[str]:
    """Create missing demo users. Returns usernames created."""
    created = []
    for username, display, role, org, env in DEMO_USERS:
        if db.scalar(select(User).where(User.username == username)):
            continue
        pw = os.environ.get(env) or secrets.token_urlsafe(12)
        db.add(
            User(username=username, display_name=display, role=role, organisation=org, password_hash=hash_password(pw))
        )
        created.append(username)
    db.flush()
    return created
