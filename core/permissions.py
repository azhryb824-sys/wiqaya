from django.core.exceptions import PermissionDenied

def get_user_institution(user):
    return user.institutions.first()

def require_executive_or_admin_assistant(user):
    if not user.is_authenticated:
        raise PermissionDenied("يجب تسجيل الدخول")
    if user.user_type not in ["executive", "admin_assistant"]:
        raise PermissionDenied("ليس لديك صلاحية")

def require_executive(user):
    if not user.is_authenticated:
        raise PermissionDenied("يجب تسجيل الدخول")
    if user.user_type != "executive":
        raise PermissionDenied("ليس لديك صلاحية")

def require_same_institution(user, obj):
    institution = get_user_institution(user)
    if not institution:
        raise PermissionDenied("لا توجد مؤسسة مرتبطة بالمستخدم")

    obj_institution = getattr(obj, "institution", None)
    if obj_institution != institution:
        raise PermissionDenied("لا يمكنك الوصول لهذا السجل")

def require_client_ownership(user, obj):
    if user.user_type != "client":
        raise PermissionDenied("ليس لديك صلاحية")
    if getattr(obj, "client", None) != user:
        raise PermissionDenied("لا يمكنك الوصول لهذا السجل")

def require_technician_assignment(user, visit):
    if user.user_type != "technician":
        raise PermissionDenied("ليس لديك صلاحية")
    if getattr(visit, "technician", None) != user:
        raise PermissionDenied("هذه الزيارة ليست مسندة إليك")
