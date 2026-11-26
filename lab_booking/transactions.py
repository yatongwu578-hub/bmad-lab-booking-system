def transaction_rejected(error, *, additional_sqlstates=()):
    """Only classify a COMMIT error as failed when PostgreSQL confirms rejection."""
    sqlstate = getattr(error.__cause__, "sqlstate", None) or ""
    return sqlstate.startswith("23") or sqlstate in {"40001", "40002", "40P01"} or sqlstate in additional_sqlstates
