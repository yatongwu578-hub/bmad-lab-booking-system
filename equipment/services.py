from django.core.exceptions import PermissionDenied
from django.db import Error, transaction

from accounts.models import Role, User
from lab_booking.transactions import transaction_rejected

from .models import Equipment, EquipmentStatus


class EquipmentNumberConflict(Exception):
    pass


class EquipmentCreationFailed(Exception):
    pass


class EquipmentCreationUnknown(Exception):
    pass


class EquipmentEditFailed(Exception):
    pass


class EquipmentEditUnknown(Exception):
    pass


CATALOG_FIELDS = ("number", "name", "category", "location", "status")
EQUIPMENT_EDIT_FIELDS = ("name", "category", "location", "description")


def is_equipment_admin(user):
    return user.is_authenticated and user.is_active and user.role == Role.ADMIN


def _require_catalog_reader(user):
    if not user.is_authenticated or not user.is_active or user.role not in Role.values:
        raise PermissionDenied


def _add_status_label(row):
    return {**row, "status_label": EquipmentStatus(row["status"]).label}


def list_equipment(user):
    _require_catalog_reader(user)
    rows = Equipment.objects.order_by("number").values("id", *CATALOG_FIELDS)
    return [_add_status_label(row) for row in rows]


def get_equipment_detail(user, pk):
    _require_catalog_reader(user)
    try:
        row = Equipment.objects.values(*CATALOG_FIELDS, "description").get(pk=pk)
    except Equipment.DoesNotExist:
        return None
    return _add_status_label(row)


def lock_equipment(pk):
    """Lock only this device by primary key inside the caller's transaction."""
    try:
        return Equipment.objects.filter(pk=pk).select_for_update().values_list("pk", flat=True).get()
    except Equipment.DoesNotExist:
        return None


def _is_equipment_number_conflict(error):
    cause = error.__cause__
    diagnostic = getattr(cause, "diag", None)
    return (
        getattr(cause, "sqlstate", None) == "23505"
        and getattr(diagnostic, "table_name", None) == Equipment._meta.db_table
        and getattr(diagnostic, "constraint_name", None) == "equipment_number_unique"
    )


def create_equipment(user, values):
    if not user.is_authenticated or not user.is_active or user.role != Role.ADMIN:
        raise PermissionError("仅启用的业务管理员可以新增设备。")

    connection = transaction.get_connection()
    ready_to_commit = False
    try:
        # Durable blocks reject ordinary nesting but do not reject manual autocommit control.
        if not connection.in_atomic_block and not connection.get_autocommit():
            raise RuntimeError("新增设备要求由服务管理最外层事务。")
        with transaction.atomic(durable=True):
            equipment = Equipment.objects.create(
                number=values["number"],
                name=values["name"],
                category=values["category"],
                location=values["location"],
                description=values["description"],
                status=EquipmentStatus.AVAILABLE,
            )
            if connection.closed_in_transaction or transaction.get_rollback():
                raise EquipmentCreationFailed
            ready_to_commit = True
    except Error as error:
        if _is_equipment_number_conflict(error):
            raise EquipmentNumberConflict from None
        if ready_to_commit and not transaction_rejected(error):
            raise EquipmentCreationUnknown from None
        raise EquipmentCreationFailed from None
    return equipment


def _textarea_newlines(value):
    return value.replace("\r\n", "\n").replace("\r", "\n")


def edit_equipment(user, pk, values):
    if not is_equipment_admin(user):
        raise PermissionDenied
    if values.keys() != set(EQUIPMENT_EDIT_FIELDS):
        raise ValueError("只允许更新设备的四项基础信息。")

    connection = transaction.get_connection()
    ready_to_commit = False
    try:
        if not connection.in_atomic_block and not connection.get_autocommit():
            raise RuntimeError("编辑设备要求由服务管理最外层事务。")
        with transaction.atomic(durable=True):
            if lock_equipment(pk) is None:
                return False
            # The request's cached user can be stale after waiting for the device lock.
            try:
                active, role = User.objects.values_list("is_active", "role").get(pk=user.pk)
            except User.DoesNotExist:
                raise PermissionDenied from None
            if not active or role != Role.ADMIN:
                raise PermissionDenied
            # Read the current row in a separate Read Committed statement after acquiring its lock.
            current = Equipment.objects.values("id", *CATALOG_FIELDS, "description").get(pk=pk)
            updates = {field: values[field] for field in EQUIPMENT_EDIT_FIELDS}
            # Browsers submit textarea line endings as CRLF even when the original text used LF.
            if _textarea_newlines(updates["description"]) == _textarea_newlines(current["description"]):
                updates["description"] = current["description"]
            updated = Equipment.objects.filter(pk=current["id"]).update(**updates)
            if updated != 1 or connection.closed_in_transaction or transaction.get_rollback():
                raise EquipmentEditFailed
            ready_to_commit = True
    except Error as error:
        if ready_to_commit and not transaction_rejected(error):
            raise EquipmentEditUnknown from None
        raise EquipmentEditFailed from None
    return True
