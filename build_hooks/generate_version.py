from pathlib import Path
import tomllib


def main():
    project_root = Path(__file__).resolve().parent.parent
    pyproject_file = project_root / "pyproject.toml"

    with open(pyproject_file, "rb") as file:
        data = tomllib.load(file)

    version = str(data["project"]["version"])

    version_file = project_root / "Utils" / "version.py"

    version_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    version_file.write_text(
        f'APP_VERSION = "{version}"\n',
        encoding="utf-8"
    )

    print(
        f"Generated Utils/version.py "
        f"with version {version}"
    )


if __name__ == "__main__":
    main()