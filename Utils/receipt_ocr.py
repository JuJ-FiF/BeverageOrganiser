import os
import sys
from pathlib import Path


ANDROID_PACKAGE_NAME = (
    "de.jujfif.beverageorganiser"
)


def is_android():

    return (
        sys.platform == "android"
        or bool(
            os.environ.get(
                "ANDROID_ARGUMENT"
            )
        )
    )


def recognize_receipt_text(
    image_path
):

    if not is_android():

        raise RuntimeError(
            "Die automatische Belegerkennung "
            "ist nur unter Android verfügbar."
        )

    path = Path(
        image_path
    )

    if not path.exists():

        raise FileNotFoundError(
            f"Beleg wurde nicht gefunden:\n{path}"
        )

    if not path.is_file():

        raise ValueError(
            f"Der Beleg ist keine Datei:\n{path}"
        )

    try:

        # PyJNIus bewusst erst hier importieren.
        #
        # Dadurch funktioniert die App weiterhin
        # unter Windows ohne Android-Java-Umgebung.
        from jnius import autoclass

    except ImportError as ex:

        raise RuntimeError(
            "PyJNIus konnte nicht geladen werden."
        ) from ex

    try:

        ReceiptOcr = autoclass(
            f"{ANDROID_PACKAGE_NAME}.ReceiptOcr"
        )

        text = ReceiptOcr.recognizeText(
            str(path)
        )

    except Exception as ex:

        raise RuntimeError(
            f"Android-OCR konnte nicht gestartet werden:\n{ex}"
        ) from ex

    if text is None:

        raise RuntimeError(
            "Die OCR hat keinen Text zurückgegeben."
        )

    text = str(
        text
    ).strip()

    if not text:

        raise RuntimeError(
            "Auf dem Beleg wurde kein Text erkannt."
        )

    return text