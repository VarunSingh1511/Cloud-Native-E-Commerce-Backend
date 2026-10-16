"""Create an ADMIN user, or promote an existing user to ADMIN.

Usage:
    python -m app.scripts.create_admin admin@example.com

The API never lets anyone become an admin, so the first admin is created here.
The password is typed at a hidden prompt, so it never appears on screen or in
shell history. The script uses DATABASE_URL, so the same command works for the
local database and, later, for Azure PostgreSQL.
"""

import argparse
import getpass
import sys

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.services.users import create_user, get_user_by_email


def promote_to_admin(db: Session, user: User) -> User:
    """Give an existing user the ADMIN role."""
    user.role = UserRole.ADMIN
    db.commit()
    return user


def _ask_for_password() -> str:
    """Read a new password twice at a hidden prompt."""
    password = getpass.getpass("Password for the new admin (min 8 characters): ")
    if getpass.getpass("Repeat the password: ") != password:
        sys.exit("Passwords do not match.")
    return password


def main(argv: list[str] | None = None) -> None:
    """Parse the command line, then create or promote the admin."""
    parser = argparse.ArgumentParser(description="Create or promote an ADMIN user.")
    parser.add_argument("email", help="Email address of the admin account")
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        user = get_user_by_email(db, args.email)
        if user is not None:
            promote_to_admin(db, user)
            print(f"Promoted existing user {user.email} to ADMIN.")
            return

        try:
            # UserCreate applies the same email and password rules as the API.
            user_data = UserCreate(email=args.email, password=_ask_for_password())
        except ValidationError as error:
            sys.exit(f"Invalid input: {error.errors()[0]['msg']}")
        user = create_user(db, user_data, role=UserRole.ADMIN)
        print(f"Created ADMIN user {user.email} (id {user.id}).")


if __name__ == "__main__":
    main()
