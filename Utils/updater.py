import asyncio
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen

from Utils.version import APP_VERSION

GITHUB_OWNER = "JuJ-FiF"
GITHUB_REPOSITORY = "BeverageOrganiser"

ANDROID_PACKAGE_NAME = "de.jujfif.beverageorganiser"

APK_FILE_NAME = "BeverageOrganiser-update.apk"

# =========================================================
# VERSIONSVERGLEICH
# =========================================================

def version_tuple(version):
    """
    Wandelt eine Versionsnummer in einen vergleichbaren
    Zahlen-Tupel um.

    Unterstützte Formate:

        1.2.0
        v1.2.0
        1.2.0-HotFix#1
        v1.2.0-HotFix#1
        1.2.0-HotFix#25

    Beispiele:

        1.2.0
            -> (1, 2, 0, 0)

        v1.2.0
            -> (1, 2, 0, 0)

        1.2.0-HotFix#1
            -> (1, 2, 0, 1)

        v1.2.0-HotFix#5
            -> (1, 2, 0, 5)
    """

    version = str(
        version
    ).strip()

    # -----------------------------------------------------
    # Führendes "v" entfernen
    # -----------------------------------------------------

    if version.lower().startswith("v"):

        version = version[1:]

    # -----------------------------------------------------
    # Hauptversion + optionalen HotFix extrahieren
    #
    # Beispiele:
    #
    # 1.2.0
    # 1.2.0-HotFix#1
    # -----------------------------------------------------

    match = re.match(
        r"^(\d+)"
        r"(?:\.(\d+))?"
        r"(?:\.(\d+))?"
        r"(?:-HotFix#(\d+))?"
        r"$",
        version,
        re.IGNORECASE
    )

    if not match:

        raise ValueError(
            f"Ungültige Versionsnummer: {version}"
        )

    major = int(
        match.group(1)
    )

    minor = int(
        match.group(2) or 0
    )

    patch = int(
        match.group(3) or 0
    )

    hotfix = int(
        match.group(4) or 0
    )

    return (
        major,
        minor,
        patch,
        hotfix
    )

def is_newer_version(
    current_version,
    latest_version
):
    """
    Prüft, ob latest_version neuer als
    current_version ist.

    Beispiele:

        1.2.0 -> 1.2.1
        True

        1.2.0 -> 1.2.0-HotFix#1
        True

        1.2.0-HotFix#1 -> 1.2.0-HotFix#2
        True

        1.2.0-HotFix#2 -> 1.2.0-HotFix#1
        False

        1.2.0-HotFix#99 -> 1.2.1
        True
    """

    return (
        version_tuple(latest_version)
        >
        version_tuple(current_version)
    )

# =========================================================
# GITHUB UPDATE PRÜFEN
# =========================================================

async def check_for_update():

    url = (
        "https://api.github.com/repos/"
        f"{GITHUB_OWNER}/"
        f"{GITHUB_REPOSITORY}/"
        "releases/latest"
    )

    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "BeverageOrganiser",
        },
    )

    def load_release():

        with urlopen(
            request,
            timeout=10
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )

    data = await asyncio.to_thread(
        load_release
    )

    # -----------------------------------------------------
    # Version aus GitHub Release
    # -----------------------------------------------------

    latest_version = data.get(
        "tag_name",
        ""
    )

    if not latest_version:

        return None

    latest_version = (
        latest_version
        .strip()
        .lstrip("v")
    )

    # -----------------------------------------------------
    # Versionsformat prüfen
    # -----------------------------------------------------

    try:

        version_tuple(
            latest_version
        )

    except ValueError as ex:

        print(
            "Ungültige GitHub-Version:",
            latest_version,
            ex
        )

        return None

    # -----------------------------------------------------
    # Update verfügbar?
    # -----------------------------------------------------

    if not is_newer_version(
        APP_VERSION,
        latest_version
    ):

        return None

    # -----------------------------------------------------
    # APK suchen
    # -----------------------------------------------------

    download_url = None

    for asset in data.get(
        "assets",
        []
    ):

        asset_name = asset.get(
            "name",
            ""
        ).lower()

        if asset_name.endswith(".apk"):

            download_url = asset.get(
                "browser_download_url"
            )

            break

    if not download_url:

        return None

    # -----------------------------------------------------
    # Update zurückgeben
    # -----------------------------------------------------

    return {
        "version": latest_version,
        "name": data.get(
            "name",
            f"Version {latest_version}"
        ),
        "changelog": data.get(
            "body",
            ""
        ),
        "download_url": download_url,
    }

# =========================================================
# APK-DATEIPFAD
# =========================================================

def get_update_file_path():

    storage_dir = os.environ.get(
        "FLET_APP_STORAGE_DATA"
    )

    if not storage_dir:

        storage_dir = os.getcwd()

    storage_path = Path(
        storage_dir
    )

    storage_path.mkdir(
        parents=True,
        exist_ok=True
    )

    return (
        storage_path
        / APK_FILE_NAME
    )

# =========================================================
# APK HERUNTERLADEN
# =========================================================

def download_apk(
    download_url
):

    apk_path = get_update_file_path()

    request = Request(
        download_url,
        headers={
            "User-Agent": "BeverageOrganiser",
            "Accept": "application/octet-stream",
        },
    )

    # -----------------------------------------------------
    # Alte APK löschen
    # -----------------------------------------------------

    if apk_path.exists():

        apk_path.unlink()

    # -----------------------------------------------------
    # APK herunterladen
    # -----------------------------------------------------

    with urlopen(
        request,
        timeout=120
    ) as response:

        with open(
            apk_path,
            "wb"
        ) as file:

            while True:

                chunk = response.read(
                    1024 * 1024
                )

                if not chunk:

                    break

                file.write(
                    chunk
                )

    # -----------------------------------------------------
    # Download überprüfen
    # -----------------------------------------------------

    if not apk_path.exists():

        raise RuntimeError(
            "APK wurde nicht erstellt."
        )

    if apk_path.stat().st_size == 0:

        raise RuntimeError(
            "Die heruntergeladene APK ist leer."
        )

    return apk_path

# =========================================================
# ANDROID UPDATE STARTEN
# =========================================================

def request_install_permission():
    """Return True if APK installs are allowed; otherwise open Android settings."""
    from jnius import autoclass, cast

    PythonActivity = autoclass(
        "com.flet.serious_python_android.PythonActivity"
    )
    activity = cast(
        "android.app.Activity",
        PythonActivity.mActivity,
    )
    if activity is None:
        raise RuntimeError("Die Android Activity ist nicht verfügbar.")

    if activity.getPackageManager().canRequestPackageInstalls():
        return True

    Intent = autoclass("android.content.Intent")
    Uri = autoclass("android.net.Uri")
    Settings = autoclass("android.provider.Settings")
    settings_intent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES)
    settings_intent.setData(
        Uri.parse("package:" + activity.getPackageName())
    )
    activity.startActivity(settings_intent)
    return False


def start_android_update(
    apk_path
):
    """
    Startet den Android-Installationsdialog
    direkt über die Android-Java-API.
    """

    from jnius import autoclass, cast

    apk_path = Path(
        apk_path
    )

    # -----------------------------------------------------
    # APK prüfen
    # -----------------------------------------------------

    if not apk_path.exists():

        raise RuntimeError(
            "APK-Datei wurde nicht gefunden:\n"
            f"{apk_path}"
        )

    if apk_path.stat().st_size <= 0:

        raise RuntimeError(
            "APK-Datei ist leer."
        )

    # -----------------------------------------------------
    # Flet / Serious Python Activity
    # -----------------------------------------------------

    PythonActivity = autoclass(
        "com.flet.serious_python_android.PythonActivity"
    )

    activity = cast(
        "android.app.Activity",
        PythonActivity.mActivity
    )

    if activity is None:

        raise RuntimeError(
            "Die Android Activity ist nicht verfügbar."
        )

    # -----------------------------------------------------
    # Android-Klassen
    # -----------------------------------------------------

    Intent = autoclass(
        "android.content.Intent"
    )

    Uri = autoclass(
        "android.net.Uri"
    )

    File = autoclass(
        "java.io.File"
    )

    FileProvider = autoclass(
        "androidx.core.content.FileProvider"
    )

    # -----------------------------------------------------
    # Installationsberechtigung erneut prüfen, falls sie sich geändert hat.
    # -----------------------------------------------------

    if not request_install_permission():
        raise RuntimeError(
            "Die Installation unbekannter Apps ist für diese Quelle "
            "noch nicht erlaubt. Bitte erteile die Berechtigung und "
            "starte das Update erneut."
        )

    # -----------------------------------------------------
    # APK als Java File
    # -----------------------------------------------------

    apk_file = File(
        str(apk_path)
    )

    # -----------------------------------------------------
    # Eigener FileProvider
    # -----------------------------------------------------

    authority = (
        ANDROID_PACKAGE_NAME
        + ".updateprovider"
    )

    apk_uri = (
        FileProvider.getUriForFile(
            activity,
            authority,
            apk_file
        )
    )

    # -----------------------------------------------------
    # Android Installer
    # -----------------------------------------------------

    install_intent = Intent(
        Intent.ACTION_INSTALL_PACKAGE
    )

    install_intent.setDataAndType(
        apk_uri,
        "application/vnd.android.package-archive"
    )

    install_intent.addFlags(
        Intent.FLAG_GRANT_READ_URI_PERMISSION
    )

    install_intent.addFlags(
        Intent.FLAG_ACTIVITY_NEW_TASK
    )

    # -----------------------------------------------------
    # Installer starten
    # -----------------------------------------------------

    activity.startActivity(
        install_intent
    )

    return True

# =========================================================
# UPDATE HERUNTERLADEN + INSTALLIEREN
# =========================================================

async def download_and_install_update(
    download_url
):
    can_install = await asyncio.to_thread(request_install_permission)
    if not can_install:
        return None

    apk_path = await asyncio.to_thread(
        download_apk,
        download_url
    )

    await asyncio.to_thread(
        start_android_update,
        apk_path
    )

    return apk_path
