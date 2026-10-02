import json
import tomllib
from pathlib import Path
from urllib.request import Request, urlopen


# =========================================================
# GitHub
# =========================================================

GITHUB_OWNER = "JuJ-FiF"
GITHUB_REPOSITORY = "BeverageOrganiser"


# =========================================================
# Projektversion
# =========================================================

def get_app_version():
    """
    Liest die Version aus der pyproject.toml.
    """

    project_root = Path(__file__).resolve().parent.parent
    pyproject_file = project_root / "pyproject.toml"

    if pyproject_file.exists():

        with open(pyproject_file, "rb") as file:
            data = tomllib.load(file)

        return data["project"]["version"]

    # Fallback für bereits gebaute Apps,
    # falls pyproject.toml nicht vorhanden ist.
    return "0.0.0"


APP_VERSION = get_app_version()


# =========================================================
# Versionsvergleich
# =========================================================

def version_tuple(version):
    """
    Wandelt z.B.

        1.2.3
        v1.2.3

    in

        (1, 2, 3)

    um.
    """

    version = str(version)
    version = version.lower()
    version = version.lstrip("v")

    parts = version.split(".")

    result = []

    for part in parts:

        number = ""

        for character in part:

            if character.isdigit():
                number += character
            else:
                break

        result.append(int(number) if number else 0)

    while len(result) < 3:
        result.append(0)

    return tuple(result[:3])


def is_newer_version(current_version, latest_version):
    return (
        version_tuple(latest_version)
        > version_tuple(current_version)
    )


# =========================================================
# GitHub Updateprüfung
# =========================================================

async def check_for_update():
    """
    Prüft die neueste GitHub-Release.

    Rückgabe bei neuer Version:

    {
        "version": "1.0.1",
        "name": "BeverageOrganiser 1.0.1",
        "changelog": "...",
        "download_url": "..."
    }

    Keine neue Version:
        None
    """

    url = (
        "https://api.github.com/repos/"
        f"{GITHUB_OWNER}/"
        f"{GITHUB_REPOSITORY}/"
        "releases/latest"
    )

    try:

        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "BeverageOrganiser"
            }
        )

        with urlopen(request, timeout=8) as response:

            data = json.loads(response.read().decode("utf-8"))

        latest_version = data.get("tag_name", "")

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

        for asset in data.get("assets", []):
            asset_name = asset.get("name", "").lower()

            if asset_name.endswith(".apk"):
                download_url = asset.get("browser_download_url")
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
            "download_url": download_url
        }

    except Exception as ex:
        print(f"Updateprüfung fehlgeschlagen: {ex}")

        return None