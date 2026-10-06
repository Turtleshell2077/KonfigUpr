# Эмулятор командной оболочки (вариант 14)

Практическая работа № 1 по дисциплине «Конфигурационное управление» (РТУ МИРЭА, ИКБО-10-25).
Готовы этап 1 (REPL) и этап 2 (конфигурация). Дальше: этап 3 — VFS, этапы 4–5 — команды.

## 1. Общее описание

Консольная программа на Python, которая имитирует работу в командной строке UNIX-подобной ОС. Это виртуальная
машина: команды выполняются внутри программы, настоящие программы ОС не запускаются. Сверху при запуске
печатается подпись `=== Virtual machine: shell emulator ===`.

Что умеет программа сейчас:

- Приглашение к вводу строится из данных ОС: `username@hostname:~$`.
- Команды `ls` и `cd` — заглушки, они печатают своё имя и аргументы. Команда `exit` завершает работу.
  Неизвестная команда даёт сообщение `command not found`.
- Параметры запуска `--vfs`, `--script`, `--config` и конфигурационный файл YAML. Значения из файла важнее,
  чем значения из командной строки.
- Стартовый скрипт: команды из файла выполняются по порядку, на экране видны и ввод, и вывод (как диалог).
  Поддерживаются комментарии `#`.
- При запуске печатаются все заданные параметры (отладочный вывод). Об ошибках (нет конфига, неверный YAML,
  нет скрипта) программа сообщает и завершается.

VFS пока не загружается (это этап 3): путь `--vfs` только запоминается и показывается в отладочном выводе.

## 2. Описание функций и настроек

### Параметры командной строки

| Параметр | Что задаёт |
|---|---|
| `--vfs ПУТЬ` | Путь к физическому расположению VFS |
| `--script ПУТЬ` | Путь к стартовому скрипту |
| `--config ПУТЬ` | Путь к конфигурационному файлу YAML |
| `-h`, `--help` | Справка |

Все параметры необязательны. Относительные пути считаются от текущей папки.

### Конфигурационный файл (YAML)

В файле два необязательных ключа: путь к VFS и путь к стартовому скрипту.

```yaml
vfs: examples/vfs/sample.xml
script: examples/start_b.txt
```

**Приоритет:** если значение есть в файле, берётся оно, а не значение из командной строки. Если в файле
значения нет, берётся значение из командной строки. Значения должны быть строками. Пути Windows пишите без
кавычек или с прямыми слэшами (`D:/data/vfs.xml`).

### Стартовый скрипт

Текстовый файл, по одной команде в строке.

- Каждая строка показывается с приглашением, затем идёт вывод команды, как в диалоге с пользователем.
- Комментарий начинается с `#` (целая строка или конец строки). Комментарии показываются, но не выполняются.
- Пустые строки пропускаются. Ошибочная команда выдаёт сообщение, скрипт продолжается.
- Если скрипт закончился без `exit`, программа остаётся в интерактивном режиме.

### Ошибки

| Ситуация | Сообщение | Код завершения |
|---|---|---|
| Конфиг не найден, не читается или неверный YAML | `Config error: cannot read ...` | 1 |
| В конфиге не пары «ключ: значение» или значение не строка | `Config error: ...` | 1 |
| Скрипт не найден или не читается | `Script error: cannot read ...` | 1 |
| Неизвестный параметр командной строки | `usage: ...` и описание ошибки | 2 |

### Команды эмулятора

| Команда | Что делает |
|---|---|
| `ls [аргументы]` | Заглушка: печатает `command: ls, arguments: [...]` |
| `cd [аргументы]` | Заглушка: печатает `command: cd, arguments: [...]` |
| `exit` | Завершает работу эмулятора |

`Ctrl+D` (в Windows `Ctrl+Z`, затем `Enter`) завершает работу, `Ctrl+C` сбрасывает текущую строку.

### Функции (файл `src/emulator.py`)

| Функция | Что делает |
|---|---|
| `get_prompt()` | Приглашение `username@hostname:~$ ` из имени пользователя и компьютера |
| `parse_args(argv)` | Разбирает параметры командной строки |
| `read_config(path)` | Читает YAML-конфиг, проверяет его; при ошибке сообщает и завершает работу |
| `merge_settings(args, file_data)` | Объединяет настройки: значения из файла важнее командной строки |
| `print_debug(args, file_data, settings)` | Отладочный вывод всех параметров |
| `parse_line(line)` | Делит строку на команду и аргументы, отбрасывает комментарий |
| `print_stub(name, args)` | Печатает имя команды-заглушки и аргументы |
| `cmd_ls(args)`, `cmd_cd(args)` | Заглушки команд `ls` и `cd` |
| `cmd_exit(_args)` | Команда `exit` |
| `run_line(line)` | Разбирает строку и выполняет команду |
| `run_script(path, prompt)` | Выполняет скрипт, показывая ввод и вывод как диалог |
| `run_repl(prompt)` | Интерактивный цикл: приглашение, ввод, выполнение |
| `main()` | Точка входа: параметры, отладочный вывод, скрипт, затем интерактивный режим |

## 3. Сборка, запуск и тесты

Нужен Python 3.9 или новее и библиотека PyYAML для чтения YAML. Сборка не требуется.

```
pip install -r requirements.txt
```

Запуск на Windows (из корня проекта; параметры пишутся после имени):

```
.\run.bat
.\run.bat --script examples/start_a.txt
```

Запуск на Linux/macOS: `sh run.sh [параметры]`. Или напрямую: `python src/emulator.py [параметры]`.

Тесты (из корня проекта):

```
python -m unittest -v
```

Скрипты для проверки параметров запускают эмулятор несколько раз; в каждом есть вызовы со всеми параметрами
(`--vfs`, `--script`, `--config`, `--help`). В конце скрипты ждут нажатия клавиши.

| Скрипт (папка `scripts/`) | Что проверяет |
|---|---|
| `test_params.bat` | Каждый параметр отдельно и все вместе |
| `test_priority.bat` | Приоритет значений из конфига над командной строкой |
| `test_errors.bat` | Ошибки: нет конфига, неверный YAML, нет скрипта, неизвестный параметр |

```
.\scripts\test_params.bat
.\scripts\test_priority.bat
.\scripts\test_errors.bat
```

## 4. Примеры использования

Запуск без параметров (пользователь `alice`, компьютер `workstation`):

```
=== Virtual machine: shell emulator ===
[debug] command line: vfs=None, script=None, config=None
[debug] config file : {}
[debug] used values : vfs=None, script=None
alice@workstation:~$ ls -l /tmp
command: ls, arguments: ['-l', '/tmp']
alice@workstation:~$ foo
foo: command not found
alice@workstation:~$ exit
```

Стартовый скрипт с комментариями и ошибкой (`.\run.bat --script examples/start_a.txt`):

```
=== Virtual machine: shell emulator ===
[debug] command line: vfs=None, script=examples/start_a.txt, config=None
[debug] config file : {}
[debug] used values : vfs=None, script=examples/start_a.txt
alice@workstation:~$ # Start script A: dialog, comments and error handling
alice@workstation:~$ ls
command: ls, arguments: []
alice@workstation:~$ ls -l /tmp   # a comment after a command is ignored
command: ls, arguments: ['-l', '/tmp']
alice@workstation:~$ # an unknown command is reported, the script goes on
alice@workstation:~$ foo bar
foo: command not found
alice@workstation:~$ cd /home/user
command: cd, arguments: ['/home/user']
alice@workstation:~$ exit
```

Приоритет конфига. В командной строке указаны `minimal.xml` и `start_a.txt`, а в конфиге другие значения,
поэтому берутся значения из файла и выполняется `start_b.txt`:

```
.\run.bat --vfs examples/vfs/minimal.xml --script examples/start_a.txt --config examples/config_full.yaml
```

```
=== Virtual machine: shell emulator ===
[debug] command line: vfs=examples/vfs/minimal.xml, script=examples/start_a.txt, config=examples/config_full.yaml
[debug] config file : {'vfs': 'examples/vfs/sample.xml', 'script': 'examples/start_b.txt'}
[debug] used values : vfs=examples/vfs/sample.xml, script=examples/start_b.txt
alice@workstation:~$ # Start script B: an alternative script
alice@workstation:~$ cd /
command: cd, arguments: ['/']
alice@workstation:~$ ls -a
command: ls, arguments: ['-a']
alice@workstation:~$ exit
```

Ошибка в конфиге (`.\run.bat --config examples/config_bad_syntax.yaml`), код завершения 1:

```
=== Virtual machine: shell emulator ===
Config error: cannot read 'examples/config_bad_syntax.yaml': while parsing a flow sequence
  in "examples/config_bad_syntax.yaml", line 2, column 6
expected ',' or ']', but got ':'
  in "examples/config_bad_syntax.yaml", line 3, column 7
```

## Структура репозитория

```
src/emulator.py       программа
tests/                тесты (unittest)
scripts/              скрипты Windows для проверки параметров
examples/             примеры: стартовые скрипты, конфиги YAML, файлы VFS
requirements.txt      зависимости (PyYAML)
run.bat, run.sh       запуск (Windows / Linux, macOS)
```
