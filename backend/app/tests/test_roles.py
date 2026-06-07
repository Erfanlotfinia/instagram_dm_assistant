from app.core.roles import has_minimum_role
from app.domain.enums import UserRole


def test_role_hierarchy() -> None:
    assert has_minimum_role(UserRole.OWNER, UserRole.ADMIN)
    assert has_minimum_role(UserRole.ADMIN, UserRole.OPERATOR)
    assert not has_minimum_role(UserRole.OPERATOR, UserRole.ADMIN)
