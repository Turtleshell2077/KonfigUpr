"""Тесты эмулятора: парсер, команды, конфиг, скрипт, VFS и запуск."""

import contextlib
import copy
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
MINIMAL = "examples/vfs/minimal.xml"
SAMPLE = "examples/vfs/sample.xml"
STAGE5 = "examples/vfs/stage5.xml"
NO_VFS = "no VFS loaded (use --vfs or the config file)"
TODO = b"write the report\ncheck the code\nsend to teacher"


@contextlib.contextmanager
def fixed_user():
    """Подменяет имя пользователя (u) и компьютера (h): приглашение u@h."""
    with mock.patch("getpass.getuser", return_value="u"):
        with mock.patch("socket.gethostname", return_value="h"):
            yield


def small_vfs():
    """Небольшая VFS в памяти для проверки команд (текущая папка — корень)."""
    return {"name": "t", "cwd": [], "root": {
        "home": {"user": {"a.txt": b"one\ntwo\nthree\n",
                          "bin": b"\xff\xfe", "docs": {}}},
        "readme.txt": b"hello"}}


def make_file(folder, name, text):
    """Создаёт в папке файл с текстом и возвращает путь к нему."""
    path = pathlib.Path(folder) / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def printed(func, *args):
    """Вызывает func(*args) и возвращает всё, что она напечатала."""
    out = io.StringIO()
    with fixed_user(), contextlib.redirect_stdout(out):
        func(*args)
    return out.getvalue()


def run(line, vfs=None):
    """Выполняет одну команду эмулятора и возвращает её вывод."""
    return printed(emulator.run_line, line, vfs)


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

    def test_prompt(self):
        """Приглашение: ~ без VFS, с VFS — текущая папка."""
        vfs = small_vfs()
        with fixed_user():
            self.assertEqual(emulator.get_prompt(), "u@h:~$ ")
            self.assertEqual(emulator.get_prompt(vfs), "u@h:/$ ")
            vfs["cwd"] = ["home", "user"]
            self.assertEqual(emulator.get_prompt(vfs), "u@h:/home/user$ ")

    def test_command_and_arguments(self):
        """Строка делится по пробелам на команду и аргументы."""
        result = emulator.parse_line("  ls   -l  /tmp ")
        self.assertEqual(result, ("ls", ["-l", "/tmp"]))

    def test_empty_and_comment_lines(self):
        """Пустая строка и строка-комментарий не содержат команды."""
        self.assertEqual(emulator.parse_line("   "), ("", []))
        self.assertEqual(emulator.parse_line("# comment"), ("", []))

    def test_comment_after_command(self):
        """Комментарий после команды отбрасывается."""
        result = emulator.parse_line("ls -l # list files")
        self.assertEqual(result, ("ls", ["-l"]))


class PathTests(unittest.TestCase):
    """Разбор путей и поиск в дереве VFS."""

    def test_absolute_and_relative_paths(self):
        """Абсолютный путь идёт от корня, относительный от текущей папки."""
        vfs = small_vfs()
        vfs["cwd"] = ["home"]
        self.assertEqual(emulator.resolve_path(vfs, "/home/user"),
                         ["home", "user"])
        self.assertEqual(emulator.resolve_path(vfs, "user"),
                         ["home", "user"])

    def test_dot_and_dotdot(self):
        """Точка и две точки; родитель корня — это корень."""
        vfs = small_vfs()
        vfs["cwd"] = ["home", "user"]
        self.assertEqual(emulator.resolve_path(vfs, "."), ["home", "user"])
        self.assertEqual(emulator.resolve_path(vfs, ".."), ["home"])
        self.assertEqual(emulator.resolve_path(vfs, "../.."), [])
        self.assertEqual(emulator.resolve_path(vfs, "/../.."), [])
        self.assertEqual(emulator.resolve_path(vfs, "./docs/"),
                         ["home", "user", "docs"])

    def test_find_node(self):
        """Находятся папка (словарь), файл (байты) и отсутствие (None)."""
        vfs = small_vfs()
        self.assertIsInstance(emulator.find_node(vfs, ["home"]), dict)
        self.assertEqual(emulator.find_node(vfs, ["readme.txt"]), b"hello")
        self.assertIsNone(emulator.find_node(vfs, ["nope"]))
        self.assertIsNone(emulator.find_node(vfs, ["readme.txt", "x"]))
        self.assertIs(emulator.find_node(vfs, []), vfs["root"])


class LsTests(unittest.TestCase):
    """Команда ls."""

    def test_listing(self):
        """Папка (текущая, по пути, ., ..) и файл: что печатается."""
        vfs = small_vfs()
        user = "a.txt\nbin\ndocs/\n"
        self.assertEqual(run("ls", vfs), "home/\nreadme.txt\n")
        self.assertEqual(run("ls /home/user", vfs), user)
        self.assertEqual(run("ls readme.txt", vfs), "readme.txt\n")
        vfs["cwd"] = ["home"]
        self.assertEqual(run("ls user", vfs), user)
        self.assertEqual(run("ls ..", vfs), "home/\nreadme.txt\n")
        self.assertEqual(run("ls .", vfs), "user/\n")

    def test_long_format(self):
        """Параметр -l добавляет тип и размер."""
        out = run("ls -l /home/user", small_vfs())
        self.assertEqual(out, "-       14 a.txt\n"
                              "-        2 bin\n"
                              "d        - docs/\n")

    def test_several_paths(self):
        """Несколько путей: перед каждым выводится его имя."""
        out = run("ls /home /home/user/docs readme.txt", small_vfs())
        self.assertEqual(out, "/home:\nuser/\n\n/home/user/docs:\n\n"
                              "readme.txt:\nreadme.txt\n")

    def test_all_option(self):
        """-a показывает скрытые имена (с точки), . и ..; без -a их нет."""
        vfs = small_vfs()
        vfs["root"]["home"]["user"][".profile"] = b"x"
        self.assertEqual(run("ls /home/user", vfs), "a.txt\nbin\ndocs/\n")
        self.assertEqual(run("ls -a /home/user", vfs),
                         "./\n../\n.profile\na.txt\nbin\ndocs/\n")
        self.assertEqual(run("ls /home/user/.profile", vfs),
                         "/home/user/.profile\n")

    def test_human_option(self):
        """-h с -l печатает размеры как 1.5K и 2.0M; параметры объединяются."""
        vfs = small_vfs()
        user = vfs["root"]["home"]["user"]
        user["big.txt"] = b"a" * 1536
        user["huge.bin"] = b"a" * 2097152
        user[".profile"] = b"x"
        out = run("ls -lh /home/user", vfs)
        self.assertIn("      14 a.txt\n", out)
        self.assertIn("     1.5K big.txt\n", out)
        self.assertIn("     2.0M huge.bin\n", out)
        self.assertNotIn(".profile", out)
        self.assertEqual(run("ls -hl /home/user", vfs), out)
        everything = run("ls -lah /home/user", vfs)
        self.assertIn("d        - ./\n", everything)
        self.assertIn("-        1 .profile\n", everything)
        self.assertEqual(run("ls -h /home/user", vfs),
                         run("ls /home/user", vfs))
        sizes = ((0, "0"), (1023, "1023"), (1024, "1.0K"), (1536, "1.5K"),
                 (1048576, "1.0M"), (1073741824, "1.0G"))
        for size, text in sizes:
            with self.subTest(size=size):
                self.assertEqual(emulator.human_size(size), text)

    def test_errors(self):
        """Несуществующий путь, неизвестный параметр или буква в группе."""
        vfs = small_vfs()
        self.assertEqual(
            run("ls /nope", vfs),
            "ls: cannot access '/nope': No such file or directory\n")
        self.assertEqual(run("ls -x", vfs), "ls: invalid option -- 'x'\n")
        self.assertEqual(run("ls -lx", vfs), "ls: invalid option -- 'x'\n")
        self.assertEqual(run("ls --all", vfs),
                         "ls: unrecognized option '--all'\n")
        self.assertEqual(run("ls -", vfs),
                         "ls: cannot access '-': No such file or directory\n")


class CdTests(unittest.TestCase):
    """Команда cd."""

    def test_paths(self):
        """Абсолютные и относительные пути, . и ..; ls работает после cd."""
        vfs = small_vfs()
        for line, expected in (("cd /home/user", ["home", "user"]),
                               ("cd docs", ["home", "user", "docs"]),
                               ("cd ..", ["home", "user"]),
                               ("cd ../..", []),
                               ("cd home", ["home"]),
                               ("cd .", ["home"])):
            with self.subTest(line=line):
                self.assertEqual(run(line, vfs), "")
                self.assertEqual(vfs["cwd"], expected)
        self.assertEqual(run("ls user", vfs), "a.txt\nbin\ndocs/\n")

    def test_without_arguments_goes_to_root(self):
        """cd без аргументов возвращает в корень."""
        vfs = small_vfs()
        vfs["cwd"] = ["home", "user"]
        run("cd", vfs)
        self.assertEqual(vfs["cwd"], [])

    def test_errors_keep_current_folder(self):
        """После ошибки текущая папка не меняется."""
        vfs = small_vfs()
        vfs["cwd"] = ["home"]
        self.assertEqual(run("cd /nope", vfs),
                         "cd: /nope: No such file or directory\n")
        self.assertEqual(run("cd /readme.txt", vfs),
                         "cd: /readme.txt: Not a directory\n")
        self.assertEqual(run("cd user docs", vfs),
                         "cd: too many arguments\n")
        self.assertEqual(vfs["cwd"], ["home"])


class TacRevWhoamiTests(unittest.TestCase):
    """Команды tac, rev и whoami."""

    def test_tac(self):
        """tac печатает строки файла в обратном порядке (файлов несколько)."""
        vfs = small_vfs()
        self.assertEqual(run("tac /home/user/a.txt", vfs),
                         "three\ntwo\none\n")
        self.assertEqual(run("tac readme.txt /home/user/a.txt", vfs),
                         "hello\nthree\ntwo\none\n")

    def test_rev(self):
        """rev печатает каждую строку наоборот, в том числе русский текст."""
        vfs = small_vfs()
        vfs["root"]["ru.txt"] = "привет".encode("utf-8")
        self.assertEqual(run("rev readme.txt", vfs), "olleh\n")
        self.assertEqual(run("rev /home/user/a.txt", vfs), "eno\nowt\neerht\n")
        self.assertEqual(run("rev ru.txt", vfs), "тевирп\n")

    def test_errors_of_tac_and_rev(self):
        """Ошибки: нет операнда, нет файла, папка, не текст."""
        vfs = small_vfs()
        for command in ("tac", "rev"):
            with self.subTest(command=command):
                self.assertEqual(run(command, vfs),
                                 f"{command}: missing file operand\n")
                self.assertEqual(
                    run(f"{command} nope", vfs),
                    f"{command}: nope: No such file or directory\n")
                self.assertEqual(run(f"{command} home", vfs),
                                 f"{command}: home: Is a directory\n")
                self.assertEqual(
                    run(f"{command} home/user/bin", vfs),
                    f"{command}: home/user/bin: not a text file\n")
        self.assertEqual(run("rev nope readme.txt", vfs),
                         "rev: nope: No such file or directory\nolleh\n")

    def test_whoami(self):
        """whoami печатает имя пользователя; лишний аргумент — ошибка."""
        self.assertEqual(run("whoami"), "u\n")
        self.assertEqual(run("whoami", small_vfs()), "u\n")
        self.assertEqual(run("whoami now"), "whoami: extra operand 'now'\n")


class RmdirRmTests(unittest.TestCase):
    """Команды rmdir и rm: меняют только VFS в памяти."""

    def test_rmdir(self):
        """rmdir удаляет пустые папки (сразу несколько), сообщает ошибки."""
        vfs = small_vfs()
        vfs["root"]["e1"] = {}
        self.assertEqual(run("rmdir e1 home/user/docs", vfs), "")
        self.assertEqual(sorted(vfs["root"]), ["home", "readme.txt"])
        self.assertEqual(sorted(vfs["root"]["home"]["user"]),
                         ["a.txt", "bin"])
        head = "rmdir: failed to remove"
        for line, text in (
                ("rmdir home", f"{head} 'home': Directory not empty"),
                ("rmdir readme.txt", f"{head} 'readme.txt': Not a directory"),
                ("rmdir nope", f"{head} 'nope': No such file or directory"),
                ("rmdir", "rmdir: missing operand"),
                ("rmdir -p home", "rmdir: invalid option -- 'p'")):
            with self.subTest(line=line):
                self.assertEqual(run(line, vfs), text + "\n")

    def test_rm(self):
        """rm удаляет файлы, с -r и -R папки; ошибки не мешают остальным."""
        vfs = small_vfs()
        out = run("rm readme.txt nope home/user/a.txt", vfs)
        self.assertEqual(
            out, "rm: cannot remove 'nope': No such file or directory\n")
        self.assertNotIn("readme.txt", vfs["root"])
        self.assertNotIn("a.txt", vfs["root"]["home"]["user"])
        self.assertEqual(run("rm -R home/user/docs", vfs), "")
        self.assertEqual(run("rm -r home", vfs), "")
        self.assertEqual(vfs["root"], {})
        for line, text in (
                ("rm home", "rm: cannot remove 'home': Is a directory"),
                ("rm", "rm: missing operand"),
                ("rm -x home", "rm: invalid option -- 'x'")):
            with self.subTest(line=line):
                self.assertEqual(run(line, small_vfs()), text + "\n")

    def test_current_folder_and_parents_are_busy(self):
        """Текущую папку и её родителей удалить нельзя, VFS остаётся целой."""
        vfs = small_vfs()
        vfs["cwd"] = ["home", "user", "docs"]
        before = copy.deepcopy(vfs["root"])
        for line in ("rmdir .", "rmdir /home/user/docs", "rm -r ..",
                     "rm -r ../..", "rm -r /home", "rm -r /"):
            with self.subTest(line=line):
                self.assertIn("Device or resource busy", run(line, vfs))
        self.assertEqual(vfs["root"], before)
        self.assertIsInstance(emulator.find_node(vfs, vfs["cwd"]), dict)

    def test_changes_only_memory(self):
        """Удаление не меняет XML-файл на диске: новая загрузка даёт всё."""
        with tempfile.TemporaryDirectory() as folder:
            body = pathlib.Path(STAGE5).read_text(encoding="utf-8")
            path = pathlib.Path(make_file(folder, "vfs.xml", body))
            before = (path.read_bytes(), sorted(os.listdir(folder)))
            vfs = emulator.load_vfs(str(path))
            for line in ("rm -r nested", "rm old.txt", "rmdir empty1"):
                run(line, vfs)
            after = (path.read_bytes(), sorted(os.listdir(folder)))
            fresh = emulator.load_vfs(str(path))
        self.assertEqual(before, after)
        self.assertEqual(emulator.count_nodes(fresh["root"]), (5, 5))
        self.assertEqual(emulator.count_nodes(vfs["root"]), (2, 3))


class VfsUsageTests(unittest.TestCase):
    """Работа команд без VFS и неизменность VFS."""

    def test_commands_without_vfs(self):
        """Без VFS команды сообщают, что VFS не загружена."""
        for line, name in (("ls", "ls"), ("cd /", "cd"), ("tac x", "tac"),
                           ("rev x", "rev"), ("rm x", "rm"),
                           ("rmdir x", "rmdir"), ("vfs-info", "vfs-info")):
            with self.subTest(line=line):
                self.assertEqual(run(line), f"{name}: {NO_VFS}\n")

    def test_commands_do_not_change_vfs(self):
        """Команды только читают VFS: данные остаются прежними."""
        vfs = small_vfs()
        before = copy.deepcopy(vfs["root"])
        for line in ("ls -l /home", "tac readme.txt", "rev /home/user/a.txt",
                     "cd /home/user", "vfs-info", "ls docs"):
            run(line, vfs)
        self.assertEqual(vfs["root"], before)


class OtherCommandTests(unittest.TestCase):
    """Команда exit, неизвестная и пустая команды."""

    def test_unknown_and_empty_commands(self):
        """Неизвестная команда — ошибка; пустая строка и комментарий — нет."""
        self.assertEqual(run("foo bar"), "foo: command not found\n")
        self.assertEqual(run(""), "")
        self.assertEqual(run("# note"), "")

    def test_exit(self):
        """Команда exit завершает работу эмулятора."""
        with self.assertRaises(SystemExit):
            emulator.run_line("exit", None)


class ConfigTests(unittest.TestCase):
    """Чтение YAML-конфига и приоритет значений."""

    def test_read_config(self):
        """Читаются пути к VFS и скрипту; из комментариев — пустой конфиг."""
        with tempfile.TemporaryDirectory() as folder:
            both = make_file(folder, "c.yaml", "vfs: a.xml\nscript: s.txt\n")
            empty = make_file(folder, "e.yaml", "# nothing\n")
            self.assertEqual(emulator.read_config(both),
                             {"vfs": "a.xml", "script": "s.txt"})
            self.assertEqual(emulator.read_config(empty), {})

    def test_config_errors(self):
        """Ошибки: нет файла, неверный YAML, не пары, значение не строка."""
        message = exit_message(emulator.read_config, "no/such.yaml")
        self.assertIn("Config error: cannot read 'no/such.yaml'", message)
        cases = (("vfs: [a.xml\nscript: s\n", "Config error: cannot read"),
                 ("- a\n- b\n", "must contain 'key: value' pairs"),
                 ("vfs: 42\n", "must be a string"))
        with tempfile.TemporaryDirectory() as folder:
            for body, text in cases:
                with self.subTest(body=body):
                    path = make_file(folder, "c.yaml", body)
                    message = exit_message(emulator.read_config, path)
                    self.assertIn(text, message)

    def test_merge_settings(self):
        """Файл важнее командной строки; недостающее берётся из неё."""
        args = emulator.parse_args(["--vfs", "cli.xml", "--script", "cli.txt"])
        both = {"vfs": "file.xml", "script": "file.txt"}
        self.assertEqual(emulator.merge_settings(args, both), both)
        self.assertEqual(emulator.merge_settings(args, {"vfs": "file.xml"}),
                         {"vfs": "file.xml", "script": "cli.txt"})
        self.assertEqual(emulator.merge_settings(args, {"vfs": None}),
                         {"vfs": "cli.xml", "script": "cli.txt"})
        nothing = emulator.merge_settings(emulator.parse_args([]), {})
        self.assertEqual(nothing, {"vfs": None, "script": None})

    def test_debug_output(self):
        """Отладочный вывод показывает параметры и итоговые значения."""
        args = emulator.parse_args(["--vfs", "a.xml", "--config", "c.yaml"])
        settings = {"vfs": "a.xml", "script": None}
        out = printed(emulator.print_debug, args, {}, settings)
        self.assertIn("vfs=a.xml, script=None, config=c.yaml", out)
        self.assertIn("used values : vfs=a.xml, script=None", out)


class VfsLoadTests(unittest.TestCase):
    """Загрузка VFS из XML-файла."""

    def test_example_files(self):
        """Минимальная VFS, VFS с файлами (текст и base64), три уровня."""
        minimal = emulator.load_vfs(MINIMAL)
        self.assertEqual(minimal, {"name": "minimal", "root": {}, "cwd": []})
        root = emulator.load_vfs("examples/vfs/files.xml")["root"]
        self.assertEqual(sorted(root), ["data.bin", "empty.txt",
                                        "hello.txt", "readme.txt"])
        self.assertEqual(root["hello.txt"], b"hello world")
        self.assertEqual(root["data.bin"], bytes([0, 1, 2, 3]))
        self.assertEqual(root["empty.txt"], b"")
        deep = emulator.load_vfs(SAMPLE)["root"]["home"]["user"]
        self.assertEqual(deep["docs"]["todo.txt"], TODO)
        self.assertEqual(deep["data.bin"],
                         bytes([0xFF, 0xFE, 0xFD, 0xFC, 0xFB]))

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

    def test_read_errors(self):
        """Нет файла и папка вместо файла — сообщение об ошибке чтения."""
        message = exit_message(emulator.load_vfs, "no/such.xml")
        self.assertIn("VFS error: cannot read 'no/such.xml'", message)
        with tempfile.TemporaryDirectory() as folder:
            message = exit_message(emulator.load_vfs, folder)
        self.assertIn("VFS error: cannot read", message)

    def test_xml_errors(self):
        """Не XML и незакрытый тег (с номером строки)."""
        self.assertIn("VFS error: invalid XML", vfs_error("this is not xml"))
        message = vfs_error('<vfs><dir name="a"></vfs>')
        self.assertIn("invalid XML", message)
        self.assertIn("line 1", message)

    def test_format_errors(self):
        """Неверная структура VFS: сообщение называет причину."""
        cases = (
            ("<files/>", "root element must be <vfs>"),
            ('<vfs><folder name="a"/></vfs>', "unknown element <folder>"),
            ("<vfs><dir/></vfs>", "needs a name"),
            ('<vfs><file name="a/b"/></vfs>', "needs a name"),
            ('<vfs><file name="."/></vfs>', "needs a name"),
            ('<vfs><file name=".."/></vfs>', "needs a name"),
            ('<vfs><file name="a"/><dir name="a"/></vfs>',
             "duplicate name 'a'"),
            ('<vfs><file name="b" encoding="base64">%%%</file></vfs>',
             "invalid base64"),
            ('<vfs><file name="b" encoding="hex">00</file></vfs>',
             "unknown encoding 'hex'"),
        )
        for body, text in cases:
            with self.subTest(body=body):
                message = vfs_error(body)
                self.assertIn("invalid format", message)
                self.assertIn(text, message)


class VfsInfoTests(unittest.TestCase):
    """Служебная команда vfs-info и описание дерева."""

    def test_count_and_tree(self):
        """Считаются папки и файлы; дерево с отступами и размерами."""
        root = emulator.load_vfs(SAMPLE)["root"]
        self.assertEqual(emulator.count_nodes(root), (3, 6))
        tree = {"a": {"b.txt": b"12"}, "c": b""}
        self.assertEqual(emulator.tree_lines(tree),
                         ["a/", "  b.txt (2 bytes)", "c (0 bytes)"])

    def test_vfs_info(self):
        """vfs-info показывает имя, число папок и файлов и дерево."""
        out = run("vfs-info", emulator.load_vfs(SAMPLE))
        self.assertIn("VFS: sample (folders: 3, files: 6)", out)
        self.assertIn("      docs/\n        todo.txt (47 bytes)\n", out)


class ScriptTests(unittest.TestCase):
    """Выполнение стартового скрипта."""

    def run_text(self, text, vfs=None):
        """Выполняет скрипт с текстом text и возвращает его вывод."""
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as folder:
            path = make_file(folder, "start.txt", text)
            with fixed_user(), contextlib.redirect_stdout(out):
                with contextlib.suppress(SystemExit):
                    emulator.run_script(path, vfs)
        return out.getvalue()

    def test_dialog(self):
        """Видны ввод и вывод; комментарии показываются, пустые пропущены."""
        out = self.run_text("# hello\nwhoami # why\n\n  \n")
        self.assertEqual(out, "u@h:~$ # hello\nu@h:~$ whoami # why\nu\n")

    def test_errors_do_not_stop_script(self):
        """После ошибочной команды скрипт продолжается."""
        out = self.run_text("foo\nwhoami\n")
        self.assertEqual(out, "u@h:~$ foo\nfoo: command not found\n"
                              "u@h:~$ whoami\nu\n")

    def test_exit_stops_script(self):
        """Команда exit прекращает выполнение скрипта."""
        out = self.run_text("exit\nwhoami\n")
        self.assertEqual(out, "u@h:~$ exit\n")

    def test_prompt_follows_cd(self):
        """В скрипте приглашение показывает текущую папку VFS."""
        out = self.run_text("cd /home\nls\n", small_vfs())
        self.assertEqual(out, "u@h:/$ cd /home\nu@h:/home$ ls\nuser/\n")

    def test_missing_script(self):
        """Нет файла скрипта — сообщение об ошибке."""
        message = exit_message(emulator.run_script, "no/such.txt", None)
        self.assertIn("Script error: cannot read 'no/such.txt'", message)


class ReplTests(unittest.TestCase):
    """Интерактивный цикл (ввод подменяется)."""

    def run_input(self, lines, vfs=None):
        """Запускает REPL на заданных строках, даёт (вывод, вызовы input)."""
        with mock.patch("builtins.input", side_effect=lines) as fake_input:
            out = printed(emulator.run_repl, vfs)
        return out, [call.args[0] for call in fake_input.call_args_list]

    def test_session_and_ctrl_c(self):
        """Команды работают, пустые строки пропускаются, Ctrl+C не мешает."""
        lines = ["whoami", "", "foo", KeyboardInterrupt(), "whoami",
                 EOFError()]
        out, _ = self.run_input(lines)
        self.assertEqual(out, "u\nfoo: command not found\n\nu\nexit\n")

    def test_prompt_follows_cd(self):
        """Приглашение для каждого ввода показывает текущую папку."""
        out, prompts = self.run_input(["cd /home", "ls", EOFError()],
                                      small_vfs())
        self.assertEqual(prompts, ["u@h:/$ ", "u@h:/home$ ", "u@h:/home$ "])
        self.assertEqual(out, "user/\nexit\n")


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
        self.assertIn("foo: command not found", result.stdout)
        self.assertIn(f"vfs-info: {NO_VFS}", result.stdout)

    def test_interactive_session_with_vfs(self):
        """Интерактивно: VFS загружена, cd меняет приглашение, команды ок."""
        text = "vfs-info\ncd /home/user/docs\nls\ntac todo.txt\nexit\n"
        result = start_program(["--vfs", SAMPLE], text)
        self.assertEqual(result.returncode, 0)
        self.assertIn("VFS loaded: sample (folders: 3, files: 6)",
                      result.stdout)
        self.assertIn("notes.txt (5 bytes)", result.stdout)
        self.assertIn(":/home/user/docs$ ", result.stdout)
        self.assertIn("send to teacher\ncheck the code\nwrite the report\n",
                      result.stdout)

    def test_output_survives_unencodable_characters(self):
        """Символ, которого нет в кодировке вывода, не роняет программу."""
        body = f'<vfs><file name="s.txt">hi {chr(0x1F600)} ok</file></vfs>'
        with tempfile.TemporaryDirectory() as folder:
            path = make_file(folder, "vfs.xml", body)
            result = subprocess.run(
                [sys.executable, str(PROGRAM), "--vfs", path],
                input="tac s.txt\nexit\n", capture_output=True, text=True,
                encoding="cp1251", cwd=ROOT, timeout=60, check=False,
                env=dict(os.environ, PYTHONIOENCODING="cp1251"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn("hi ? ok", result.stdout)

    def test_stage4_script_with_vfs(self):
        """Скрипт этапа 4 выполняется на VFS: все команды и все ошибки."""
        result = start_program(["--vfs", SAMPLE, "--script",
                                "examples/stage4.txt"])
        out = result.stdout
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        for text in ("whoami: extra operand 'extra'",
                     "d        - docs/",
                     "/home:\nuser/\n",
                     "ls: invalid option -- 'x'",
                     "cd: /readme.txt: Not a directory",
                     "cd: too many arguments",
                     "send to teacher\ncheck the code\nwrite the report\n",
                     "rehcaet ot dnes\n",
                     "rev: data.bin: not a text file",
                     "tac: docs: Is a directory"):
            self.assertIn(text, out)

    def test_stage4_script_without_vfs(self):
        """Без VFS скрипт этапа 4 не падает: команды сообщают об отсутствии."""
        result = start_program(["--script", "examples/stage4.txt"])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        self.assertIn(f"ls: {NO_VFS}", result.stdout)
        self.assertIn(f"tac: {NO_VFS}", result.stdout)

    def test_stage5_script(self):
        """Скрипт этапа 5: удаления и ошибки; второй запуск даёт то же."""
        args = ["--vfs", STAGE5, "--script", "examples/stage5.txt"]
        first = start_program(args)
        second = start_program(args)
        self.assertEqual(first.returncode, 0)
        self.assertEqual(first.stderr, "")
        self.assertEqual(first.stdout, second.stdout)
        for text in ("rmdir: failed to remove 'docs': Directory not empty",
                     "rmdir: failed to remove 'readme.txt': Not a directory",
                     "rm: cannot remove 'docs': Is a directory",
                     "rm: cannot remove 'nope.txt': No such file",
                     "rm: invalid option -- 'x'",
                     "rm: cannot remove '/': Device or resource busy",
                     "VFS: stage5 (folders: 5, files: 5)",
                     "VFS: stage5 (folders: 0, files: 1)"):
            self.assertIn(text, first.stdout)
        without = start_program(["--script", "examples/stage5.txt"])
        self.assertEqual(without.returncode, 0)
        self.assertIn(f"rm: {NO_VFS}", without.stdout)

    def test_all_commands_script_with_and_without_vfs(self):
        """Краткий скрипт со всеми командами работает с любой VFS и без."""
        script = "examples/all_commands.txt"
        for vfs in (MINIMAL, "examples/vfs/files.xml", SAMPLE, None):
            with self.subTest(vfs=vfs):
                args = ["--script", script] + (["--vfs", vfs] if vfs else [])
                result = start_program(args)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stderr, "")
                self.assertIn("foo: command not found", result.stdout)

    def test_startup_errors(self):
        """Ошибки запуска: сообщение и код завершения (1 или 2)."""
        cases = ((["--vfs", "examples/vfs/missing.xml"], 1, "VFS error"),
                 (["--vfs", "examples/vfs/bad_syntax.xml"], 1, "invalid XML"),
                 (["--vfs", "examples/vfs/bad_format.xml"], 1,
                  "invalid format"),
                 (["--config", "examples/config_bad_syntax.yaml"], 1,
                  "Config error"),
                 (["--script", "missing.txt"], 1, "Script error"),
                 (["--unknown"], 2, "usage:"))
        for args, code, text in cases:
            with self.subTest(args=args):
                result = start_program(args)
                self.assertEqual(result.returncode, code)
                self.assertIn(text, result.stderr)


if __name__ == "__main__":
    unittest.main()
