import contextlib
import getpass
import importlib
import socket
import sys

DEFAULT_USER = "user"
DEFAULT_HOST = "localhost"
HOST_SEPARATOR = "."
HOME_MARK = "~"
PROMPT_END = "$ "
BYTE_ORDER_MARK = "﻿"

EXIT_OK = 0
EXIT_MISUSE = 2
EXIT_CODE_MASK = 0xFF
MAX_EXIT_ARGS = 1


def get_username() -> str:
    """Возвращает имя текущего пользователя реальной ОС."""
    try:
        return getpass.getuser() or DEFAULT_USER
    except (ImportError, KeyError, OSError):
        return DEFAULT_USER


def get_hostname() -> str:
    """Возвращает короткое имя хоста реальной ОС (до первой точки)."""
    try:
        full_name = socket.gethostname()
    except OSError:
        return DEFAULT_HOST
    return full_name.split(HOST_SEPARATOR)[0] or DEFAULT_HOST


def build_prompt() -> str:
    """Формирует приглашение к вводу вида ``username@hostname:~$ ``.

    Текущий каталог пока всегда домашний (``~``): команда cd — заглушка.
    """
    user = get_username()
    host = get_hostname()
    return f"{user}@{host}:{HOME_MARK}{PROMPT_END}"


def parse_line(line: str) -> tuple[str, list[str]]:
    "Разбивает строку на команду и аргументы по пробельным символам."
    parts = line.lstrip(BYTE_ORDER_MARK).split()
    if not parts:
        return "", []
    return parts[0], parts[1:]


def describe_call(name: str, args: list[str]) -> str:
    """Формирует вывод команды-заглушки: её имя и аргументы."""
    return f"command: {name}, arguments: {args}"


def cmd_ls(args: list[str]) -> None:
    """Заглушка команды ls: выводит своё имя и аргументы."""
    print(describe_call("ls", args))


def cmd_cd(args: list[str]) -> None:
    """Заглушка команды cd: выводит своё имя и аргументы."""
    print(describe_call("cd", args))


def cmd_exit(args: list[str]) -> None:
    """Завершает работу эмулятора."""
    if not args:
        raise SystemExit(EXIT_OK)
    try:
        code = int(args[0])
    except ValueError:
        print(f"exit: {args[0]}: numeric argument required", file=sys.stderr)
        raise SystemExit(EXIT_MISUSE) from None
    if len(args) > MAX_EXIT_ARGS:
        print("exit: too many arguments", file=sys.stderr)
        return
    raise SystemExit(code & EXIT_CODE_MASK)


COMMANDS = {
    "ls": cmd_ls,
    "cd": cmd_cd,
    "exit": cmd_exit,
}


def execute(command: str, args: list[str]) -> None:
    """Выполняет команду или сообщает, что такой команды нет."""
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"{command}: command not found", file=sys.stderr)
        return
    handler(args)


def enable_line_editing() -> None:
    """Включает историю и редактирование ввода, если есть readline."""
    with contextlib.suppress(ImportError):
        importlib.import_module("readline")


def run_repl(prompt: str) -> None:
    """Запускает цикл «приглашение — чтение — разбор — выполнение»."""
    while True:
        try:
            line = input(prompt)
        except EOFError:
            print("exit")
            return
        except KeyboardInterrupt:
            print()
            continue
        command, args = parse_line(line)
        if command:
            execute(command, args)


def main() -> int:
    """Точка входа: запускает REPL и возвращает код завершения."""
    enable_line_editing()
    run_repl(build_prompt())
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
