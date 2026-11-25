from django.db import Error, transaction

from accounts.models import Role

from .models import Equipment, EquipmentStatus


class EquipmentNumberConflict(Exception):
    pass


class EquipmentCreationFailed(Exception):
    pass


class EquipmentCreationUnknown(Exception):
    pass


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
        sqlstate = getattr(error.__cause__, "sqlstate", None) or ""
        transaction_rejected = sqlstate.startswith("23") or sqlstate in {"40001", "40002", "40P01"}
        if ready_to_commit and not transaction_rejected:
            raise EquipmentCreationUnknown from None
        raise EquipmentCreationFailed from None
    return equipment
