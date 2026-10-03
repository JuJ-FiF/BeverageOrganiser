from datetime import datetime
from pathlib import Path
import os
import uuid


RECEIPT_FOLDER_NAME = "receipts"
TEMP_RECEIPT_FOLDER_NAME = "receipt_temp"


def get_storage_directory():

    storage_dir = os.environ.get(
        "FLET_APP_STORAGE_DATA"
    )

    if not storage_dir:
        storage_dir = os.getcwd() + "/FLET/GetränkeverwaltungFLET"

    path = Path(storage_dir)

    path.mkdir(
        parents=True,
        exist_ok=True
    )

    return path


def get_receipts_directory():

    directory = (
        get_storage_directory()
        / RECEIPT_FOLDER_NAME
    )

    directory.mkdir(
        parents=True,
        exist_ok=True
    )

    return directory


def get_temp_receipts_directory():

    directory = (
        get_storage_directory()
        / TEMP_RECEIPT_FOLDER_NAME
    )

    directory.mkdir(
        parents=True,
        exist_ok=True
    )

    return directory


def create_receipt_filename(
    extension=".jpg"
):

    extension = extension.lower()

    if not extension.startswith("."):
        extension = "." + extension

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    unique_id = uuid.uuid4().hex[:8]

    return (
        f"{timestamp}_"
        f"{unique_id}"
        f"{extension}"
    )


def save_receipt(
    data,
    extension=".jpg"
):

    if not data:
        raise ValueError(
            "Es wurden keine Bilddaten übergeben."
        )

    filename = create_receipt_filename(
        extension
    )

    directory = get_receipts_directory()

    file_path = (
        directory / filename
    )

    with open(
        file_path,
        "wb"
    ) as file:
        file.write(data)

    relative_path = (
        Path(RECEIPT_FOLDER_NAME)
        / filename
    )

    return relative_path.as_posix()


def save_receipt_temp(
    data,
    extension=".jpg"
):

    if not data:
        raise ValueError(
            "Es wurden keine Bilddaten übergeben."
        )

    filename = create_receipt_filename(
        extension
    )

    directory = (
        get_temp_receipts_directory()
    )

    file_path = (
        directory / filename
    )

    with open(
        file_path,
        "wb"
    ) as file:
        file.write(data)

    return file_path


def delete_receipt_temp(
    file_path
):

    if not file_path:
        return

    try:

        path = Path(file_path)

        if path.exists():
            path.unlink()

    except OSError:
        pass


def get_receipt_path(receipt):

    if not receipt:
        return None

    path = Path(receipt)

    if path.is_absolute():
        return path

    return (
        get_storage_directory()
        / path
    )


def read_receipt(receipt):

    path = get_receipt_path(
        receipt
    )

    if not path:
        return None

    if not path.exists():
        return None

    try:
        return path.read_bytes()

    except OSError:
        return None


def delete_receipt(receipt):

    path = get_receipt_path(
        receipt
    )

    if not path:
        return

    try:

        if path.exists():
            path.unlink()

    except OSError:
        pass


def receipt_exists(receipt):

    path = get_receipt_path(
        receipt
    )

    return (
        path is not None
        and path.exists()
        and path.is_file()
    )