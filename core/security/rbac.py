"""
Role-Based Access Control (RBAC) & Anti-IDOR Tenant Authorization
Guarantees absolute tenant isolation across all multi-site SaaS operations.
Strictly blocks Insecure Direct Object References (IDOR).
"""

from typing import List, Optional, Any
from fastapi import HTTPException, Depends
from core.niche_builder.schema import PermissionRole
from core.security.auth import AuthenticatedUser, get_authenticated_user


class AuthorizationError(HTTPException):
    def __init__(self, detail: str = "Access forbidden: Insufficient permissions"):
        super().__init__(status_code=403, detail=detail)


class TenantIsolationError(HTTPException):
    def __init__(self, detail: str = "Access denied: Cross-tenant resource access blocked"):
        super().__init__(status_code=403, detail=detail)


def require_role(min_role: PermissionRole):
    """
    FastAPI dependency factory enforcing minimum role level.
    Hierarchy: OWNER > ADMIN > EDITOR > VIEWER
    """
    def dependency(user: AuthenticatedUser = Depends(get_authenticated_user)) -> AuthenticatedUser:
        if not user.has_role(min_role):
            raise AuthorizationError(
                f"Action requires minimum role '{min_role.value}', but user holds '{user.role}'."
            )
        return user
    return dependency


def verify_tenant_access(user: AuthenticatedUser, resource_tenant_id: Optional[str]) -> bool:
    """
    Verifies that the authenticated user's tenant matches the requested resource's tenant.
    Raises 403 TenantIsolationError on mismatch.
    """
    if not resource_tenant_id:
        return True  # Unscoped or global resource

    if str(user.tenant_id) != str(resource_tenant_id):
        raise TenantIsolationError(
            f"Tenant mismatch: Authenticated tenant '{user.tenant_id}' cannot access "
            f"resource belonging to tenant '{resource_tenant_id}'."
        )
    return True


def verify_site_access(
    user: AuthenticatedUser,
    site: Any,
    required_roles: Optional[List[PermissionRole]] = None
) -> bool:
    """
    Enforces dual-layer security:
    1. Tenant isolation check (site.tenant_id == user.tenant_id)
    2. Optional site-level role permissions (e.g. OWNER or ADMIN for lifecycle actions)
    """
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    site_tenant_id = getattr(site, "tenant_id", None)
    if isinstance(site, dict):
        site_tenant_id = site.get("tenant_id")

    verify_tenant_access(user, site_tenant_id)

    if required_roles:
        site_roles = getattr(site, "user_roles", {})
        if isinstance(site, dict):
            site_roles = site.get("user_roles", {})

        # Default role in site is user's system role
        user_site_role_val = site_roles.get(user.user_id, user.role)
        if isinstance(user_site_role_val, PermissionRole):
            user_site_role = user_site_role_val
        else:
            try:
                user_site_role = PermissionRole(str(user_site_role_val).upper())
            except ValueError:
                user_site_role = PermissionRole.VIEWER

        if user_site_role not in required_roles:
            raise AuthorizationError(
                f"User '{user.user_id}' with role '{user_site_role.value}' in site lacks required permissions: "
                f"{[r.value for r in required_roles]}"
            )

    return True
