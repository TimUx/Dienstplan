"""User-domain helpers shared by auth routes."""

from typing import Iterable, List, Tuple


VALID_USER_ROLES = ('Admin', 'Mitarbeiter', 'Disponent')


def normalize_and_validate_roles(roles: Iterable[str] | str | None) -> Tuple[List[str], str | None]:
    """Normalize role payload and validate against allowed roles."""
    if roles is None:
        normalized = ['Mitarbeiter']
    elif isinstance(roles, list):
        normalized = roles
    else:
        normalized = [roles]

    for role in normalized:
        if role not in VALID_USER_ROLES:
            return [], f'Ungültige Rolle: {role}. Erlaubt: {", ".join(VALID_USER_ROLES)}'

    return normalized, None
