"""Тесты эмулятора: парсер, команды, конфиг, скрипт, VFS и запуск."""

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
MINIMAL = "examples/vfs/minimal.xml"
SAMPLE = "examples/vfs/sample.xml"


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


def vfs_from_text(body):
    """Загружает VFS из XML-текста, записанного во временный файл."""
    with tempfile.TemporaryDirectory() as folder:
        path = make_file(folder, "vfs.xml", body)
        return emulator.load_vfs(path)


def vfs_error(body):
    """Возвращает сообщение об ошибке при загрузке VFS из XML-текста."""
    with tempfile.TemporaryDirectory() as folder:
        path = make_file(folder, "vfs.xml", body)
        return exit_message(emulator.load_vfs, path)


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
        out = printed(emulator.run_line, "ls -l /tmp", None)
        self.assertEqual(out, "command: ls, arguments: ['-l', '/tmp']\n")

    def test_cd_stub(self):
        """Заглушка cd печатает своё имя и аргументы."""
        out = printed(emulator.run_line, "cd /home", None)
        self.assertEqual(out, "command: cd, arguments: ['/home']\n")

    def test_unknown_command(self):
        """Неизвестная команда даёт сообщение об ошибке."""
        out = printed(emulator.run_line, "foo bar", None)
        self.assertEqual(out, "foo: command not found\n")

    def test_exit(self):
        """Команда exit завершает работу эмулятора."""
        with self.assertRaises(SystemExit):
            emulator.run_line("exit", None)

    def test_empty_line_does_nothing(self):
        """Пустая строка и комментарий ничего не печатают."""
        self.assertEqual(printed(emulator.run_line, "", None), "")
        self.assertEqual(printed(emulator.run_line, "# note", None), "")


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


class VfsLoadTests(unittest.TestCase):
    """Загрузка VFS из XML-файла."""

    def test_minimal_vfs(self):
        """Минимальная VFS: только корень, без папок и файлов."""
        vfs = emulator.load_vfs(MINIMAL)
        self.assertEqual(vfs, {"name": "minimal", "root": {}})

    def test_several_files(self):
        """Несколько файлов в корне: текст и base64."""
        vfs = emulator.load_vfs("examples/vfs/files.xml")
        root = vfs["root"]
        self.assertEqual(sorted(root), ["data.bin", "empty.txt",
                                        "hello.txt", "readme.txt"])
        self.assertEqual(root["hello.txt"], b"hello world")
        self.assertEqual(root["data.bin"], bytes([0, 1, 2, 3]))
        self.assertEqual(root["empty.txt"], b"")

    def test_three_levels(self):
        """Вложенные папки: файл на глубине home/user/docs."""
        root = emulator.load_vfs(SAMPLE)["root"]
        self.assertEqual(root["home"]["user"]["docs"]["todo.txt"],
                         b"write the report")
        self.assertEqual(root["home"]["user"]["data.bin"],
                         bytes([0, 1, 2, 3, 4]))

    def test_unicode_text_and_default_name(self):
        """Русский текст читается правильно, имя по умолчанию — vfs."""
        vfs = vfs_from_text('<vfs><file name="a.txt">привет</file></vfs>')
        self.assertEqual(vfs["name"], "vfs")
        self.assertEqual(vfs["root"]["a.txt"], "привет".encode("utf-8"))

    def test_base64_with_line_breaks(self):
        """Данные base64 можно переносить на несколько строк."""
        body = ('<vfs><file name="b" encoding="base64">'
                'AAEC\n  Aw==</file></vfs>')
        root = vfs_from_text(body)["root"]
        self.assertEqual(root["b"], bytes([0, 1, 2, 3]))

    def test_loading_does_not_write_to_disk(self):
        """Загрузка VFS ничего не создаёт и не меняет на диске."""
        with tempfile.TemporaryDirectory() as folder:
            path = make_file(folder, "vfs.xml", pathlib.Path(SAMPLE).read_text(
                encoding="utf-8"))
            before = (sorted(os.listdir(folder)), os.path.getmtime(path))
            emulator.load_vfs(path)
            after = (sorted(os.listdir(folder)), os.path.getmtime(path))
        self.assertEqual(before, after)

    def test_missing_file(self):
        """Нет файла VFS — сообщение об ошибке."""
        message = exit_message(emulator.load_vfs, "no/such.xml")
        self.assertIn("VFS error: cannot read 'no/such.xml'", message)

    def test_directory_instead_of_file(self):
        """Папка вместо файла — сообщение об ошибке."""
        with tempfile.TemporaryDirectory() as folder:
            message = exit_message(emulator.load_vfs, folder)
        self.assertIn("VFS error: cannot read", message)

    def test_not_xml(self):
        """Файл не является XML — сообщение об ошибке."""
        message = vfs_error("this is not xml")
        self.assertIn("VFS error: invalid XML", message)

    def test_unclosed_tag(self):
        """Незакрытый тег — ошибка XML с номером строки."""
        message = vfs_error('<vfs><dir name="a"></vfs>')
        self.assertIn("invalid XML", message)
        self.assertIn("line 1", message)

    def test_wrong_root(self):
        """Корень не <vfs> — ошибка формата."""
        message = vfs_error("<files/>")
        self.assertIn("invalid format", message)
        self.assertIn("root element must be <vfs>", message)

    def test_unknown_element(self):
        """Неизвестный элемент внутри VFS — ошибка формата."""
        message = vfs_error('<vfs><folder name="a"/></vfs>')
        self.assertIn("unknown element <folder>", message)

    def test_missing_name(self):
        """У папки или файла нет имени — ошибка формата."""
        self.assertIn("needs a name", vfs_error("<vfs><dir/></vfs>"))

    def test_bad_names(self):
        """Имя со слэшем, точка и две точки недопустимы."""
        for name in ("a/b", ".", ".."):
            message = vfs_error(f'<vfs><file name="{name}"/></vfs>')
            self.assertIn("needs a name", message, name)

    def test_duplicate_names(self):
        """Два элемента с одним именем в папке — ошибка формата."""
        body = '<vfs><file name="a"/><dir name="a"/></vfs>'
        self.assertIn("duplicate name 'a'", vfs_error(body))

    def test_invalid_base64(self):
        """Неверные данные base64 — ошибка формата."""
        body = '<vfs><file name="b" encoding="base64">%%%</file></vfs>'
        self.assertIn("invalid base64", vfs_error(body))

    def test_unknown_encoding(self):
        """Неизвестная кодировка файла — ошибка формата."""
        body = '<vfs><file name="b" encoding="hex">00</file></vfs>'
        self.assertIn("unknown encoding 'hex'", vfs_error(body))


class VfsCommandTests(unittest.TestCase):
    """Служебная команда vfs-info и описание дерева."""

    def test_count_nodes(self):
        """Считаются папки и файлы по всему дереву."""
        root = emulator.load_vfs(SAMPLE)["root"]
        self.assertEqual(emulator.count_nodes(root), (3, 4))

    def test_tree_lines(self):
        """Дерево: папки со знаком /, у файлов размер, отступы по уровням."""
        root = {"a": {"b.txt": b"12"}, "c": b""}
        self.assertEqual(emulator.tree_lines(root),
                         ["a/", "  b.txt (2 bytes)", "c (0 bytes)"])

    def test_vfs_info_with_vfs(self):
        """vfs-info показывает имя, число папок и файлов и дерево."""
        vfs = emulator.load_vfs(SAMPLE)
        out = printed(emulator.run_line, "vfs-info", vfs)
        self.assertIn("VFS: sample (folders: 3, files: 4)", out)
        self.assertIn("      docs/\n        todo.txt (16 bytes)\n", out)

    def test_vfs_info_without_vfs(self):
        """Без VFS команда vfs-info сообщает, что VFS не загружена."""
        out = printed(emulator.run_line, "vfs-info", None)
        self.assertIn("no VFS loaded", out)


class ScriptTests(unittest.TestCase):
    """Выполнение стартового скрипта."""

    def run_text(self, text, vfs=None):
        """Выполняет скрипт с текстом text и возвращает его вывод."""
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as folder:
            path = make_file(folder, "start.txt", text)
            with contextlib.redirect_stdout(out):
                with contextlib.suppress(SystemExit):
                    emulator.run_script(path, PROMPT, vfs)
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

    def test_script_works_with_vfs(self):
        """Команда vfs-info в скрипте использует загруженную VFS."""
        out = self.run_text("vfs-info\n", emulator.load_vfs(MINIMAL))
        self.assertIn("VFS: minimal (folders: 0, files: 0)", out)

    def test_missing_script(self):
        """Нет файла скрипта — сообщение об ошибке."""
        message = exit_message(emulator.run_script, "no/such.txt", PROMPT,
                               None)
        self.assertIn("Script error: cannot read 'no/such.txt'", message)


class ReplTests(unittest.TestCase):
    """Интерактивный цикл (ввод подменяется)."""

    def run_input(self, lines):
        """Запускает REPL на заданных строках и возвращает вывод."""
        with mock.patch("builtins.input", side_effect=lines):
            return printed(emulator.run_repl, PROMPT, None)

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
        """Конфиг важнее командной строки: берутся его VFS и скрипт."""
        result = start_program(["--vfs", MINIMAL, "--script",
                                "examples/start_a.txt", "--config",
                                "examples/config_full.yaml"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("used values : vfs=examples/vfs/sample.xml, "
                      "script=examples/start_b.txt", result.stdout)
        self.assertIn("VFS loaded: sample", result.stdout)
        self.assertIn("# Start script B", result.stdout)
        self.assertNotIn("# Start script A", result.stdout)

    def test_script_dialog_with_comments_and_error(self):
        """Скрипт показывает диалог, комментарии и ошибку команды."""
        result = start_program(["--script", "examples/start_a.txt"])
        self.assertIn("# Start script A", result.stdout)
        self.assertIn("command: ls, arguments: ['-l', '/tmp']", result.stdout)
        self.assertIn("foo: command not found", result.stdout)

    def test_vfs_is_loaded_and_shown(self):
        """С параметром --vfs VFS загружается и видна по vfs-info."""
        result = start_program(["--vfs", SAMPLE], "vfs-info\nexit\n")
        self.assertIn("VFS loaded: sample (folders: 3, files: 4)",
                      result.stdout)
        self.assertIn("notes.txt (5 bytes)", result.stdout)

    def test_all_commands_script_with_and_without_vfs(self):
        """Скрипт со всеми командами работает с VFS и без неё."""
        script = "examples/all_commands.txt"
        with_vfs = start_program(["--vfs", SAMPLE, "--script", script])
        without = start_program(["--script", script])
        self.assertEqual(with_vfs.returncode, 0)
        self.assertEqual(without.returncode, 0)
        self.assertIn("todo.txt (16 bytes)", with_vfs.stdout)
        self.assertIn("no VFS loaded", without.stdout)
        self.assertIn("foo: command not found", with_vfs.stdout)

    def test_vfs_errors_stop_program(self):
        """Ошибки VFS: сообщение и код завершения 1."""
        cases = (("examples/vfs/missing.xml", "cannot read"),
                 ("examples/vfs/bad_syntax.xml", "invalid XML"),
                 ("examples/vfs/bad_format.xml", "invalid format"))
        for path, text in cases:
            result = start_program(["--vfs", path])
            self.assertEqual(result.returncode, 1, path)
            self.assertIn("VFS error", result.stderr)
            self.assertIn(text, result.stderr)

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
