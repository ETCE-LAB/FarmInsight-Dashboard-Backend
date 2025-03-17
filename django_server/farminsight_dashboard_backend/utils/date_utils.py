from datetime import datetime


def get_date_range(from_date=None, to_date=None):
    """
    Returns a tuple (from_date_iso, to_date_iso) in ISO 8601 UTC format (YYYY-MM-DDTHH:MM:SSZ).
    If to_date is None, a default is set the current date time.
    """

    from_date_iso = from_date.isoformat(timespec="seconds").replace("+00:00", "Z")

    if not to_date:
        to_date_iso = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    else:
        to_date_iso = to_date.isoformat(timespec="seconds").replace("+00:00", "Z")

    return from_date_iso, to_date_iso
