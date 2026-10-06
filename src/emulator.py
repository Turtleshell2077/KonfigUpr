"""Эмулятор оболочки (вариант 14): REPL, параметры, стартовый скрипт."""

import argparse
import getpass
import socket
import sys

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
    parser.add_argument("--vfs", help="путь к физическому расположению VFS")
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


def parse_line(line):
    """Делит строку на команду и аргументы; всё после # — комментарий."""
    words = line.split("#")[0].split()
    if not words:
        return "", []
    return words[0], words[1:]


def print_stub(name, args):
    """Печатает имя команды-заглушки и её аргументы."""
    print(f"command: {name}, arguments: {args}")


def cmd_ls(args):
    """Заглушка команды ls."""
    print_stub("ls", args)


def cmd_cd(args):
    """Заглушка команды cd."""
    print_stub("cd", args)


def cmd_exit(_args):
    """Завершает работу эмулятора."""
    sys.exit()


COMMANDS = {"ls": cmd_ls, "cd": cmd_cd, "exit": cmd_exit}


def run_line(line):
    """Разбирает строку и выполняет команду, если она есть."""
    command, args = parse_line(line)
    if command in COMMANDS:
        COMMANDS[command](args)
    elif command:
        print(f"{command}: command not found")


def run_script(path, prompt):
    """Выполняет команды из файла, показывая ввод и вывод как диалог."""
    try:
        with open(path, encoding="utf-8-sig") as file:
            lines = file.read().splitlines()
    except (OSError, UnicodeDecodeError) as error:
        sys.exit(f"Script error: cannot read '{path}': {error}")
    for line in lines:
        if line.strip():
            print(prompt + line.rstrip())
            run_line(line)


def run_repl(prompt):
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
        run_line(line)


def main():
    """Точка входа: параметры, отладочный вывод, скрипт, затем REPL."""
    args = parse_args()
    print(BANNER)
    file_data = read_config(args.config) if args.config else {}
    settings = merge_settings(args, file_data)
    print_debug(args, file_data, settings)
    prompt = get_prompt()
    if settings["script"]:
        run_script(settings["script"], prompt)
    run_repl(prompt)


if __name__ == "__main__":
    main()
