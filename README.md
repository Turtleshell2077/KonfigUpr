# Эмулятор командной оболочки (вариант 14)

Практическая работа № 1 по дисциплине «Конфигурационное управление» (РТУ МИРЭА, ИКБО-10-25).
Готовы этап 1 (REPL), этап 2 (конфигурация) и этап 3 (VFS). Дальше: этапы 4–5 — команды.

## 1. Общее описание

Консольная программа на Python, которая имитирует работу в командной строке UNIX-подобной ОС. Это виртуальная
машина: команды выполняются внутри программы, настоящие программы ОС не запускаются. Сверху при запуске
печатается подпись `=== Virtual machine: shell emulator ===`.

Что умеет программа сейчас:

- Приглашение к вводу строится из данных ОС: `username@hostname:~$`.
- Команды `ls` и `cd` — заглушки, они печатают своё имя и аргументы. Команда `exit` завершает работу.
  Неизвестная команда даёт сообщение `command not found`.
- Параметры запуска `--vfs`, `--script`, `--config` и конфигурационный файл YAML. Значения из файла важнее,
  чем значения из командной строки. При запуске печатаются все параметры (отладочный вывод).
- Стартовый скрипт: команды из файла выполняются по порядку, на экране видны и ввод, и вывод (как диалог).
  Поддерживаются комментарии `#`.
- Виртуальная файловая система (VFS) загружается из XML-файла и целиком хранится в памяти. Служебная команда
  `vfs-info` показывает загруженную VFS. Об ошибках загрузки (нет файла, неверный формат) программа сообщает.

Эмулятор читает только файлы, которые ему указали (конфиг, скрипт, XML-файл VFS), и ничего не записывает на диск.
Содержимое VFS не распаковывается и не изменяется: всё хранится в памяти.

## 2. Описание функций и настроек

### Параметры командной строки

| Параметр | Что задаёт |
|---|---|
| `--vfs ПУТЬ` | Путь к XML-файлу с VFS |
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

### VFS (XML-файл)

Корневой элемент `<vfs name="имя">` — это корневая папка. Внутри него и внутри папок можно писать:

- `<dir name="имя">` — папка (внутри другие `dir` и `file`);
- `<file name="имя">текст</file>` — файл; текст хранится в UTF-8;
- `<file name="имя" encoding="base64">...</file>` — файл с двоичными данными в base64.

```xml
<vfs name="sample">
  <dir name="home">
    <dir name="user">
      <file name="notes.txt">hello</file>
      <file name="data.bin" encoding="base64">AAECAwQ=</file>
    </dir>
  </dir>
  <file name="readme.txt">sample VFS</file>
</vfs>
```

Правила: у каждой папки и файла есть имя без `/` (не `.` и не `..`), имена в одной папке не повторяются, других
элементов быть не должно. Файл загружается целиком в память в виде вложенных словарей (папка — словарь, файл —
байты). Имя `<vfs>` по умолчанию `vfs`.

Примеры в `examples/vfs/`: `minimal.xml` (только корень), `files.xml` (несколько файлов в одной папке),
`sample.xml` (три уровня папок, текстовые и двоичный файлы), а также сломанные `bad_syntax.xml` (не XML) и
`bad_format.xml` (неверная структура).

### Стартовый скрипт

Текстовый файл, по одной команде в строке.

- Каждая строка показывается с приглашением, затем идёт вывод команды, как в диалоге с пользователем.
- Комментарий начинается с `#` (целая строка или конец строки). Комментарии показываются, но не выполняются.
- Пустые строки пропускаются. Ошибочная команда выдаёт сообщение, скрипт продолжается.
- Если скрипт закончился без `exit`, программа остаётся в интерактивном режиме.

Скрипт `examples/all_commands.txt` проверяет все команды этапов 1–3, включая `vfs-info`, комментарии и ошибку.

### Ошибки

| Ситуация | Сообщение | Код завершения |
|---|---|---|
| Конфиг не найден, не читается или неверный YAML | `Config error: cannot read ...` | 1 |
| В конфиге не пары «ключ: значение» или значение не строка | `Config error: ...` | 1 |
| Файл VFS не найден или не читается | `VFS error: cannot read ...` | 1 |
| Файл VFS не является XML | `VFS error: invalid XML in ...` | 1 |
| Неверный формат VFS (не тот элемент, нет имени, повтор, плохой base64) | `VFS error: invalid format in ...` | 1 |
| Скрипт не найден или не читается | `Script error: cannot read ...` | 1 |
| Неизвестный параметр командной строки | `usage: ...` и описание ошибки | 2 |

### Команды эмулятора

| Команда | Что делает |
|---|---|
| `ls [аргументы]` | Заглушка: печатает `command: ls, arguments: [...]` |
| `cd [аргументы]` | Заглушка: печатает `command: cd, arguments: [...]` |
| `exit` | Завершает работу эмулятора |
| `vfs-info` | Служебная команда: имя VFS, число папок и файлов, дерево с размерами. Без VFS сообщает, что её нет |

`Ctrl+D` (в Windows `Ctrl+Z`, затем `Enter`) завершает работу, `Ctrl+C` сбрасывает текущую строку.

### Функции (файл `src/emulator.py`)

| Функция | Что делает |
|---|---|
| `get_prompt()` | Приглашение `username@hostname:~$ ` из имени пользователя и компьютера |
| `parse_args(argv)` | Разбирает параметры командной строки |
| `read_config(path)` | Читает YAML-конфиг, проверяет его; при ошибке сообщает и завершает работу |
| `merge_settings(args, file_data)` | Объединяет настройки: значения из файла важнее командной строки |
| `print_debug(args, file_data, settings)` | Отладочный вывод всех параметров |
| `fail(path, message)` | Сообщает о неверном формате VFS и завершает работу |
| `read_xml_root(path)` | Читает XML-файл и возвращает корневой элемент; сообщает, если файла нет или это не XML |
| `check_name(name, tag, path)` | Проверяет имя папки или файла в описании VFS |
| `read_file(item, path)` | Содержимое файла VFS в байтах (текст UTF-8 или base64) |
| `read_dir(element, path)` | Читает содержимое папки (рекурсивно): словарь «имя → папка или байты» |
| `load_vfs(path)` | Загружает VFS из XML-файла в память: `{"name": ..., "root": ...}` |
| `count_nodes(directory)` | Считает папки и файлы во всём дереве |
| `tree_lines(directory, indent)` | Строки дерева VFS для команды `vfs-info` |
| `vfs_summary(vfs)` | Краткое описание: имя, число папок и файлов |
| `parse_line(line)` | Делит строку на команду и аргументы, отбрасывает комментарий |
| `print_stub(name, args)` | Печатает имя команды-заглушки и аргументы |
| `cmd_ls`, `cmd_cd`, `cmd_exit`, `cmd_vfs_info` | Команды `ls`, `cd`, `exit` и `vfs-info` |
| `run_line(line, vfs)` | Разбирает строку и выполняет команду |
| `run_script(path, prompt, vfs)` | Выполняет скрипт, показывая ввод и вывод как диалог |
| `run_repl(prompt, vfs)` | Интерактивный цикл: приглашение, ввод, выполнение |
| `main()` | Точка входа: параметры, VFS, скрипт, затем интерактивный режим |

## 3. Сборка, запуск и тесты

Нужен Python 3.9 или новее и библиотека PyYAML для чтения YAML. Сборка не требуется.

```
pip install -r requirements.txt
```

Запуск на Windows (из корня проекта; параметры пишутся после имени):

```
.\run.bat
.\run.bat --vfs examples/vfs/sample.xml --script examples/all_commands.txt
```

Запуск на Linux/macOS: `sh run.sh [параметры]`. Или напрямую: `python src/emulator.py [параметры]`.

Тесты (из корня проекта):

```
python -m unittest -v
```

Скрипты для проверки запускают эмулятор несколько раз. В конце они ждут нажатия клавиши. Скрипты этапа 2 вызывают
эмулятор со всеми параметрами (`--vfs`, `--script`, `--config`, `--help`), скрипты этапа 3 в каждом случае
проверяют три вида VFS: минимальную, с несколькими файлами и с несколькими уровнями вложенности.

| Скрипт (папка `scripts/`) | Что проверяет |
|---|---|
| `test_params.bat` | Каждый параметр отдельно и все вместе |
| `test_priority.bat` | Приоритет значений из конфига над командной строкой |
| `test_errors.bat` | Ошибки: нет конфига, неверный YAML, нет скрипта, неизвестный параметр |
| `test_vfs.bat` | Загрузка трёх видов VFS (и из конфига), команда `vfs-info` |
| `test_all_commands.bat` | Скрипт со всеми командами этапов 1–3 на трёх видах VFS и без VFS |
| `test_vfs_errors.bat` | Ошибки VFS: нет файла, не XML, неверный формат; затем три корректные VFS |

```
.\scripts\test_params.bat
.\scripts\test_vfs.bat
.\scripts\test_all_commands.bat
```

## 4. Примеры использования

Скрипт со всеми командами и VFS (`.\run.bat --vfs examples/vfs/sample.xml --script examples/all_commands.txt`),
пользователь `alice`, компьютер `workstation`:

```
=== Virtual machine: shell emulator ===
[debug] command line: vfs=examples/vfs/sample.xml, script=examples/all_commands.txt, config=None
[debug] config file : {}
[debug] used values : vfs=examples/vfs/sample.xml, script=examples/all_commands.txt
VFS loaded: sample (folders: 3, files: 4)
alice@workstation:~$ # Start script that tests all commands of stages 1-3 (use it with --vfs)
alice@workstation:~$ # Stage 1: ls and cd are stubs, they print their name and arguments
alice@workstation:~$ ls
command: ls, arguments: []
alice@workstation:~$ ls -l /home/user
command: ls, arguments: ['-l', '/home/user']
alice@workstation:~$ cd /home/user
command: cd, arguments: ['/home/user']
alice@workstation:~$ cd
command: cd, arguments: []
alice@workstation:~$ # Stage 2: comments work on their own line and after a command
alice@workstation:~$ ls docs   # this part is ignored
command: ls, arguments: ['docs']
alice@workstation:~$ # An unknown command is an error, the script goes on
alice@workstation:~$ foo bar
foo: command not found
alice@workstation:~$ # Stage 3: the service command vfs-info works with the loaded VFS
alice@workstation:~$ vfs-info
VFS: sample (folders: 3, files: 4)
/
  home/
    user/
      data.bin (5 bytes)
      docs/
        todo.txt (16 bytes)
      notes.txt (5 bytes)
  readme.txt (10 bytes)
alice@workstation:~$ # exit ends the work
alice@workstation:~$ exit
```

Ошибка формата VFS (`.\run.bat --vfs examples/vfs/bad_format.xml`), код завершения 1:

```
=== Virtual machine: shell emulator ===
[debug] command line: vfs=examples/vfs/bad_format.xml, script=None, config=None
[debug] config file : {}
[debug] used values : vfs=examples/vfs/bad_format.xml, script=None
VFS error: invalid format in 'examples/vfs/bad_format.xml': unknown element <folder>
```

Другие ошибки VFS (код завершения 1):

```
VFS error: invalid XML in 'examples/vfs/bad_syntax.xml': mismatched tag: line 5, column 2
VFS error: cannot read 'examples/vfs/missing.xml': [Errno 2] No such file or directory: 'examples/vfs/missing.xml'
```

Приоритет конфига. В командной строке указаны `minimal.xml` и `start_a.txt`, а в конфиге другие значения, поэтому
загружается `sample.xml` и выполняется `start_b.txt`
(`.\run.bat --vfs examples/vfs/minimal.xml --script examples/start_a.txt --config examples/config_full.yaml`):

```
=== Virtual machine: shell emulator ===
[debug] command line: vfs=examples/vfs/minimal.xml, script=examples/start_a.txt, config=examples/config_full.yaml
[debug] config file : {'vfs': 'examples/vfs/sample.xml', 'script': 'examples/start_b.txt'}
[debug] used values : vfs=examples/vfs/sample.xml, script=examples/start_b.txt
VFS loaded: sample (folders: 3, files: 4)
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
scripts/              скрипты Windows для проверки параметров и VFS
examples/             примеры: стартовые скрипты, конфиги YAML, XML-файлы VFS (папка vfs/)
requirements.txt      зависимости (PyYAML)
run.bat, run.sh       запуск (Windows / Linux, macOS)
```
