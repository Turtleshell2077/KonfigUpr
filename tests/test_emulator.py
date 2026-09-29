"""Тесты этапа 1: приглашение, парсер, команды и цикл REPL."""

import contextlib
import io
import os
import pathlib
import subprocess
import sys
import unittest
from unittest import mock

from src import emulator

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
CUSTOM_EXIT_CODE = 3
WRAPPED_EXIT_CODE = 255
PROCESS_TIMEOUT = 30


def capture(func, *args):
    """Вызывает func(*args) и возвращает пару (stdout, stderr)."""
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        func(*args)
    return out.getvalue(), err.getvalue()


def run_session(lines):
    """Запускает REPL на заданных строках ввода.

    Возвращает stdout, stderr и подменённую функцию input. Выход по
    команде exit (SystemExit) гасится, чтобы можно было проверить вывод.
    """
    out = io.StringIO()
    err = io.StringIO()
    with mock.patch("builtins.input", side_effect=lines) as fake_input:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with contextlib.suppress(SystemExit):
                emulator.run_repl("$ ")
    return out.getvalue(), err.getvalue(), fake_input


class ParseLineTests(unittest.TestCase):
    """Проверки разбиения строки на команду и аргументы."""

    def test_command_with_arguments(self):
        """Строка делится по пробелам на команду и аргументы."""
        result = emulator.parse_line("ls -l /tmp")
        self.assertEqual(result, ("ls", ["-l", "/tmp"]))

    def test_command_without_arguments(self):
        """Команда без аргументов даёт пустой список аргументов."""
        self.assertEqual(emulator.parse_line("cd"), ("cd", []))

    def test_repeated_spaces_and_tabs(self):
        """Повторяющиеся пробелы и табуляции считаются одним разделителем."""
        result = emulator.parse_line("  ls \t -a   dir  ")
        self.assertEqual(result, ("ls", ["-a", "dir"]))

    def test_empty_line(self):
        """Пустая строка даёт пустую команду."""
        self.assertEqual(emulator.parse_line(""), ("", []))

    def test_whitespace_only_line(self):
        """Строка из одних пробелов даёт пустую команду."""
        self.assertEqual(emulator.parse_line("   \t "), ("", []))

    def test_leading_bom_is_ignored(self):
        """BOM в начале строки (например, из PowerShell) не мешает разбору."""
        result = emulator.parse_line("﻿ls -l")
        self.assertEqual(result, ("ls", ["-l"]))

    def test_quotes_are_not_special(self):
        """Кавычки на этом этапе не обрабатываются, разбор идёт по пробелам."""
        result = emulator.parse_line('ls "a b"')
        self.assertEqual(result, ("ls", ['"a', 'b"']))


class PromptTests(unittest.TestCase):
    """Проверки формирования приглашения к вводу."""

    def test_prompt_format(self):
        """Приглашение имеет вид username@hostname:~$ ."""
        with mock.patch.object(emulator, "get_username", return_value="bob"):
            with mock.patch.object(emulator, "get_hostname",
                                   return_value="pc"):
                self.assertEqual(emulator.build_prompt(), "bob@pc:~$ ")

    def test_real_prompt_shape(self):
        """Приглашение из реальных данных ОС содержит «@» и оканчивается ~$."""
        prompt = emulator.build_prompt()
        self.assertIn("@", prompt)
        self.assertTrue(prompt.endswith(":~$ "))

    def test_username_from_getpass(self):
        """Имя пользователя берётся из getpass."""
        with mock.patch("getpass.getuser", return_value="alice"):
            self.assertEqual(emulator.get_username(), "alice")

    def test_username_fallback_on_errors(self):
        """При ошибке определения имени используется значение по умолчанию."""
        for error in (ImportError, KeyError, OSError):
            with mock.patch("getpass.getuser", side_effect=error):
                self.assertEqual(emulator.get_username(), "user")

    def test_username_fallback_on_empty(self):
        """Пустое имя заменяется значением по умолчанию."""
        with mock.patch("getpass.getuser", return_value=""):
            self.assertEqual(emulator.get_username(), "user")

    def test_hostname_is_short(self):
        """Имя хоста обрезается до первой точки."""
        with mock.patch("socket.gethostname", return_value="pc.example.org"):
            self.assertEqual(emulator.get_hostname(), "pc")

    def test_hostname_fallback_on_error(self):
        """При ошибке определения хоста используется значение по умолчанию."""
        with mock.patch("socket.gethostname", side_effect=OSError):
            self.assertEqual(emulator.get_hostname(), "localhost")

    def test_hostname_fallback_on_empty(self):
        """Пустое имя хоста заменяется значением по умолчанию."""
        with mock.patch("socket.gethostname", return_value=""):
            self.assertEqual(emulator.get_hostname(), "localhost")


class CommandTests(unittest.TestCase):
    """Проверки команд ls, cd, exit и неизвестных команд."""

    def test_ls_stub_prints_name_and_args(self):
        """Заглушка ls печатает своё имя и аргументы."""
        out, err = capture(emulator.execute, "ls", ["-l", "/tmp"])
        self.assertEqual(out, "command: ls, arguments: ['-l', '/tmp']\n")
        self.assertEqual(err, "")

    def test_cd_stub_prints_name_and_args(self):
        """Заглушка cd печатает своё имя и аргументы."""
        out, err = capture(emulator.execute, "cd", ["/home"])
        self.assertEqual(out, "command: cd, arguments: ['/home']\n")
        self.assertEqual(err, "")

    def test_stub_without_arguments(self):
        """Заглушка без аргументов печатает пустой список."""
        out, _ = capture(emulator.execute, "ls", [])
        self.assertEqual(out, "command: ls, arguments: []\n")

    def test_unknown_command(self):
        """Неизвестная команда даёт сообщение об ошибке в stderr."""
        out, err = capture(emulator.execute, "foo", ["bar"])
        self.assertEqual(out, "")
        self.assertEqual(err, "foo: command not found\n")

    def test_command_names_are_case_sensitive(self):
        """Имена команд чувствительны к регистру, как в UNIX."""
        _, err = capture(emulator.execute, "LS", [])
        self.assertEqual(err, "LS: command not found\n")

    def test_exit_without_arguments(self):
        """Команда exit без аргументов завершает работу с кодом 0."""
        with self.assertRaises(SystemExit) as context:
            emulator.execute("exit", [])
        self.assertEqual(context.exception.code, emulator.EXIT_OK)

    def test_exit_with_code(self):
        """Команда exit принимает код возврата."""
        with self.assertRaises(SystemExit) as context:
            emulator.execute("exit", [str(CUSTOM_EXIT_CODE)])
        self.assertEqual(context.exception.code, CUSTOM_EXIT_CODE)

    def test_exit_negative_code_is_wrapped(self):
        """Отрицательный код приводится к диапазону 0..255, как в bash."""
        with self.assertRaises(SystemExit) as context:
            emulator.execute("exit", ["-1"])
        self.assertEqual(context.exception.code, WRAPPED_EXIT_CODE)

    def test_exit_non_numeric_argument(self):
        """Нечисловой аргумент даёт ошибку и код 2."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as context:
                emulator.execute("exit", ["abc"])
        self.assertEqual(context.exception.code, emulator.EXIT_MISUSE)
        self.assertEqual(err.getvalue(),
                         "exit: abc: numeric argument required\n")

    def test_exit_too_many_arguments(self):
        """При лишних аргументах ошибка выводится, а выхода нет."""
        out, err = capture(emulator.execute, "exit", ["1", "2"])
        self.assertEqual(out, "")
        self.assertEqual(err, "exit: too many arguments\n")


class ReplTests(unittest.TestCase):
    """Проверки цикла REPL с подменой ввода."""

    def test_prompt_is_passed_to_input(self):
        """Приглашение передаётся в input."""
        _, _, fake_input = run_session([EOFError()])
        fake_input.assert_called_with("$ ")

    def test_session(self):
        """Сессия: заглушки, пустые строки, ошибка и выход."""
        lines = ["ls -l", "", "   ", "cd /tmp", "foo", "exit"]
        out, err, _ = run_session(lines)
        self.assertEqual(out,
                         "command: ls, arguments: ['-l']\n"
                         "command: cd, arguments: ['/tmp']\n")
        self.assertEqual(err, "foo: command not found\n")

    def test_exit_stops_reading_input(self):
        """После exit новые строки не читаются."""
        _, _, fake_input = run_session(["exit", "ls"])
        self.assertEqual(fake_input.call_count, 1)

    def test_eof_ends_session(self):
        """Конец ввода (Ctrl+D) завершает REPL и печатает exit."""
        out, _, _ = run_session(["ls", EOFError()])
        self.assertEqual(out, "command: ls, arguments: []\nexit\n")

    def test_keyboard_interrupt_keeps_session(self):
        """Ctrl+C сбрасывает строку, но сессия продолжается."""
        out, _, _ = run_session([KeyboardInterrupt(), "cd", EOFError()])
        self.assertEqual(out, "\ncommand: cd, arguments: []\nexit\n")


class MainTests(unittest.TestCase):
    """Проверки точки входа и включения редактирования строки."""

    def test_main_returns_ok_on_end_of_input(self):
        """main возвращает код 0, когда ввод закончился."""
        with mock.patch("builtins.input", side_effect=EOFError):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(emulator.main(), emulator.EXIT_OK)

    def test_line_editing_requests_readline(self):
        """Редактирование строки включается через модуль readline."""
        with mock.patch("importlib.import_module") as fake_import:
            emulator.enable_line_editing()
        fake_import.assert_called_once_with("readline")

    def test_line_editing_without_readline(self):
        """Отсутствие readline (например, в Windows) не вызывает ошибки."""
        with mock.patch("importlib.import_module", side_effect=ImportError):
            emulator.enable_line_editing()


class ProcessTests(unittest.TestCase):
    """Проверки запуска эмулятора как отдельного процесса."""

    def run_emulator(self, text):
        """Запускает python -m src.emulator и подаёт text на stdin."""
        return subprocess.run(
            [sys.executable, "-m", "src.emulator"],
            input=text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=REPO_ROOT,
            env=dict(os.environ, PYTHONUTF8="1"),
            timeout=PROCESS_TIMEOUT,
            check=False,
        )

    def test_exit_code_and_output(self):
        """Процесс печатает вывод команд и возвращает код из exit."""
        result = self.run_emulator("ls -l /tmp\nfoo\nexit 3\n")
        self.assertEqual(result.returncode, CUSTOM_EXIT_CODE)
        self.assertIn("command: ls, arguments: ['-l', '/tmp']", result.stdout)
        self.assertIn("foo: command not found", result.stderr)
        self.assertIn(emulator.build_prompt(), result.stdout)

    def test_end_of_input(self):
        """Конец ввода завершает процесс с кодом 0."""
        result = self.run_emulator("")
        self.assertEqual(result.returncode, emulator.EXIT_OK)
        self.assertTrue(result.stdout.endswith("exit\n"))


if __name__ == "__main__":
    unittest.main()
