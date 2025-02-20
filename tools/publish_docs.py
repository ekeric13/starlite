import importlib.metadata
import json
import os
import shutil
import subprocess
from pathlib import Path
import argparse
import shutil
from typing import TypedDict

parser = argparse.ArgumentParser()
parser.add_argument("--version", required=False)
parser.add_argument("--push", action="store_true")


class VersionSpec(TypedDict):
    versions: list[str]
    latest: str


def add_to_versions_file(version: str) -> VersionSpec:
    versions_file = Path("versions.json")
    version_spec: VersionSpec
    if versions_file.exists():
        version_spec = json.loads(versions_file.read_text())
    else:
        version_spec = {"versions": [], "latest": ""}

    if version not in version_spec["versions"]:
        version_spec["versions"].append(version)

    versions_file.write_text(json.dumps(version_spec))

    return version_spec


def make_version(version: str | None, push: bool) -> None:
    if version is None:
        version = importlib.metadata.version("starlite").rsplit(".")[0]
    else:
        os.environ["_STARLITE_DOCS_BUILD_VERSION"] = version

    git_add = [".nojekyll", "versions.json", version]
    subprocess.run(["make", "docs"], check=True)

    subprocess.run(["git", "checkout", "gh-pages"], check=True)

    Path(".nojekyll").touch(exist_ok=True)

    version_spec = add_to_versions_file(version)
    is_latest = version == version_spec["latest"]

    docs_src_path = Path("docs/_build/html")

    shutil.copytree(docs_src_path / "lib", version, dirs_exist_ok=True)

    if is_latest:
        for path in docs_src_path.iterdir():
            git_add.append(path.name)
            if path.is_dir():
                shutil.copytree(path, path.name, dirs_exist_ok=True)
            else:
                shutil.copy2(path, ".")

    shutil.rmtree("docs/_build")

    for file in git_add:
        subprocess.run(["git", "add", file], check=True)

    subprocess.run(
        ["git", "commit", "-m", f"Automatic docs build for version {version!r}", "--no-verify"],
        check=True,
    )

    if push:
        subprocess.run(["git", "push"], check=True)

    subprocess.run(["git", "checkout", "-"], check=True)


def main() -> None:
    args = parser.parse_args()
    make_version(version=args.version, push=args.push)


if __name__ == "__main__":
    main()
