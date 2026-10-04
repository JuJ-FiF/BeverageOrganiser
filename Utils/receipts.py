import os
from datetime import datetime
from pathlib import Path
import uuid

RECEIPT_FOLDER_NAME = "receipts"

def get_storage_directory():
    """
    Liefert den persistenten App-Speicher.
    """

    storage_dir = os.environ.get(
        "FLET_APP_STORAGE_DATA"
    )

    if not storage_dir:
        storage_dir = Path(__file__).resolve().parent.parent

    path = Path(storage_dir)
    path.mkdir(
        parents=True,
        exist_ok=True
    )

    return path

def get_receipts_directory():
    """
    Liefert den Ordner für die Belegbilder.
    """

    directory = (
        get_storage_directory()
        / RECEIPT_FOLDER_NAME
    )

    directory.mkdir(
        parents=True,
        exist_ok=True
    )

    return directory

def create_receipt_filename(extension=".jpg"):
    """
    Erstellt einen eindeutigen Dateinamen.
    """

    extension = extension.lower()

    if not extension.startswith("."):
        extension = "." + extension

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    unique_id = uuid.uuid4().hex[:8]

    return (
        f"{timestamp}_{unique_id}"
        f"{extension}"
    )

def save_receipt(data, extension=".jpg"):
    """
    Speichert Bildbytes im Belegordner.

    Gibt den relativen Pfad zurück.
    """

    if not data:
        raise ValueError(
            "Es wurden keine Bilddaten übergeben."
        )

    filename = create_receipt_filename(
        extension
    )

    directory = get_receipts_directory()
    file_path = directory / filename

    with open(file_path, "wb") as file:
        file.write(data)

    relative_path = (
        Path(RECEIPT_FOLDER_NAME)
        / filename
    )

    return relative_path.as_posix()

def get_receipt_path(receipt):
    """
    Wandelt den relativen Belegpfad
    in einen absoluten Dateipfad um.
    """

    if not receipt:
        return None

    path = Path(receipt)

    if path.is_absolute():
        return path

    return get_storage_directory() / path

def read_receipt(receipt):
    """
    Liest einen gespeicherten Beleg als Bytes.
    """

    path = get_receipt_path(receipt)

    if not path:
        return None

    if not path.exists():
        return None

    try:
        return path.read_bytes()
    except OSError:
        return None

def delete_receipt(receipt):
    """
    Löscht einen Beleg vom Gerät.
    """

    path = get_receipt_path(receipt)

    if not path:
        return

    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass

def receipt_exists(receipt):
    """
    Prüft, ob ein Beleg tatsächlich existiert.
    """

    path = get_receipt_path(receipt)

    return (
        path is not None
        and path.exists()
        and path.is_file()
    )
