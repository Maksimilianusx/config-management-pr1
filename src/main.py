import argparse
import getpass
import os
import shlex
import socket
import tkinter as tk
import xml.etree.ElementTree as ET

from datetime import datetime
from pathlib import Path
from tkinter import scrolledtext


def expand_environment(command_line):
    """Раскрыть переменные окружения."""
    if "HOME" not in os.environ:
        os.environ["HOME"] = os.environ.get("USERPROFILE", "")

    return os.path.expandvars(command_line)


def parse_command(command_line):
    """Разобрать командную строку."""
    expanded_line = expand_environment(command_line)

    try:
        return shlex.split(expanded_line, posix=False)
    except ValueError as error:
        raise ValueError(
            f"ошибка разбора команды: {error}"
        ) from error


def parse_arguments():
    """Получить параметры запуска программы."""
    parser = argparse.ArgumentParser(
        description="Эмулятор оболочки ОС"
    )

    parser.add_argument(
        "--vfs",
        default="",
        help="Путь к физическому расположению VFS",
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
    """XML-журнал событий выполнения команд."""

    def __init__(self, log_path):
        self.log_path = Path(log_path)

    def write(self, command, error=""):
        """Записать событие в XML-файл."""
        self.log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if self.log_path.exists():
            try:
                tree = ET.parse(self.log_path)
                root = tree.getroot()
            except ET.ParseError:
                root = ET.Element("log")
                tree = ET.ElementTree(root)
        else:
            root = ET.Element("log")
            tree = ET.ElementTree(root)

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


class ShellEmulator:
    """Графический эмулятор оболочки."""

    def __init__(self, root, arguments):
        self.root = root
        self.arguments = arguments
        self.logger = XmlLogger(arguments.log)

        username = getpass.getuser()
        hostname = socket.gethostname()

        self.root.title(
            f"Эмулятор - [{username}@{hostname}]"
        )
        self.root.geometry("800x500")

        self.create_widgets()

        self.print_output(
            "Shell emulator started."
        )

        self.print_configuration()

        if self.arguments.script:
            self.run_startup_script(
                self.arguments.script
            )

    def create_widgets(self):
        """Создать GUI."""
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
        """Вывести текст в окно."""
        self.output.config(
            state=tk.NORMAL
        )

        self.output.insert(
            tk.END,
            text + "\n"
        )

        self.output.see(
            tk.END
        )

        self.output.config(
            state=tk.DISABLED
        )

    def print_configuration(self):
        """Отладочный вывод параметров запуска."""
        self.print_output(
            f"VFS: {self.arguments.vfs}"
        )

        self.print_output(
            f"LOG: {self.arguments.log}"
        )

        self.print_output(
            f"SCRIPT: {self.arguments.script}"
        )

    def execute_command(self, event=None):
        """Обработать команду из GUI."""
        command_line = self.entry.get().strip()

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
        """Выполнить одну команду."""
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

        except ValueError as error:
            error_message = str(error)

            self.print_output(
                f"Ошибка: {error_message}"
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
        """Выполнить поддерживаемую команду."""
        if command == "ls":
            self.print_output(
                f"ls: {args}"
            )

        elif command == "cd":
            self.print_output(
                f"cd: {args}"
            )

        elif command == "exit":
            self.root.destroy()

        else:
            raise ValueError(
                f"неизвестная команда '{command}'"
            )

    def run_startup_script(self, script_path):
        """Выполнить стартовый скрипт."""
        path = Path(script_path)

        if not path.exists():
            self.print_output(
                f"Ошибка стартового скрипта: "
                f"файл '{script_path}' не найден"
            )
            return

        try:
            lines = path.read_text(
                encoding="utf-8"
            ).splitlines()

        except OSError as error:
            self.print_output(
                f"Ошибка стартового скрипта: {error}"
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
    """Запустить программу."""
    arguments = parse_arguments()

    root = tk.Tk()

    ShellEmulator(
        root,
        arguments,
    )

    root.mainloop()


if __name__ == "__main__":
    main()