import argparse
import getpass
import os
import posixpath
import shlex
import socket
import tkinter as tk
import xml.etree.ElementTree as ET
import zipfile

from datetime import datetime
from pathlib import Path
from tkinter import scrolledtext


def expand_environment(command_line):
    """Раскрыть переменные окружения."""
    if "HOME" not in os.environ:
        os.environ["HOME"] = os.environ.get(
            "USERPROFILE",
            "",
        )

    return os.path.expandvars(command_line)


def parse_command(command_line):
    """Разобрать командную строку."""
    expanded_line = expand_environment(
        command_line
    )

    try:
        return shlex.split(
            expanded_line,
            posix=False,
        )
    except ValueError as error:
        raise ValueError(
            f"ошибка разбора команды: {error}"
        ) from error


def parse_arguments():
    """Получить параметры запуска."""
    parser = argparse.ArgumentParser(
        description="Эмулятор оболочки ОС"
    )

    parser.add_argument(
        "--vfs",
        default="",
        help="Путь к ZIP-архиву VFS",
    )

    parser.add_argument(
        "--log",
        default="logs/log.xml",
        help="Путь к XML-файлу журнала",
    )

    parser.add_argument(
        "--script",
        default="",
        help="Путь к стартовому скрипту",
    )

    return parser.parse_args()


class XmlLogger:
    """XML-журнал выполнения команд."""

    def __init__(self, log_path):
        self.log_path = Path(log_path)

    def load_tree(self):
        if not self.log_path.exists():
            root = ET.Element("log")
            return ET.ElementTree(root)

        try:
            return ET.parse(self.log_path)
        except ET.ParseError:
            root = ET.Element("log")
            return ET.ElementTree(root)

    def write(self, command, error=""):
        self.log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        tree = self.load_tree()
        root = tree.getroot()

        event = ET.SubElement(
            root,
            "event",
        )

        ET.SubElement(
            event,
            "datetime",
        ).text = datetime.now().isoformat(
            timespec="seconds"
        )

        ET.SubElement(
            event,
            "command",
        ).text = command

        ET.SubElement(
            event,
            "error",
        ).text = error

        ET.indent(
            tree,
            space="    ",
        )

        tree.write(
            self.log_path,
            encoding="utf-8",
            xml_declaration=True,
        )


class VirtualFileSystem:
    """Виртуальная файловая система из ZIP."""

    def __init__(self, zip_path):
        self.zip_path = zip_path
        self.files = {}
        self.directories = {"/"}

    def load(self):
        """Загрузить VFS в память."""
        if not self.zip_path:
            raise ValueError(
                "путь к VFS не указан"
            )

        if not os.path.exists(self.zip_path):
            raise FileNotFoundError(
                f"VFS не найдена: {self.zip_path}"
            )

        try:
            self.read_archive()
        except zipfile.BadZipFile as error:
            raise ValueError(
                "неверный формат VFS"
            ) from error

    def read_archive(self):
        """Прочитать ZIP без распаковки."""
        with zipfile.ZipFile(
            self.zip_path,
            "r",
        ) as archive:
            for name in archive.namelist():
                clean_name = name.replace(
                    "\\",
                    "/",
                ).strip("/")

                if not clean_name:
                    continue

                if name.endswith("/"):
                    self.add_directories(
                        clean_name
                    )
                    continue

                self.files[
                    "/" + clean_name
                ] = archive.read(name)

                parent = posixpath.dirname(
                    "/" + clean_name
                )

                self.add_directories(
                    parent
                )

    def add_directories(self, path):
        """Добавить директории в список VFS."""
        path = "/" + path.strip("/")

        while path not in ("", "/"):
            self.directories.add(path)
            path = posixpath.dirname(path)

        self.directories.add("/")

    def normalize_path(self, current_dir, path):
        """Получить абсолютный путь внутри VFS."""
        if not path:
            return current_dir

        if path.startswith("/"):
            result = posixpath.normpath(path)
        else:
            result = posixpath.normpath(
                posixpath.join(
                    current_dir,
                    path,
                )
            )

        if not result.startswith("/"):
            result = "/" + result

        return result

    def list_directory(self, directory):
        """Получить содержимое каталога."""
        if directory not in self.directories:
            raise ValueError(
                f"каталог не найден: {directory}"
            )

        items = set()

        prefix = directory.rstrip("/")

        if prefix:
            prefix += "/"
        else:
            prefix = "/"

        for path in self.directories:
            if path == directory:
                continue

            if path.startswith(prefix):
                rest = path[len(prefix):]

                if rest and "/" not in rest:
                    items.add(rest + "/")

        for path in self.files:
            if path.startswith(prefix):
                rest = path[len(prefix):]

                if rest and "/" not in rest:
                    items.add(rest)

        return sorted(items)


class ShellEmulator:
    """Графический эмулятор оболочки."""

    def __init__(self, root, arguments):
        self.root = root
        self.arguments = arguments

        self.logger = XmlLogger(
            arguments.log
        )

        self.vfs = None
        self.current_dir = "/"

        self.setup_window()
        self.create_widgets()

        self.print_output(
            "Shell emulator started."
        )

        self.print_configuration()
        self.load_vfs()

        if self.arguments.script:
            self.run_startup_script(
                self.arguments.script
            )

    def setup_window(self):
        username = getpass.getuser()
        hostname = socket.gethostname()

        self.root.title(
            f"Эмулятор - "
            f"[{username}@{hostname}]"
        )

        self.root.geometry(
            "800x500"
        )

    def create_widgets(self):
        self.output = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            font=("Consolas", 11),
            state=tk.DISABLED,
        )

        self.output.pack(
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=10,
        )

        self.entry = tk.Entry(
            self.root,
            font=("Consolas", 11),
        )

        self.entry.pack(
            fill=tk.X,
            padx=10,
            pady=(0, 10),
        )

        self.entry.bind(
            "<Return>",
            self.execute_command,
        )

        self.entry.focus()

    def print_output(self, text):
        self.output.config(
            state=tk.NORMAL
        )

        self.output.insert(
            tk.END,
            text + "\n",
        )

        self.output.see(
            tk.END
        )

        self.output.config(
            state=tk.DISABLED
        )

    def print_configuration(self):
        self.print_output(
            f"VFS: {self.arguments.vfs}"
        )

        self.print_output(
            f"LOG: {self.arguments.log}"
        )

        self.print_output(
            f"SCRIPT: {self.arguments.script}"
        )

    def load_vfs(self):
        if not self.arguments.vfs:
            return

        try:
            self.vfs = VirtualFileSystem(
                self.arguments.vfs
            )

            self.vfs.load()

            self.print_output(
                "VFS загружена: "
                f"{self.arguments.vfs}"
            )

        except Exception as error:
            self.vfs = None

            self.print_output(
                "Ошибка загрузки VFS: "
                f"{error}"
            )

    def execute_command(self, event=None):
        command_line = (
            self.entry.get().strip()
        )

        self.entry.delete(
            0,
            tk.END,
        )

        if not command_line:
            return

        self.process_command(
            command_line
        )

    def process_command(self, command_line):
        self.print_output(
            f"> {command_line}"
        )

        error_message = ""

        try:
            parts = parse_command(
                command_line
            )

            if not parts:
                return

            command = parts[0]
            args = parts[1:]

            self.dispatch_command(
                command,
                args,
            )

        except Exception as error:
            error_message = str(error)

            self.print_output(
                f"Ошибка: {error_message}"
            )

        finally:
            self.logger.write(
                command_line,
                error_message,
            )

    def dispatch_command(self, command, args):
        if command == "ls":
            self.command_ls(args)

        elif command == "cd":
            self.command_cd(args)

        elif command == "date":
            self.command_date(args)

        elif command == "rev":
            self.command_rev(args)

        elif command == "exit":
            self.root.destroy()

        else:
            raise ValueError(
                f"неизвестная команда "
                f"'{command}'"
            )

    def require_vfs(self):
        """Проверить наличие загруженной VFS."""
        if self.vfs is None:
            raise ValueError(
                "VFS не загружена"
            )

    def command_ls(self, args):
        """Команда ls."""
        self.require_vfs()

        if len(args) > 1:
            raise ValueError(
                "ls: слишком много аргументов"
            )

        path = (
            args[0]
            if args
            else self.current_dir
        )

        target = self.vfs.normalize_path(
            self.current_dir,
            path,
        )

        if target in self.vfs.files:
            self.print_output(
                posixpath.basename(target)
            )
            return

        items = self.vfs.list_directory(
            target
        )

        if items:
            self.print_output(
                "  ".join(items)
            )
        else:
            self.print_output(
                "(пусто)"
            )

    def command_cd(self, args):
        """Команда cd."""
        self.require_vfs()

        if len(args) != 1:
            raise ValueError(
                "cd: требуется один аргумент"
            )

        target = self.vfs.normalize_path(
            self.current_dir,
            args[0],
        )

        if target not in self.vfs.directories:
            raise ValueError(
                f"cd: каталог не найден: "
                f"{args[0]}"
            )

        self.current_dir = target

        self.print_output(
            f"Текущий каталог: "
            f"{self.current_dir}"
        )

    def command_date(self, args):
        """Команда date."""
        if args:
            raise ValueError(
                "date: аргументы не поддерживаются"
            )

        now = datetime.now()

        self.print_output(
            now.strftime(
                "%d.%m.%Y %H:%M:%S"
            )
        )

    def command_rev(self, args):
        """Команда rev."""
        if not args:
            raise ValueError(
                "rev: укажите текст"
            )

        text = " ".join(args)

        self.print_output(
            text[::-1]
        )

    def run_startup_script(self, script_path):
        path = Path(script_path)

        if not path.exists():
            self.print_output(
                "Ошибка стартового скрипта: "
                f"файл '{script_path}' "
                "не найден"
            )
            return

        try:
            lines = path.read_text(
                encoding="utf-8"
            ).splitlines()

        except OSError as error:
            self.print_output(
                "Ошибка стартового скрипта: "
                f"{error}"
            )
            return

        for line in lines:
            stripped = line.strip()

            if not stripped:
                continue

            if stripped.startswith("#"):
                continue

            self.process_command(
                stripped
            )


def main():
    arguments = parse_arguments()

    root = tk.Tk()

    ShellEmulator(
        root,
        arguments,
    )

    root.mainloop()


if __name__ == "__main__":
    main()