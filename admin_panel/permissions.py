from rest_framework.permissions import BasePermission

class IsSuperAdmin(BasePermission):
    #check if Admin is superadmin or not
    def has_permission(self, request, view):
        user = request.user
        
        if not user.is_authenticated or not hasattr(user, 'admin_profile'):
            return False
        return user.admin_profile.access_level == 5
