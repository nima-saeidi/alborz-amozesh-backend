from rest_framework.permissions import BasePermission

class IsSuperAdmin(BasePermission):
    #check if Admin is superadmin or not
    def has_permission(self, request, view):
        user = request.user
        
        if not user.is_authenticated or not hasattr(user, 'admin_profile'):
            return False
        return user.admin_profile.access_level == 5


#we use this founction to check if admin has permision to do the task or not
class HasAdminLevel(BasePermission):
    required_level = 1  # defult access level

    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated and
            hasattr(user, 'admin_profile') and
            user.admin_profile.access_level >= self.required_level
        )

    @classmethod
    def level(cls, level):
        #return a subclass for the required_level
        return type(f'HasAdminLevel{level}', (cls,), {'required_level': level})