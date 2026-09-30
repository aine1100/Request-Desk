from rest_framework.permissions import BasePermission

from desk.models import Role


class IsOperatorOrAdmin(BasePermission):
    message = "Only operators can do this."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role in (Role.OPERATOR, Role.ADMIN)
        )


class IsAdmin(BasePermission):
    message = "Only admins can do this."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == Role.ADMIN)
