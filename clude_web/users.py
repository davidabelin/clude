"""The app's own accounts: one `users/<name>.json` document per player.

Accounts are made from the CLI and never from a sign-up page
(`docs/phase8.1-plan.md` 3.4), so nothing reachable from the web can
create one. A password is only ever stored as a Werkzeug hash -- scrypt
by default in Werkzeug 3 -- and the plaintext never reaches the store,
the event log or a record.

Everything else here leans towards convenience, on purpose (David,
2026-09-17; CLAUDE.md, "Settled decisions"): a new account gets
`DEFAULT_PASSWORD`, any non-empty password is accepted, and a player is
asked once whether they want to change it. After that only David can,
from the CLI.

The login name is the player's identity, not just a credential: Phase
8.2 writes it into `SeatRecord.label`, so a human's logbook follows the
name across whichever suspect they sit as (`docs/architecture.md`,
"Seats and player identity"). It is therefore stored as typed, and
matched case-insensitively -- `David` and `david` are one account, and
the account remembers which of the two to show.
"""
from __future__ import annotations

from datetime import datetime, timezone

from clude_core.domain import SUSPECTS
from werkzeug.security import check_password_hash, generate_password_hash

from clude_storage.stores import validate_run_id

USERS_PREFIX = "users"
"""Folder holding the account documents, beside `runs/` and `games/`."""

DEFAULT_PASSWORD = "password"

RESERVED_NAMES: frozenset = frozenset(
    {suspect.lower() for suspect in SUSPECTS} | {"floor", "random", "web", "envelope"}
)
"""Names an account may not take, compared in key form (lower-cased): a
login name is a logbook identity (`SeatRecord.label`), and an account
called ``mustard`` would share ``logbooks/mustard/`` with the character
on a case-insensitive file system, or a bot's label anywhere."""
"""What a new account gets. Accounts are handed out by David himself to
family and friends, so convenience beats secrecy here (David,
2026-09-17; CLAUDE.md, "Settled decisions"). A player is offered a
change once, after their first login (`clude_web.auth.password`); after
that only `clude_cli.py users passwd` can change it."""

DOCUMENT_VERSION = 2
"""1 was the first shape; 2 added `password_prompted`. A version 1
account simply reads as never having been offered the change."""


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


def add_user(store, name: str, password: str = DEFAULT_PASSWORD) -> dict:
    """Create an account and return its document.

    Any non-empty password is accepted, a single character included: this
    app is for family and friends and convenience wins here. Empty is
    still refused, because an empty password makes the form's own
    `required` the only thing standing in the way, which is a surprise
    rather than a choice.

    Raises
    ------
    ValueError
        On a bad name, an empty password, or a name already taken.
    """
    key = normalise(name)
    if key in RESERVED_NAMES:
        raise ValueError(f"{name!r} is taken: it is a character's name or a bot's")
    if not password:
        raise ValueError("a password cannot be empty")
    if get_user(store, key) is not None:
        raise ValueError(f"user {key!r} already exists")
    document = {
        "version": DOCUMENT_VERSION,
        "name": name.strip(),
        "key": key,
        "password_hash": generate_password_hash(password),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "password_prompted": False,
    }
    store.put_doc(user_key(key), document)
    return document


def set_password(store, name: str, password: str) -> dict:
    """Replace an account's password; returns the updated document."""
    document = get_user(store, name)
    if document is None:
        raise ValueError(f"no such user: {name!r}")
    if not password:
        raise ValueError("a password cannot be empty")
    document["password_hash"] = generate_password_hash(password)
    store.put_doc(user_key(name), document)
    return document


def needs_password_offer(document) -> bool:
    """Whether this account has yet to be offered the one-time change.

    An account made before `DOCUMENT_VERSION` 2 has no flag and so reads
    as never offered, which is the right answer for it.
    """
    return not document.get("password_prompted", False)


def mark_password_prompted(store, name: str) -> dict:
    """Record that the one-time offer has been made, whether or not the
    player took it. Nothing offers it again after this."""
    document = get_user(store, name)
    if document is None:
        raise ValueError(f"no such user: {name!r}")
    document["password_prompted"] = True
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
