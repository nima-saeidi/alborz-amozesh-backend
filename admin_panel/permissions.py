from rest_framework.permissions import BasePermission


def admin_level(user):
    """Admin API access level of a user (Django superusers count as super admins)"""
    if not user or not user.is_authenticated:
        return 0
    if user.is_superuser:
        return 5
    profile = getattr(user, 'admin_profile', None)
    return profile.access_level if profile else 0


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return admin_level(request.user) >= 5


class HasAdminLevel(BasePermission):
    """HasAdminLevel.level(4) -> permission class requiring access level >= 4"""
    required_level = 1

    def has_permission(self, request, view):
        return admin_level(request.user) >= self.required_level

    @classmethod
    def level(cls, level):
        return type(f'HasAdminLevel{level}', (cls,), {'required_level': level})
