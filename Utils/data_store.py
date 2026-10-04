"""Persistence for the app's local JSON data file."""

import json
import os
import tempfile
from pathlib import Path

from Utils.classes import Beverage, Expense, Person

DATA_FILE_NAME = "data.json"
BACKUP_FILE_SUFFIX = ".bak"


def get_data_file_path(app_file):
    """Return the writable app data path, using Flet storage when available."""
    storage_dir = os.getenv("FLET_APP_STORAGE_DATA")
    base_dir = (
        Path(storage_dir)
        if storage_dir
        else Path(app_file).resolve().parent
    )
    return base_dir / DATA_FILE_NAME


def get_backup_file_path(file_path):
    """Return the single previous-version file for a data path."""
    return Path(f"{file_path}{BACKUP_FILE_SUFFIX}")


def has_saved_data_file(file_path):
    """Check for either the current data file or its recovery copy."""
    file_path = Path(file_path)
    return file_path.exists() or get_backup_file_path(file_path).exists()


def _load_data_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Die Datendatei enthält kein JSON-Objekt.")

    for section in ("persons", "expenses", "beverages"):
        if section in data and not isinstance(data[section], list):
            raise ValueError(f"Der Datenbereich '{section}' ist keine Liste.")

    persons = [Person.from_dict(item) for item in data.get("persons", [])]
    beverages = [
        Beverage.from_dict(item)
        for item in data.get("beverages", [])
    ]
    expenses = [
        Expense.from_dict(item, beverages)
        for item in data.get("expenses", [])
    ]
    return persons, expenses, beverages


def _write_atomically(file_path, content):
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{file_path.name}.",
        suffix=".tmp",
        dir=file_path.parent,
    )

    try:
        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_name, file_path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def load_data(file_path):
    """Load data and recover from the previous copy when needed."""
    file_path = Path(file_path)
    backup_path = get_backup_file_path(file_path)

    if not file_path.exists():
        if not backup_path.exists():
            return [], [], []
        recovered_data = _load_data_file(backup_path)
        _write_atomically(file_path, backup_path.read_bytes())
        print("Hauptdatendatei fehlte; Daten aus Sicherung wiederhergestellt.")
        return recovered_data

    try:
        return _load_data_file(file_path)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        if not backup_path.exists():
            raise

        try:
            recovered_data = _load_data_file(backup_path)
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
        ) as backup_error:
            raise RuntimeError(
                "Hauptdatei und Sicherung konnten nicht gelesen werden: "
                f"{error}; {backup_error}"
            ) from backup_error

        _write_atomically(file_path, backup_path.read_bytes())
        print(
            f"Datendatei fehlerhaft ({error}); "
            "Sicherung wurde wiederhergestellt."
        )
        return recovered_data


def save_data(file_path, persons, expenses, beverages):
    """Save atomically and retain the previous file for recovery."""
    data = {
        "persons": [person.to_dict() for person in persons],
        "expenses": [expense.to_dict() for expense in expenses],
        "beverages": [beverage.to_dict() for beverage in beverages],
    }

    file_path = Path(file_path)
    content = json.dumps(data, ensure_ascii=False, indent=4).encode("utf-8")

    if file_path.exists():
        backup_path = get_backup_file_path(file_path)
        _write_atomically(backup_path, file_path.read_bytes())

    _write_atomically(file_path, content)
