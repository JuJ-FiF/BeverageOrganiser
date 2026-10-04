"""Serialization and validation for user initiated data import and export."""

from Utils.classes import Beverage, Expense, Person

def create_export_data(persons, expenses, beverages):
    return {
        "persons": [person.to_dict() for person in persons],
        "expenses": [expense.to_dict() for expense in expenses],
        "beverages": [beverage.to_dict() for beverage in beverages],
    }

def validate_import_data(data):
    if not isinstance(data, dict):
        raise ValueError("Die Datei enthält keine gültige Datenstruktur.")

    for section in ("persons", "expenses", "beverages"):
        if section not in data:
            raise ValueError(f"Der Bereich '{section}' fehlt.")
        if not isinstance(data[section], list):
            raise ValueError(f"Der Bereich '{section}' muss eine Liste sein.")

    return data

def build_import_data(data):
    """Build all imported objects before replacing the current app data."""
    validate_import_data(data)
    persons = [Person.from_dict(item) for item in data["persons"]]
    beverages = [Beverage.from_dict(item) for item in data["beverages"]]
    expenses = [
        Expense.from_dict(item, beverages)
        for item in data["expenses"]
    ]
    return persons, expenses, beverages
