"""Manually populate the DB with demo agents, test cases, eval sets, and runs.

Run locally with:
    python app/seed_demo_data.py

This is NOT called from prestart / migrations. It's opt-in.
Safe to re-run: skips entirely if any agent already exists.
"""

import logging

from sqlmodel import Session

from app.core.db import engine, seed_eval_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Seeding demo data")
    with Session(engine) as session:
        seed_eval_data(session)
    logger.info("Demo data seeded")


if __name__ == "__main__":
    main()
