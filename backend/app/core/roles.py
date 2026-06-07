from app.domain.enums import UserRole

ROLE_RANK: dict[UserRole, int] = {
    UserRole.OPERATOR: 1,
    UserRole.ADMIN: 2,
    UserRole.OWNER: 3,
}


def has_minimum_role(actor_role: UserRole, required_role: UserRole) -> bool:
    return ROLE_RANK[actor_role] >= ROLE_RANK[required_role]
