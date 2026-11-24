"""Add to an agency's prepaid balance by hand.

Until top-ups exist this is the only way a balance grows. It writes one line to the
agency's ledger (`balance_entry`) against the database in `DATABASE_URL`.

    uv run python scripts/add_balance.py <agency id> <dollars> --note "Why"
"""

import argparse
import sys
import uuid
from decimal import Decimal, InvalidOperation

from sqlmodel import Session

from app.core.db import engine
from app.models.agency import Agency
from app.services.billing_state import add_balance, settle_period


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agency_id", type=uuid.UUID)
    parser.add_argument("dollars", help="A positive amount, such as 100 or 49.50")
    parser.add_argument("--note", required=True, help="Why it was added")
    args = parser.parse_args()
    try:
        amount = Decimal(args.dollars)
    except InvalidOperation:
        print("dollars must be a number", file=sys.stderr)
        return 2
    if amount <= 0:
        print("dollars must be more than zero", file=sys.stderr)
        return 2
    with Session(engine) as session:
        agency = session.get(Agency, args.agency_id)
        if agency is None:
            print("No agency with that id", file=sys.stderr)
            return 1
        add_balance(
            session=session,
            agency=agency,
            amount_usd=amount,
            note=args.note,
            created_by=None,
        )
        _included_left, balance = settle_period(session=session, agency=agency)
        print(f"Added ${amount:.2f} to {agency.name}. Balance now ${balance:.2f}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
