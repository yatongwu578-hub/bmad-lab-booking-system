from .models import Role


RESERVATION_ROLES = (Role.STUDENT, Role.TEACHER)


def can_reserve(user):
    return user.is_authenticated and user.is_active and user.role in RESERVATION_ROLES
