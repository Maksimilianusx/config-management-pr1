import os
import unittest

from src.main import parse_command


class ParseCommandTests(unittest.TestCase):
    """Тесты парсера команд."""

    def test_simple_command(self):
        """Проверить обычную команду с аргументом."""
        result = parse_command("ls test")

        self.assertEqual(
            result,
            ["ls", "test"],
        )

    def test_home_variable(self):
        """Проверить раскрытие переменной HOME."""
        os.environ["HOME"] = r"C:\Users\makson"

        result = parse_command("ls $HOME")

        self.assertEqual(
            result,
            ["ls", r"C:\Users\makson"],
        )

    def test_cd_command(self):
        """Проверить команду cd."""
        result = parse_command("cd folder")

        self.assertEqual(
            result,
            ["cd", "folder"],
        )


if __name__ == "__main__":
    unittest.main()