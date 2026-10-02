import asyncio
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from jnius import autoclass, cast

from Utils.version import APP_VERSION


GITHUB_OWNER = "JuJ-FiF"
GITHUB_REPOSITORY = "BeverageOrganiser"

ANDROID_PACKAGE_NAME = "de.jujfif.beverageorganiser"

APK_FILE_NAME = "BeverageOrganiser-update.apk"


def version_tuple(version):
    version = str(version).lower().lstrip("v")

    parts = version.split(".")

    result = []

    for part in parts:
        number = ""

        for character in part:
            if character.isdigit():
                number += character
            else:
                break

        result.append(
            int(number) if number else 0
        )

    while len(result) < 3:
        result.append(0)

    return tuple(result[:3])


def is_newer_version(
    current_version,
    latest_version
):
    return (
        version_tuple(latest_version)
        > version_tuple(current_version)
    )


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

    latest_version = data.get(
        "tag_name",
        ""
    )

    if not latest_version:
        return None

    latest_version = (
        latest_version
        .lstrip("v")
    )

    if not is_newer_version(
        APP_VERSION,
        latest_version
    ):
        return None

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

    if apk_path.exists():
        apk_path.unlink()

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

                file.write(chunk)

    if not apk_path.exists():

        raise RuntimeError(
            "APK wurde nicht erstellt."
        )

    if apk_path.stat().st_size == 0:

        raise RuntimeError(
            "Die heruntergeladene APK ist leer."
        )

    return apk_path


def start_android_update(apk_path):
    """
    Startet den Android-Installationsdialog
    direkt über die Android-Java-API.
    """

    apk_path = Path(apk_path)

    if not apk_path.exists():
        raise RuntimeError(
            "APK-Datei wurde nicht gefunden:\n"
            f"{apk_path}"
        )

    if apk_path.stat().st_size <= 0:
        raise RuntimeError(
            "APK-Datei ist leer."
        )

    # -------------------------------------------------
    # Flet / Serious Python Activity
    # -------------------------------------------------

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

    # -------------------------------------------------
    # Android-Klassen
    # -------------------------------------------------

    Intent = autoclass(
        "android.content.Intent"
    )

    Uri = autoclass(
        "android.net.Uri"
    )

    Settings = autoclass(
        "android.provider.Settings"
    )

    File = autoclass(
        "java.io.File"
    )

    FileProvider = autoclass(
        "androidx.core.content.FileProvider"
    )

    # -------------------------------------------------
    # Installation aus unbekannten Quellen prüfen
    #
    # minSdk der App ist >= 29.
    # Daher ist keine Build.VERSION-Prüfung notwendig.
    # -------------------------------------------------

    package_manager = (
        activity.getPackageManager()
    )

    if not package_manager.canRequestPackageInstalls():

        settings_intent = Intent(
            Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES
        )

        settings_uri = Uri.parse(
            "package:"
            + activity.getPackageName()
        )

        settings_intent.setData(
            settings_uri
        )

        activity.startActivity(
            settings_intent
        )

        raise RuntimeError(
            "Android blockiert momentan die "
            "Installation unbekannter Apps.\n\n"
            "Bitte erlaube in den Android-Einstellungen "
            "die Installation aus dieser Quelle und "
            "starte das Update anschließend erneut."
        )

    # -------------------------------------------------
    # APK als Java File
    # -------------------------------------------------

    apk_file = File(
        str(apk_path)
    )

    # -------------------------------------------------
    # Eigener FileProvider
    # -------------------------------------------------

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

    # -------------------------------------------------
    # Android Installer
    # -------------------------------------------------

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

    # -------------------------------------------------
    # Installer starten
    # -------------------------------------------------

    activity.startActivity(
        install_intent
    )

    return True

    # -------------------------------------------------
    # APK als Java File
    # -------------------------------------------------

    apk_file = File(str(apk_path))

    # -------------------------------------------------
    # Eigener FileProvider
    # -------------------------------------------------

    authority = (ANDROID_PACKAGE_NAME + ".updateprovider")

    apk_uri = (
        FileProvider.getUriForFile(
            activity,
            authority,
            apk_file
        )
    )

    # -------------------------------------------------
    # Android Installer Intent
    # -------------------------------------------------

    install_intent = Intent(Intent.ACTION_INSTALL_PACKAGE)
    install_intent.setDataAndType(apk_uri, "application/vnd.android.package-archive")
    install_intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    install_intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

    # -------------------------------------------------
    # Installer starten
    # -------------------------------------------------

    activity.startActivity(
        install_intent
    )

    return True


async def download_and_install_update(
    download_url
):

    apk_path = await asyncio.to_thread(
        download_apk,
        download_url
    )

    await asyncio.to_thread(
        start_android_update,
        apk_path
    )

    return apk_path