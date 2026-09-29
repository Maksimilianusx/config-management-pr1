import os
import socket
import tkinter as tk
from tkinter import scrolledtext


class ShellEmulator:
    def __init__(self, root):
        self.root = root

        username = os.getlogin()
        hostname = socket.gethostname()

        self.root.title(f"Эмулятор - [{username}@{hostname}]")
        self.root.geometry("800x500")

        self.output = scrolledtext.ScrolledText(
            root,
            wrap=tk.WORD,
            font=("Consolas", 11),
            state=tk.DISABLED
        )
        self.output.pack(
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=10
        )

        self.entry = tk.Entry(
            root,
            font=("Consolas", 11)
        )
        self.entry.pack(
            fill=tk.X,
            padx=10,
            pady=(0, 10)
        )

        self.entry.bind(
            "<Return>",
            self.execute_command
        )
        self.entry.focus()

        self.print_output(
            "Shell emulator started."
        )

    def print_output(self, text):
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

    def execute_command(self, event=None):
        command_line = self.entry.get().strip()

        self.entry.delete(
            0,
            tk.END
        )

        if not command_line:
            return

        self.print_output(
            f"> {command_line}"
        )

        if "HOME" not in os.environ:
            os.environ["HOME"] = os.environ.get(
                "USERPROFILE",
                ""
            )

        command_line = os.path.expandvars(
            command_line
        )

        parts = command_line.split()

        if not parts:
            return

        command = parts[0]
        args = parts[1:]

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
            self.print_output(
                f"Ошибка: неизвестная команда '{command}'"
            )


def main():
    root = tk.Tk()

    ShellEmulator(
        root
    )

    root.mainloop()


if __name__ == "__main__":
    main()