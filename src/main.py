import getpass
import os
import shlex
import socket
import tkinter as tk
from tkinter import scrolledtext


def expand_environment(command_line):
    """Раскрыть переменные окружения в командной строке."""
    if "HOME" not in os.environ:
        os.environ["HOME"] = os.environ.get("USERPROFILE", "")

    return os.path.expandvars(command_line)


def parse_command(command_line):
    """Разобрать командную строку на команду и аргументы."""
    expanded_line = expand_environment(command_line)

    try:
        return shlex.split(expanded_line, posix=False)
    except ValueError as error:
        raise ValueError(
            f"ошибка разбора команды: {error}"
        ) from error


class ShellEmulator:
    """Графический эмулятор командной оболочки."""

    def __init__(self, root):
        self.root = root

        username = getpass.getuser()
        hostname = socket.gethostname()

        self.root.title(
            f"Эмулятор - [{username}@{hostname}]"
        )
        self.root.geometry("800x500")

        self.create_widgets()
        self.print_output("Shell emulator started.")

    def create_widgets(self):
        """Создать элементы графического интерфейса."""
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
        """Вывести текст в окно эмулятора."""
        self.output.config(state=tk.NORMAL)
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)
        self.output.config(state=tk.DISABLED)

    def execute_command(self, event=None):
        """Получить введённую команду и выполнить её."""
        command_line = self.entry.get().strip()
        self.entry.delete(0, tk.END)

        if not command_line:
            return

        self.print_output(f"> {command_line}")

        try:
            parts = parse_command(command_line)
        except ValueError as error:
            self.print_output(f"Ошибка: {error}")
            return

        if not parts:
            return

        command = parts[0]
        args = parts[1:]

        self.dispatch_command(command, args)

    def dispatch_command(self, command, args):
        """Выполнить поддерживаемую команду."""
        if command == "ls":
            self.print_output(f"ls: {args}")

        elif command == "cd":
            self.print_output(f"cd: {args}")

        elif command == "exit":
            self.root.destroy()

        else:
            self.print_output(
                f"Ошибка: неизвестная команда '{command}'"
            )


def main():
    """Запустить графический эмулятор."""
    root = tk.Tk()
    ShellEmulator(root)
    root.mainloop()


if __name__ == "__main__":
    main()