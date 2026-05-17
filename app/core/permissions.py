from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class Permission(str, Enum):
    TRAIN_ASSISTANT = "train_assistant"
    CHAT = "chat"
    VIEW_USAGE = "view_usage"
    MANAGE_INTEGRATIONS = "manage_integrations"
    MANAGE_USERS = "manage_users"
    MANAGE_ASSISTANTS = "manage_assistants"
    DELETE_ASSISTANTS = "delete_assistants"


ROLE_PERMISSIONS = {
    Role.OWNER: [
        Permission.TRAIN_ASSISTANT,
        Permission.CHAT,
        Permission.VIEW_USAGE,
        Permission.MANAGE_INTEGRATIONS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_ASSISTANTS,
        Permission.DELETE_ASSISTANTS,
    ],
    Role.ADMIN: [
        Permission.TRAIN_ASSISTANT,
        Permission.CHAT,
        Permission.VIEW_USAGE,
        Permission.MANAGE_INTEGRATIONS,
        Permission.MANAGE_ASSISTANTS,
        Permission.DELETE_ASSISTANTS,
    ],
    Role.USER: [
        Permission.TRAIN_ASSISTANT,
        Permission.CHAT,
        Permission.VIEW_USAGE,
    ],
    Role.VIEWER: [
        Permission.CHAT,
    ],
}


def has_permission(role: str, permission: Permission) -> bool:
    role_enum = Role(role) if role in [r.value for r in Role] else None
    if not role_enum:
        return False
    return permission in ROLE_PERMISSIONS.get(role_enum, [])


def get_assistant_permissions(user_role: str, user_assistant_ids: list, assistant_id: str) -> bool:
    if user_role in [Role.OWNER.value, Role.ADMIN.value]:
        return True
    return assistant_id in user_assistant_ids