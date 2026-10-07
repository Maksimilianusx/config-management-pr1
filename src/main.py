import argparse
import getpass
import os
import posixpath
import shlex
import socket
import tkinter as tk
import xml.etree.ElementTree as element_tree
import zipfile

from datetime import datetime
from pathlib import Path
from tkinter import scrolledtext


def expand_environment(command_line):
    """Раскрыть переменные окружения реальной ОС."""
    if "HOME" not in os.environ:
        os.environ["HOME"] = os.environ.get("USERPROFILE", "")
    return os.path.expandvars(command_line)


def parse_command(command_line):
    """Разобрать командную строку."""
    expanded_line = expand_environment(command_line)
    try:
        return shlex.split(expanded_line, posix=False)
    except ValueError as error:
        raise ValueError(f"ошибка разбора команды: {error}") from error


def parse_arguments():
    """Получить параметры запуска программы."""
    parser = argparse.ArgumentParser(description="Эмулятор оболочки ОС")
    parser.add_argument("--vfs", required=True)
    parser.add_argument("--log", default="logs/log.xml")
    parser.add_argument("--script", default="")
    return parser.parse_args()


class XmlLogger:
    """XML-журнал событий выполнения команд."""

    def __init__(self, log_path):
        self.log_path = Path(log_path)

    def _load_tree(self):
        if not self.log_path.exists():
            root = element_tree.Element("log")
            return element_tree.ElementTree(root)

        try:
            return element_tree.parse(self.log_path)
        except element_tree.ParseError:
            root = element_tree.Element("log")
            return element_tree.ElementTree(root)

    def write(self, command, error=""):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        tree = self._load_tree()
        root = tree.getroot()

        event = element_tree.SubElement(root, "event")
        now = datetime.now().isoformat(timespec="seconds")
        element_tree.SubElement(event, "datetime").text = now
        element_tree.SubElement(event, "command").text = command
        element_tree.SubElement(event, "error").text = error

        element_tree.indent(tree, space="    ")
        tree.write(
            self.log_path,
            encoding="utf-8",
            xml_declaration=True,
        )


class VirtualFileSystem:
    """ZIP-VFS, загружаемая и изменяемая только в памяти."""

    def __init__(self, zip_path):
        self.zip_path = Path(zip_path)
        self.files = {}
        self.directories = {"/"}
        self.cwd = "/"
        self._load_zip()

    def _load_zip(self):
        self._validate_zip()
        with zipfile.ZipFile(self.zip_path, "r") as archive:
            for info in archive.infolist():
                self._load_entry(archive, info)

    def _validate_zip(self):
        if not self.zip_path.exists():
            raise ValueError(f"VFS-файл '{self.zip_path}' не найден")
        if not zipfile.is_zipfile(self.zip_path):
            raise ValueError(
                f"VFS-файл '{self.zip_path}' имеет неверный формат"
            )

    def _load_entry(self, archive, info):
        raw_name = info.filename.replace("\\", "/").strip("/")
        if not raw_name:
            return

        full_path = "/" + raw_name
        if info.is_dir() or info.filename.endswith("/"):
            self._add_directory(full_path)
            return

        parent = posixpath.dirname(full_path) or "/"
        self._add_directory(parent)
        self.files[full_path] = archive.read(info.filename)

    def _add_directory(self, path):
        current = self._normalize(path)
        while True:
            self.directories.add(current)
            if current == "/":
                return
            current = posixpath.dirname(current) or "/"

    def _normalize(self, path):
        if path is None or path == "":
            return self.cwd

        clean_path = path.replace("\\", "/")
        if clean_path.startswith("/"):
            combined = clean_path
        else:
            combined = posixpath.join(self.cwd, clean_path)

        normalized = posixpath.normpath(combined)
        if normalized.startswith("/"):
            return normalized
        return "/" + normalized

    def list_dir(self, path=""):
        target = self._normalize(path)
        self._ensure_list_target(target, path)

        if target in self.files:
            return [posixpath.basename(target)]

        return self._collect_children(target)

    def _ensure_list_target(self, target, original):
        if target not in self.directories and target not in self.files:
            raise ValueError(f"ls: '{original}' не найден")

    def _collect_children(self, target):
        children = set()

        for directory in self.directories:
            if self._is_direct_child(directory, target):
                children.add(posixpath.basename(directory) + "/")

        for file_path in self.files:
            if self._is_direct_child(file_path, target):
                children.add(posixpath.basename(file_path))

        return sorted(children, key=str.lower)

    @staticmethod
    def _is_direct_child(path, parent):
        if path == parent:
            return False
        path_parent = posixpath.dirname(path) or "/"
        return path_parent == parent

    def change_dir(self, path):
        target = self._normalize(path)
        if target not in self.directories:
            raise ValueError(f"cd: каталог '{path}' не найден")
        self.cwd = target

    def touch(self, path):
        target = self._prepare_touch_path(path)
        if target not in self.files:
            self.files[target] = b""

    def _prepare_touch_path(self, path):
        if not path:
            raise ValueError("touch: не указано имя файла")

        target = self._normalize(path)
        parent = posixpath.dirname(target) or "/"

        if parent not in self.directories:
            raise ValueError(
                f"touch: родительский каталог '{parent}' не найден"
            )
        if target in self.directories:
            raise ValueError(f"touch: '{path}' является каталогом")
        return target


class ShellEmulator:
    """Графический эмулятор оболочки."""

    def __init__(self, root, arguments):
        self.root = root
        self.arguments = arguments
        self.logger = XmlLogger(arguments.log)
        self.vfs = None
        self._configure_window()
        self._create_widgets()
        self._start_emulator()

    def _configure_window(self):
        username = getpass.getuser()
        hostname = socket.gethostname()
        self.root.title(f"Эмулятор - [{username}@{hostname}]")
        self.root.geometry("800x500")

    def _create_widgets(self):
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

        self.entry = tk.Entry(self.root, font=("Consolas", 11))
        self.entry.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.entry.bind("<Return>", self.execute_command)
        self.entry.focus()

    def _start_emulator(self):
        self.print_output("Shell emulator started.")
        self._print_configuration()

        try:
            self.vfs = VirtualFileSystem(self.arguments.vfs)
        except ValueError as error:
            self.print_output(f"Ошибка загрузки VFS: {error}")
            self.entry.config(state=tk.DISABLED)
            return

        self.print_output("VFS loaded successfully.")
        if self.arguments.script:
            self.run_startup_script(self.arguments.script)

    def _print_configuration(self):
        self.print_output(f"VFS: {self.arguments.vfs}")
        self.print_output(f"LOG: {self.arguments.log}")
        self.print_output(f"SCRIPT: {self.arguments.script}")

    def print_output(self, text):
        self.output.config(state=tk.NORMAL)
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)
        self.output.config(state=tk.DISABLED)

    def execute_command(self, event=None):
        command_line = self.entry.get().strip()
        self.entry.delete(0, tk.END)
        if command_line:
            self.process_command(command_line)

    def process_command(self, command_line):
        self.print_output(f"> {command_line}")
        error_message = ""

        try:
            parts = parse_command(command_line)
            if parts:
                self._dispatch(parts[0], parts[1:])
        except (ValueError, OSError) as error:
            error_message = str(error)
            self.print_output(f"Ошибка: {error_message}")
        finally:
            self.logger.write(command_line, error_message)

    def _dispatch(self, command, args):
        commands = {
            "ls": self._command_ls,
            "cd": self._command_cd,
            "date": self._command_date,
            "rev": self._command_rev,
            "touch": self._command_touch,
            "exit": self._command_exit,
        }

        handler = commands.get(command)
        if handler is None:
            raise ValueError(f"неизвестная команда '{command}'")
        handler(args)

    def _command_ls(self, args):
        if len(args) > 1:
            raise ValueError("ls: слишком много аргументов")

        path = args[0] if args else ""
        items = self.vfs.list_dir(path)
        self.print_output("  ".join(items))

    def _command_cd(self, args):
        if len(args) != 1:
            raise ValueError("cd: требуется ровно один аргумент")
        self.vfs.change_dir(args[0])

    def _command_date(self, args):
        if args:
            raise ValueError("date: команда не принимает аргументы")
        value = datetime.now().strftime("%a %b %d %H:%M:%S %Y")
        self.print_output(value)

    def _command_rev(self, args):
        if not args:
            raise ValueError("rev: укажите строку")
        self.print_output(" ".join(args)[::-1])

    def _command_touch(self, args):
        if len(args) != 1:
            raise ValueError("touch: требуется ровно один аргумент")
        self.vfs.touch(args[0])

    def _command_exit(self, args):
        if args:
            raise ValueError("exit: команда не принимает аргументы")
        self.root.destroy()

    def run_startup_script(self, script_path):
        path = Path(script_path)
        lines = self._read_script(path, script_path)

        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                self.process_command(stripped)

    def _read_script(self, path, script_path):
        if not path.exists():
            self.print_output(
                f"Ошибка стартового скрипта: "
                f"файл '{script_path}' не найден"
            )
            return []

        try:
            return path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            self.print_output(
                f"Ошибка стартового скрипта: {error}"
            )
            return []


def main():
    arguments = parse_arguments()
    root = tk.Tk()
    ShellEmulator(root, arguments)
    root.mainloop()


if __name__ == "__main__":
    main()
