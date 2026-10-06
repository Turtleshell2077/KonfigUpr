"""Тесты эмулятора: парсер, команды, конфиг, скрипт и запуск программы."""

import contextlib
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from src import emulator

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROGRAM = ROOT / "src" / "emulator.py"
PROMPT = "$ "


def make_file(folder, name, text):
    """Создаёт в папке файл с текстом и возвращает путь к нему."""
    path = pathlib.Path(folder) / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def printed(func, *args):
    """Вызывает func(*args) и возвращает всё, что она напечатала."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        func(*args)
    return out.getvalue()


def exit_message(func, *args):
    """Вызывает func(*args), которая должна завершить работу с сообщением."""
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            func(*args)
        except SystemExit as error:
            return str(error.code)
    return ""


def start_program(args, text=""):
    """Запускает src/emulator.py как отдельную программу."""
    return subprocess.run(
        [sys.executable, str(PROGRAM), *args],
        input=text, capture_output=True, text=True, encoding="utf-8",
        cwd=ROOT, env=dict(os.environ, PYTHONUTF8="1"),
        timeout=60, check=False)


class PromptAndParserTests(unittest.TestCase):
    """Приглашение к вводу и разбор строки."""

    def test_prompt_format(self):
        """Приглашение имеет вид username@hostname:~$ ."""
        with mock.patch("getpass.getuser", return_value="bob"):
            with mock.patch("socket.gethostname", return_value="pc"):
                self.assertEqual(emulator.get_prompt(), "bob@pc:~$ ")

    def test_command_and_arguments(self):
        """Строка делится по пробелам на команду и аргументы."""
        result = emulator.parse_line("  ls   -l  /tmp ")
        self.assertEqual(result, ("ls", ["-l", "/tmp"]))

    def test_empty_line(self):
        """Пустая строка не содержит команды."""
        self.assertEqual(emulator.parse_line("   "), ("", []))

    def test_comment_line(self):
        """Строка-комментарий не содержит команды."""
        self.assertEqual(emulator.parse_line("# comment"), ("", []))

    def test_comment_after_command(self):
        """Комментарий после команды отбрасывается."""
        result = emulator.parse_line("ls -l # list files")
        self.assertEqual(result, ("ls", ["-l"]))


class CommandTests(unittest.TestCase):
    """Команды ls, cd, exit и неизвестная команда."""

    def test_ls_stub(self):
        """Заглушка ls печатает своё имя и аргументы."""
        out = printed(emulator.run_line, "ls -l /tmp")
        self.assertEqual(out, "command: ls, arguments: ['-l', '/tmp']\n")

    def test_cd_stub(self):
        """Заглушка cd печатает своё имя и аргументы."""
        out = printed(emulator.run_line, "cd /home")
        self.assertEqual(out, "command: cd, arguments: ['/home']\n")

    def test_unknown_command(self):
        """Неизвестная команда даёт сообщение об ошибке."""
        out = printed(emulator.run_line, "foo bar")
        self.assertEqual(out, "foo: command not found\n")

    def test_exit(self):
        """Команда exit завершает работу эмулятора."""
        with self.assertRaises(SystemExit):
            emulator.run_line("exit")

    def test_empty_line_does_nothing(self):
        """Пустая строка и комментарий ничего не печатают."""
        self.assertEqual(printed(emulator.run_line, ""), "")
        self.assertEqual(printed(emulator.run_line, "# note"), "")


class ConfigTests(unittest.TestCase):
    """Чтение YAML-конфига и приоритет значений."""

    def test_read_both_values(self):
        """Из конфига читаются пути к VFS и к скрипту."""
        with tempfile.TemporaryDirectory() as folder:
            path = make_file(folder, "c.yaml", "vfs: a.xml\nscript: s.txt\n")
            data = emulator.read_config(path)
        self.assertEqual(data, {"vfs": "a.xml", "script": "s.txt"})

    def test_empty_config(self):
        """Пустой конфиг — это конфиг без настроек."""
        with tempfile.TemporaryDirectory() as folder:
            path = make_file(folder, "c.yaml", "# nothing\n")
            self.assertEqual(emulator.read_config(path), {})

    def test_missing_config(self):
        """Нет файла конфига — сообщение об ошибке."""
        message = exit_message(emulator.read_config, "no/such.yaml")
        self.assertIn("Config error: cannot read 'no/such.yaml'", message)

    def test_invalid_yaml(self):
        """Некорректный YAML — сообщение об ошибке."""
        with tempfile.TemporaryDirectory() as folder:
            path = make_file(folder, "c.yaml", "vfs: [a.xml\nscript: s\n")
            message = exit_message(emulator.read_config, path)
        self.assertIn("Config error: cannot read", message)

    def test_config_is_not_a_mapping(self):
        """Список вместо пар «ключ: значение» — ошибка."""
        with tempfile.TemporaryDirectory() as folder:
            path = make_file(folder, "c.yaml", "- a\n- b\n")
            message = exit_message(emulator.read_config, path)
        self.assertIn("must contain 'key: value' pairs", message)

    def test_value_is_not_a_string(self):
        """Число вместо пути — ошибка."""
        with tempfile.TemporaryDirectory() as folder:
            path = make_file(folder, "c.yaml", "vfs: 42\n")
            message = exit_message(emulator.read_config, path)
        self.assertIn("'vfs'", message)
        self.assertIn("must be a string", message)

    def test_file_has_priority(self):
        """Значения из файла важнее значений из командной строки."""
        args = emulator.parse_args(["--vfs", "cli.xml", "--script", "cli.txt"])
        file_data = {"vfs": "file.xml", "script": "file.txt"}
        settings = emulator.merge_settings(args, file_data)
        self.assertEqual(settings, file_data)

    def test_command_line_fills_gaps(self):
        """Чего нет в файле, берётся из командной строки."""
        args = emulator.parse_args(["--vfs", "cli.xml", "--script", "cli.txt"])
        settings = emulator.merge_settings(args, {"vfs": "file.xml"})
        self.assertEqual(settings, {"vfs": "file.xml", "script": "cli.txt"})

    def test_empty_value_in_file_does_not_erase(self):
        """Пустое значение в файле не стирает значение из командной строки."""
        args = emulator.parse_args(["--vfs", "cli.xml"])
        settings = emulator.merge_settings(args, {"vfs": None})
        self.assertEqual(settings["vfs"], "cli.xml")

    def test_no_parameters(self):
        """Без параметров все настройки не заданы."""
        settings = emulator.merge_settings(emulator.parse_args([]), {})
        self.assertEqual(settings, {"vfs": None, "script": None})

    def test_debug_output(self):
        """Отладочный вывод показывает параметры и итоговые значения."""
        args = emulator.parse_args(["--vfs", "a.xml", "--config", "c.yaml"])
        settings = {"vfs": "a.xml", "script": None}
        out = printed(emulator.print_debug, args, {}, settings)
        self.assertIn("vfs=a.xml, script=None, config=c.yaml", out)
        self.assertIn("used values : vfs=a.xml, script=None", out)


class ScriptTests(unittest.TestCase):
    """Выполнение стартового скрипта."""

    def run_text(self, text):
        """Выполняет скрипт с текстом text и возвращает его вывод."""
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as folder:
            path = make_file(folder, "start.txt", text)
            with contextlib.redirect_stdout(out):
                with contextlib.suppress(SystemExit):
                    emulator.run_script(path, PROMPT)
        return out.getvalue()

    def test_input_and_output_are_shown(self):
        """На экране видны и введённая команда, и её вывод."""
        out = self.run_text("ls -l\n")
        self.assertEqual(out, "$ ls -l\ncommand: ls, arguments: ['-l']\n")

    def test_comments(self):
        """Комментарии показываются, но не выполняются."""
        out = self.run_text("# hello\nls a # why\n")
        self.assertEqual(out, "$ # hello\n$ ls a # why\n"
                              "command: ls, arguments: ['a']\n")

    def test_blank_lines_are_skipped(self):
        """Пустые строки пропускаются."""
        self.assertEqual(self.run_text("\n  \n"), "")

    def test_errors_do_not_stop_script(self):
        """После ошибочной команды скрипт продолжается."""
        out = self.run_text("foo\nls\n")
        self.assertEqual(out, "$ foo\nfoo: command not found\n"
                              "$ ls\ncommand: ls, arguments: []\n")

    def test_exit_stops_script(self):
        """Команда exit прекращает выполнение скрипта."""
        out = self.run_text("exit\nls\n")
        self.assertEqual(out, "$ exit\n")

    def test_missing_script(self):
        """Нет файла скрипта — сообщение об ошибке."""
        message = exit_message(emulator.run_script, "no/such.txt", PROMPT)
        self.assertIn("Script error: cannot read 'no/such.txt'", message)


class ReplTests(unittest.TestCase):
    """Интерактивный цикл (ввод подменяется)."""

    def run_input(self, lines):
        """Запускает REPL на заданных строках и возвращает вывод."""
        with mock.patch("builtins.input", side_effect=lines):
            return printed(emulator.run_repl, PROMPT)

    def test_session(self):
        """Команды выполняются, пустые строки пропускаются."""
        out = self.run_input(["ls", "", "foo", EOFError()])
        self.assertEqual(out, "command: ls, arguments: []\n"
                              "foo: command not found\nexit\n")

    def test_ctrl_c(self):
        """Ctrl+C сбрасывает строку, но работа продолжается."""
        out = self.run_input([KeyboardInterrupt(), "cd", EOFError()])
        self.assertEqual(out, "\ncommand: cd, arguments: []\nexit\n")


class ProgramTests(unittest.TestCase):
    """Запуск программы целиком, как это делает пользователь."""

    def test_no_parameters(self):
        """Без параметров: подпись, отладочный вывод и конец ввода."""
        result = start_program([])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines()[0], emulator.BANNER)
        self.assertIn("[debug] command line: vfs=None", result.stdout)
        self.assertTrue(result.stdout.endswith("exit\n"))

    def test_config_beats_command_line(self):
        """Конфиг важнее командной строки, скрипт из конфига выполняется."""
        result = start_program(["--vfs", "cli.xml", "--script",
                                "examples/start_a.txt", "--config",
                                "examples/config_full.yaml"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("used values : vfs=examples/vfs/sample.xml, "
                      "script=examples/start_b.txt", result.stdout)
        self.assertIn("# Start script B", result.stdout)
        self.assertNotIn("# Start script A", result.stdout)

    def test_script_dialog_with_comments_and_error(self):
        """Скрипт показывает диалог, комментарии и ошибку команды."""
        result = start_program(["--script", "examples/start_a.txt"])
        self.assertIn("# Start script A", result.stdout)
        self.assertIn("command: ls, arguments: ['-l', '/tmp']", result.stdout)
        self.assertIn("foo: command not found", result.stdout)

    def test_bad_config_stops_program(self):
        """Ошибка в конфиге: сообщение и код завершения 1."""
        result = start_program(["--config", "examples/config_bad_syntax.yaml"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("Config error", result.stderr)

    def test_missing_script_stops_program(self):
        """Нет файла скрипта: сообщение и код завершения 1."""
        result = start_program(["--script", "missing.txt"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("Script error", result.stderr)

    def test_unknown_parameter(self):
        """Неизвестный параметр: справка по использованию, код 2."""
        result = start_program(["--unknown"])
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage:", result.stderr)


if __name__ == "__main__":
    unittest.main()
