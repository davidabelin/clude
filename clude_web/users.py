"""The app's own accounts: one `users/<name>.json` document per player.

Accounts are made from the CLI and never from a sign-up page
(`docs/phase8.1-plan.md` 3.4), so nothing reachable from the web can
create one. A password is only ever stored as a Werkzeug hash -- scrypt
by default in Werkzeug 3 -- and the plaintext never reaches the store,
the event log or a record.

The login name is the player's identity, not just a credential: Phase
8.2 writes it into `SeatRecord.label`, so a human's logbook follows the
name across whichever suspect they sit as (`docs/architecture.md`,
"Seats and player identity"). It is therefore stored as typed, and
matched case-insensitively -- `David` and `david` are one account, and
the account remembers which of the two to show.
"""
from __future__ import annotations

from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from clude_storage.stores import validate_run_id

USERS_PREFIX = "users"
"""Folder holding the account documents, beside `runs/` and `games/`."""

MIN_PASSWORD = 8
"""Shortest password `add_user` will accept."""


def normalise(name: str) -> str:
    """The key form of `name`: stripped and lower-cased.

    Raises
    ------
    ValueError
        If the name is empty, or holds anything but letters, digits,
        ``_``, ``.`` and ``-`` -- the store's own rule for a path
        segment, checked here so the message names the account rather
        than the file.
    """
    key = (name or "").strip().lower()
    if not key:
        raise ValueError("a user name cannot be empty")
    try:
        validate_run_id(key)
    except ValueError:
        raise ValueError(
            f"invalid user name {name!r}: use letters, digits, '_', '.' or '-'"
        ) from None
    return key


def user_key(name: str) -> str:
    """Storage key for one account."""
    return f"{USERS_PREFIX}/{normalise(name)}.json"


def get_user(store, name: str):
    """The account document for `name`, or None if there is no such
    account. A malformed name is not an error here, only a miss: the
    login form must not tell a stranger which names are even valid."""
    try:
        return store.get_doc(user_key(name))
    except (KeyError, ValueError):
        return None


def list_users(store) -> list:
    """Every account, by key order, each as its stored document."""
    users = []
    for key in store.list_docs(USERS_PREFIX):
        try:
            users.append(store.get_doc(f"{USERS_PREFIX}/{key}.json"))
        except KeyError:  # removed between listing and reading
            continue
    return users


def add_user(store, name: str, password: str) -> dict:
    """Create an account and return its document.

    Raises
    ------
    ValueError
        On a bad name, a password under `MIN_PASSWORD` characters, or a
        name already taken.
    """
    key = normalise(name)
    if len(password or "") < MIN_PASSWORD:
        raise ValueError(f"password must be at least {MIN_PASSWORD} characters")
    if get_user(store, key) is not None:
        raise ValueError(f"user {key!r} already exists")
    document = {
        "version": 1,
        "name": name.strip(),
        "key": key,
        "password_hash": generate_password_hash(password),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    store.put_doc(user_key(key), document)
    return document


def set_password(store, name: str, password: str) -> dict:
    """Replace an account's password; returns the updated document."""
    document = get_user(store, name)
    if document is None:
        raise ValueError(f"no such user: {name!r}")
    if len(password or "") < MIN_PASSWORD:
        raise ValueError(f"password must be at least {MIN_PASSWORD} characters")
    document["password_hash"] = generate_password_hash(password)
    store.put_doc(user_key(name), document)
    return document


def remove_user(store, name: str) -> bool:
    """Delete an account; True if it existed."""
    try:
        return store.delete_doc(user_key(name))
    except ValueError:
        return False


def authenticate(store, name: str, password: str):
    """The account document if `password` is right, else None.

    The hash is checked even when there is no such account, so that a
    wrong name and a wrong password take the same time to answer and the
    login page cannot be used to find out who has an account.
    """
    document = get_user(store, name)
    stored = document["password_hash"] if document else _DUMMY_HASH
    ok = check_password_hash(stored, password or "")
    return document if (ok and document) else None


_DUMMY_HASH = generate_password_hash("not-a-real-password")
"""Hashed once at import, to answer a missing account in the same time a
real one takes (`authenticate`)."""
