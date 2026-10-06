"""Build local ZIP archives from the tracked VFS example directories."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def main():
    vfs = Path(__file__).resolve().parent.parent / "vfs"
    for name in ("deep", "files", "minimal"):
        source = vfs / name
        target = vfs / f"{name}.zip"
        if not source.is_dir():
            raise SystemExit(f"Не найдена папка: {source}")
        with ZipFile(target, "w", ZIP_DEFLATED) as archive:
            for item in sorted(source.rglob("*")):
                if item.is_file():
                    archive.write(item, item.relative_to(source).as_posix())
        print(f"Создан архив: {target.name}")


if __name__ == "__main__":
    main()
