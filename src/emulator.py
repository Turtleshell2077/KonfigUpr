"""Эмулятор оболочки (вариант 14): REPL, параметры, скрипт и VFS."""

import argparse
import base64
import binascii
import getpass
import socket
import sys
from xml.etree import ElementTree

try:
    import yaml
except ImportError:
    yaml = None

BANNER = "=== Virtual machine: shell emulator ==="
SETTINGS = ("vfs", "script")


def get_prompt():
    """Приглашение к вводу: имя пользователя и компьютера из реальной ОС."""
    return f"{getpass.getuser()}@{socket.gethostname()}:~$ "


def parse_args(argv=None):
    """Разбирает параметры командной строки."""
    parser = argparse.ArgumentParser(
        description="Эмулятор командной оболочки")
    parser.add_argument("--vfs", help="путь к XML-файлу с VFS")
    parser.add_argument("--script", help="путь к стартовому скрипту")
    parser.add_argument("--config", help="путь к конфигурационному файлу YAML")
    return parser.parse_args(argv)


def read_config(path):
    """Читает YAML-конфиг; при ошибке сообщает о ней и завершает работу."""
    if yaml is None:
        sys.exit("Config error: PyYAML is not installed (pip install pyyaml)")
    try:
        with open(path, encoding="utf-8-sig") as file:
            data = yaml.safe_load(file) or {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        sys.exit(f"Config error: cannot read '{path}': {error}")
    if not isinstance(data, dict):
        sys.exit(f"Config error: '{path}' must contain 'key: value' pairs")
    for key in SETTINGS:
        if data.get(key) is not None and not isinstance(data[key], str):
            sys.exit(f"Config error: '{key}' in '{path}' must be a string")
    return data


def merge_settings(args, file_data):
    """Объединяет настройки: значения из файла важнее командной строки."""
    settings = {"vfs": args.vfs, "script": args.script}
    for key in SETTINGS:
        if file_data.get(key) is not None:
            settings[key] = file_data[key]
    return settings


def print_debug(args, file_data, settings):
    """Отладочный вывод всех заданных параметров."""
    print(f"[debug] command line: vfs={args.vfs}, script={args.script}, "
          f"config={args.config}")
    print(f"[debug] config file : {file_data}")
    print(f"[debug] used values : vfs={settings['vfs']}, "
          f"script={settings['script']}")


def fail(path, message):
    """Сообщает о неверном формате файла VFS и завершает работу."""
    sys.exit(f"VFS error: invalid format in '{path}': {message}")


def read_xml_root(path):
    """Читает XML-файл VFS и возвращает его корневой элемент."""
    try:
        return ElementTree.parse(path).getroot()
    except OSError as error:
        sys.exit(f"VFS error: cannot read '{path}': {error}")
    except ElementTree.ParseError as error:
        sys.exit(f"VFS error: invalid XML in '{path}': {error}")


def check_name(name, tag, path):
    """Проверяет имя папки или файла в XML-описании VFS."""
    if not name or "/" in name or name in (".", ".."):
        fail(path, f"<{tag}> needs a name without '/' (not '.' or '..')")


def read_file(item, path):
    """Возвращает содержимое файла VFS в виде байтов."""
    text = item.text or ""
    encoding = item.get("encoding", "text")
    if encoding == "base64":
        try:
            return base64.b64decode("".join(text.split()), validate=True)
        except binascii.Error:
            fail(path, f"file '{item.get('name')}' has invalid base64 data")
    elif encoding != "text":
        fail(path, f"file '{item.get('name')}': unknown encoding "
                   f"'{encoding}'")
    return text.encode("utf-8")


def read_dir(element, path):
    """Читает содержимое папки: словарь «имя -> папка (словарь) или байты»."""
    children = {}
    for item in element:
        name = item.get("name")
        if item.tag not in ("dir", "file"):
            fail(path, f"unknown element <{item.tag}>")
        check_name(name, item.tag, path)
        if name in children:
            fail(path, f"duplicate name '{name}'")
        if item.tag == "dir":
            children[name] = read_dir(item, path)
        else:
            children[name] = read_file(item, path)
    return children


def load_vfs(path):
    """Загружает VFS из XML-файла в память; при ошибке завершает работу."""
    root = read_xml_root(path)
    if root.tag != "vfs":
        fail(path, "the root element must be <vfs>")
    return {"name": root.get("name", "vfs"), "root": read_dir(root, path)}


def count_nodes(directory):
    """Считает папки и файлы во всём дереве: (папки, файлы)."""
    folders = files = 0
    for node in directory.values():
        if isinstance(node, dict):
            inner_folders, inner_files = count_nodes(node)
            folders += 1 + inner_folders
            files += inner_files
        else:
            files += 1
    return folders, files


def tree_lines(directory, indent=""):
    """Строки дерева VFS: у папок знак /, у файлов размер в байтах."""
    lines = []
    for name in sorted(directory):
        node = directory[name]
        if isinstance(node, dict):
            lines.append(f"{indent}{name}/")
            lines.extend(tree_lines(node, indent + "  "))
        else:
            lines.append(f"{indent}{name} ({len(node)} bytes)")
    return lines


def vfs_summary(vfs):
    """Краткое описание VFS: имя, число папок и файлов."""
    folders, files = count_nodes(vfs["root"])
    return f"{vfs['name']} (folders: {folders}, files: {files})"


def parse_line(line):
    """Делит строку на команду и аргументы; всё после # — комментарий."""
    words = line.split("#")[0].split()
    if not words:
        return "", []
    return words[0], words[1:]


def print_stub(name, args):
    """Печатает имя команды-заглушки и её аргументы."""
    print(f"command: {name}, arguments: {args}")


def cmd_ls(args, _vfs):
    """Заглушка команды ls."""
    print_stub("ls", args)


def cmd_cd(args, _vfs):
    """Заглушка команды cd."""
    print_stub("cd", args)


def cmd_exit(_args, _vfs):
    """Завершает работу эмулятора."""
    sys.exit()


def cmd_vfs_info(_args, vfs):
    """Служебная команда: показывает загруженную VFS и её дерево."""
    if vfs is None:
        print("vfs-info: no VFS loaded (use --vfs or the config file)")
        return
    print("VFS:", vfs_summary(vfs))
    print("/")
    for line in tree_lines(vfs["root"], "  "):
        print(line)


COMMANDS = {"ls": cmd_ls, "cd": cmd_cd, "exit": cmd_exit,
            "vfs-info": cmd_vfs_info}


def run_line(line, vfs):
    """Разбирает строку и выполняет команду, если она есть."""
    command, args = parse_line(line)
    if command in COMMANDS:
        COMMANDS[command](args, vfs)
    elif command:
        print(f"{command}: command not found")


def run_script(path, prompt, vfs):
    """Выполняет команды из файла, показывая ввод и вывод как диалог."""
    try:
        with open(path, encoding="utf-8-sig") as file:
            lines = file.read().splitlines()
    except (OSError, UnicodeDecodeError) as error:
        sys.exit(f"Script error: cannot read '{path}': {error}")
    for line in lines:
        if line.strip():
            print(prompt + line.rstrip())
            run_line(line, vfs)


def run_repl(prompt, vfs):
    """Интерактивный цикл: приглашение, ввод, выполнение команды."""
    while True:
        try:
            line = input(prompt)
        except EOFError:
            print("exit")
            return
        except KeyboardInterrupt:
            print()
            continue
        run_line(line, vfs)


def main():
    """Точка входа: параметры, VFS, скрипт, затем интерактивный режим."""
    args = parse_args()
    print(BANNER)
    file_data = read_config(args.config) if args.config else {}
    settings = merge_settings(args, file_data)
    print_debug(args, file_data, settings)
    vfs = load_vfs(settings["vfs"]) if settings["vfs"] else None
    if vfs:
        print("VFS loaded:", vfs_summary(vfs))
    prompt = get_prompt()
    if settings["script"]:
        run_script(settings["script"], prompt, vfs)
    run_repl(prompt, vfs)


if __name__ == "__main__":
    main()
