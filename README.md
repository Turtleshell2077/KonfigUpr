# Эмулятор командной оболочки (вариант 14)

Практическая работа № 1 по дисциплине «Конфигурационное управление» (РТУ МИРЭА, ИКБО-10-25).
Готовы все этапы: 1 — REPL, 2 — конфигурация, 3 — VFS, 4 — основные команды, 5 — команды `rmdir` и `rm`.

## 1. Общее описание

Консольная программа на Python, которая имитирует работу в командной строке UNIX-подобной ОС. Это виртуальная
машина: команды выполняются внутри программы, настоящие программы ОС не запускаются. Сверху при запуске
печатается подпись `=== Virtual machine: shell emulator ===`.

Что умеет программа сейчас:

- Приглашение к вводу строится из данных ОС: `username@hostname:~$`. Когда загружена VFS, вместо `~` показывается
  текущая папка внутри VFS: `username@hostname:/home/user$`.
- Параметры запуска `--vfs`, `--script`, `--config` и конфигурационный файл YAML. Значения из файла важнее,
  чем значения из командной строки. При запуске печатаются все параметры (отладочный вывод).
- Стартовый скрипт: команды из файла выполняются по порядку, на экране видны и ввод, и вывод (как диалог).
  Поддерживаются комментарии `#`.
- Виртуальная файловая система (VFS) загружается из XML-файла и целиком хранится в памяти. Служебная команда
  `vfs-info` показывает загруженную VFS. Об ошибках загрузки (нет файла, неверный формат) программа сообщает.
- Команды `ls` и `cd` ходят по папкам VFS, команды `tac` и `rev` читают файлы VFS, `whoami` печатает имя
  пользователя, `exit` завершает работу. Неизвестная команда даёт сообщение `command not found`.
- Команды `rmdir` и `rm` удаляют папки и файлы из VFS, но только в памяти: XML-файл на диске не меняется.

Эмулятор читает только файлы, которые ему указали (конфиг, скрипт, XML-файл VFS), и ничего не записывает на диск.
Содержимое VFS не распаковывается на диск: всё хранится в памяти. Команды `ls`, `cd`, `tac`, `rev` только читают
VFS, а `rmdir` и `rm` меняют её дерево в памяти. Чтобы вернуть удалённое, достаточно запустить эмулятор заново.

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
      <file name="data.bin" encoding="base64">//79/Ps=</file>
    </dir>
  </dir>
  <file name="readme.txt">sample VFS</file>
</vfs>
```

Правила: у каждой папки и файла есть имя без `/` (не `.` и не `..`), имена в одной папке не повторяются, других
элементов быть не должно. Файл загружается целиком в память в виде вложенных словарей (папка — словарь, файл —
байты). Имя `<vfs>` по умолчанию `vfs`. Текущая папка эмулятора хранится отдельно и сначала равна корню.

Примеры в `examples/vfs/`: `minimal.xml` (только корень), `files.xml` (несколько файлов в одной папке),
`sample.xml` (три уровня папок, многострочный и двоичный файлы, скрытый файл `.profile` и файл `report.txt`
больше килобайта для проверки `ls -a` и `ls -h`), `stage5.xml` (пустые папки, папка с вложенной папкой и файлы для
проверки `rmdir` и `rm`), а также сломанные `bad_syntax.xml` (не XML) и `bad_format.xml` (неверная структура).

### Стартовый скрипт

Текстовый файл, по одной команде в строке.

- Каждая строка показывается с приглашением, затем идёт вывод команды, как в диалоге с пользователем.
  Приглашение показывает текущую папку VFS на момент команды.
- Комментарий начинается с `#` (целая строка или конец строки). Комментарии показываются, но не выполняются.
- Пустые строки пропускаются. Ошибочная команда выдаёт сообщение, скрипт продолжается.
- Если скрипт закончился без `exit`, программа остаётся в интерактивном режиме.

Скрипты в `examples/`: `stage4.txt` проверяет все режимы команд этапа 4 (включая ошибки, запускать с
`examples/vfs/sample.xml`), `stage5.txt` — все режимы `rmdir` и `rm` (запускать с `examples/vfs/stage5.xml`),
`all_commands.txt` — краткий обход всех команд, работает с любой VFS и без неё, `show_vfs.txt` — только
`vfs-info`, `start_a.txt` и `start_b.txt` — короткие скрипты для проверки параметров.

### Команды эмулятора

Все сообщения команд печатаются в стандартный вывод. Без загруженной VFS команды `ls`, `cd`, `tac`, `rev`, `rmdir`,
`rm` и `vfs-info` отвечают `имя: no VFS loaded (use --vfs or the config file)`.

| Команда | Что делает |
|---|---|
| `ls [-lah] [путь...]` | Содержимое папки (по умолчанию текущей), по одному имени в строке, у папок знак `/` |
| `cd [путь]` | Переход в папку; без пути — в корень VFS |
| `tac файл...` | Строки файла в обратном порядке |
| `rev файл...` | Каждая строка файла наоборот (справа налево) |
| `whoami` | Имя текущего пользователя (то же, что в приглашении) |
| `rmdir папка...` | Удаляет пустые папки (только в памяти) |
| `rm [-r] путь...` | Удаляет файлы; с `-r` (или `-R`) и папки вместе с содержимым (только в памяти) |
| `vfs-info` | Служебная команда: имя VFS, число папок и файлов, дерево с размерами |
| `exit` | Завершает работу эмулятора |

Пути бывают абсолютными (`/home/user`) и относительными (`docs`, `../user`); `.` — текущая папка, `..` — родитель
(у корня родитель — он сам).

Режимы и сообщения об ошибках:

- `ls`
  - режимы: без аргументов; путь к папке (абсолютный, относительный, `.`, `..`); путь к файлу (печатается его имя);
    несколько путей (перед каждым печатается его имя и `:`);
  - параметры (можно объединять: `-la`, `-lh`, `-lah`, в любом порядке): `-l` — тип (`d` или `-`), размер в байтах и
    имя; `-a` — показать и скрытые имена (начинаются с точки), а также `.` и `..` (без `-a` скрытые не видны);
    `-h` — вместе с `-l` размеры в читаемом виде (`5`, `1.6K`, `2.0M`); один `-h` без `-l` ничего не меняет;
  - ошибки: `ls: cannot access 'путь': No such file or directory`, `ls: invalid option -- 'x'` (неизвестная буква,
    в том числе внутри группы вроде `-lx`), `ls: unrecognized option '--all'`.
- `cd`
  - режимы: абсолютный и относительный путь, `.`, `..`; без аргументов (переход в корень);
  - ошибки: `cd: путь: No such file or directory`, `cd: путь: Not a directory`, `cd: too many arguments`.
- `tac`, `rev`
  - режимы: один или несколько файлов, путь абсолютный или относительный;
  - ошибки (вместо `команда` стоит `tac` или `rev`): `команда: missing file operand`,
    `команда: путь: No such file or directory`, `команда: путь: Is a directory`, `команда: путь: not a text file`.
- `whoami`
  - режим: без аргументов; ошибка: `whoami: extra operand 'x'`.
- `rmdir`
  - режимы: одна папка или несколько сразу (путь абсолютный или относительный); папка должна быть пустой;
  - ошибки: `rmdir: failed to remove 'путь': причина`, где причина — `No such file or directory`, `Not a directory`,
    `Directory not empty` или `Device or resource busy`; `rmdir: missing operand`; `rmdir: invalid option -- 'p'`.
- `rm`
  - режимы: один или несколько файлов; `-r` или `-R` — папки вместе с содержимым (в том числе пустые);
    ошибка в одном пути не мешает удалить остальные;
  - ошибки: `rm: cannot remove 'путь': причина`, где причина — `No such file or directory`, `Is a directory`
    (папка без `-r`) или `Device or resource busy`; `rm: missing operand`; `rm: invalid option -- 'x'`.

Текущую папку и её родителей (включая корень) удалить нельзя: ответ `Device or resource busy`. Так текущая папка
всегда остаётся существующей.

Двоичный файл (не UTF-8) команды `tac` и `rev` не читают и сообщают `not a text file`. `Ctrl+D` (в Windows
`Ctrl+Z`, затем `Enter`) завершает работу, `Ctrl+C` сбрасывает текущую строку (в некоторых консолях Windows Python
сообщает о нём как о конце ввода, тогда эмулятор завершится). Надёжный способ выйти — команда `exit`.

### Ошибки запуска

| Ситуация | Сообщение | Код завершения |
|---|---|---|
| Конфиг не найден, не читается или неверный YAML | `Config error: cannot read ...` | 1 |
| В конфиге не пары «ключ: значение» или значение не строка | `Config error: ...` | 1 |
| Файл VFS не найден или не читается | `VFS error: cannot read ...` | 1 |
| Файл VFS не является XML | `VFS error: invalid XML in ...` | 1 |
| Неверный формат VFS (не тот элемент, нет имени, повтор, плохой base64) | `VFS error: invalid format in ...` | 1 |
| Скрипт не найден или не читается | `Script error: cannot read ...` | 1 |
| Неизвестный параметр командной строки | `usage: ...` и описание ошибки | 2 |

### Функции (файл `src/emulator.py`)

| Функция | Что делает |
|---|---|
| `get_prompt(vfs)` | Приглашение `user@host:путь$ `: `~` без VFS, иначе текущая папка VFS |
| `parse_args(argv)` | Разбирает параметры командной строки |
| `read_config(path)` | Читает YAML-конфиг, проверяет его; при ошибке сообщает и завершает работу |
| `merge_settings(args, file_data)` | Объединяет настройки: значения из файла важнее командной строки |
| `print_debug(args, file_data, settings)` | Отладочный вывод всех параметров |
| `fail(path, message)` | Сообщает о неверном формате VFS и завершает работу |
| `read_xml_root(path)` | Читает XML-файл и возвращает корневой элемент; сообщает, если файла нет или это не XML |
| `check_name(name, tag, path)` | Проверяет имя папки или файла в описании VFS |
| `read_file(item, path)` | Содержимое файла VFS в байтах (текст UTF-8 или base64) |
| `read_dir(element, path)` | Читает содержимое папки (рекурсивно): словарь «имя → папка или байты» |
| `load_vfs(path)` | Загружает VFS из XML-файла в память: `{"name": ..., "root": ..., "cwd": []}` |
| `count_nodes(directory)` | Считает папки и файлы во всём дереве |
| `tree_lines(directory, indent)` | Строки дерева VFS для команды `vfs-info` |
| `vfs_summary(vfs)` | Краткое описание: имя, число папок и файлов |
| `resolve_path(vfs, path)` | Превращает путь (абсолютный или относительный, с `.` и `..`) в список имён |
| `find_node(vfs, parts)` | Находит папку (словарь) или файл (байты) по списку имён, иначе `None` |
| `parse_line(line)` | Делит строку на команду и аргументы, отбрасывает комментарий |
| `need_vfs(name, vfs)` | Проверяет, что VFS загружена; иначе печатает сообщение |
| `is_option(arg)` | Параметр — аргумент вида `-x`; одиночный `-` считается путём |
| `split_args(args)` | Делит аргументы команды на параметры (вида `-x`) и пути |
| `options_ok(command, options, allowed)` | Проверяет буквы параметров (`-lah`); неизвестная — сообщение об ошибке |
| `option_letters(options)` | Множество букв из всех параметров: `['-l', '-ah']` → `{'l', 'a', 'h'}` |
| `human_size(size)` | Размер в читаемом виде: `5`, `1.5K`, `2.0M` (для `ls -lh`) |
| `dir_entries(directory, show_all)` | Элементы папки для `ls`: скрытые только с `-a`, с ними `.` и `..` |
| `entry_line(name, node, flags)` | Строка вывода `ls` для одного элемента (флаги `l`, `h`) |
| `list_path(vfs, path, flags)` | Печатает содержимое папки или строку для файла (для `ls`) |
| `cmd_ls`, `cmd_cd` | Команды `ls` и `cd` |
| `read_vfs_text(command, path, vfs)` | Читает файл VFS как текст; при ошибке печатает сообщение |
| `run_on_files(command, args, vfs, transform)` | Общая часть `tac` и `rev`: читает файлы и печатает результат |
| `reverse_lines(lines)`, `reverse_each(lines)` | Преобразования для `tac` и `rev` |
| `cmd_tac`, `cmd_rev`, `cmd_whoami` | Команды `tac`, `rev` и `whoami` |
| `is_busy(vfs, parts)` | Путь занят: это текущая папка или одна из её родительских |
| `delete_node(vfs, parts)` | Удаляет элемент из дерева VFS в памяти |
| `remove_dir(vfs, path)` | Удаляет пустую папку (для `rmdir`); при ошибке печатает причину |
| `remove_path(vfs, path, recursive)` | Удаляет файл или (с `-r`) папку (для `rm`); при ошибке печатает причину |
| `cmd_rmdir`, `cmd_rm` | Команды `rmdir` и `rm` |
| `cmd_exit`, `cmd_vfs_info` | Команды `exit` и `vfs-info` |
| `run_line(line, vfs)` | Разбирает строку и выполняет команду |
| `run_script(path, vfs)` | Выполняет скрипт, показывая ввод и вывод как диалог |
| `run_repl(vfs)` | Интерактивный цикл: приглашение, ввод, выполнение |
| `make_output_safe()` | Заменяет символы, которых нет в кодировке вывода, чтобы программа не падала |
| `main()` | Точка входа: параметры, VFS, скрипт, затем интерактивный режим |

## 3. Сборка, запуск и тесты

Нужен Python 3.9 или новее и библиотека PyYAML для чтения YAML. Сборка не требуется.

```
pip install -r requirements.txt
```

Запуск на Windows (из корня проекта; параметры пишутся после имени):

```
.\run.bat
.\run.bat --vfs examples/vfs/sample.xml --script examples/stage4.txt
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
| `test_all_commands.bat` | Краткий скрипт со всеми командами на трёх видах VFS и без VFS |
| `test_vfs_errors.bat` | Ошибки VFS: нет файла, не XML, неверный формат; затем три корректные VFS |
| `test_stage4.bat` | Все режимы `ls`, `cd`, `tac`, `rev`, `whoami` (скрипт `stage4.txt`) с VFS и без неё |
| `test_stage5.bat` | Все режимы `rmdir` и `rm` (скрипт `stage5.txt`); второй запуск доказывает, что XML не изменился |

```
.\scripts\test_params.bat
.\scripts\test_vfs.bat
.\scripts\test_stage4.bat
.\scripts\test_stage5.bat
```

### Команды для проверки каждого этапа

Запуск делается из корня проекта. Строки без `.\run.bat` вводятся внутри эмулятора, после приглашения. Выход: `exit`.

**Этап 1 — REPL.** Запуск без параметров, внутри можно ввести `foo` (ответ `command not found`) и `exit`:

```
.\run.bat
```

**Этап 2 — параметры и конфиг.** Скрипт из командной строки; всё из конфига; значения конфига важнее командной
строки; `vfs` из конфига, а скрипт из командной строки:

```
.\run.bat --script examples/start_a.txt
.\run.bat --config examples/config_full.yaml
.\run.bat --vfs examples/vfs/minimal.xml --script examples/start_a.txt --config examples/config_full.yaml
.\run.bat --vfs examples/vfs/minimal.xml --script examples/start_a.txt --config examples/config_vfs_only.yaml
```

Ошибки (коды завершения 1, 1, 1 и 2):

```
.\run.bat --config nope.yaml
.\run.bat --config examples/config_bad_syntax.yaml
.\run.bat --script nope.txt
.\run.bat --unknown
```

**Этап 3 — VFS.** Три вида VFS (минимальная, с несколькими файлами, с вложенными папками), внутри команда
`vfs-info`; в последней строке VFS вместе со скриптом, проверяющим все команды:

```
.\run.bat --vfs examples/vfs/minimal.xml
.\run.bat --vfs examples/vfs/files.xml
.\run.bat --vfs examples/vfs/sample.xml
.\run.bat --vfs examples/vfs/sample.xml --script examples/all_commands.txt
```

Ошибки загрузки (код завершения 1): нет файла, не XML, неверный формат:

```
.\run.bat --vfs examples/vfs/missing.xml
.\run.bat --vfs examples/vfs/bad_syntax.xml
.\run.bat --vfs examples/vfs/bad_format.xml
```

**Этап 4 — `ls`, `cd`, `tac`, `rev`, `whoami`.** Все режимы скриптом, или вручную на `sample.xml`:

```
.\run.bat --vfs examples/vfs/sample.xml --script examples/stage4.txt
.\run.bat --vfs examples/vfs/sample.xml
```

Команды для ручного ввода (по порядку: папка; `-l`; скрытые `-a`; читаемые размеры `-h`; все вместе; несколько путей):

```
ls
ls -l /home/user
ls -a /home/user
ls -lh /home/user
ls -lah /home/user
ls /home /home/user/docs
cd /home/user
cd docs
cd ..
cd
tac /home/user/docs/todo.txt
rev /home/user/notes.txt
whoami
```

Ошибки (нет пути, неверный параметр, неверная буква в группе, файл вместо папки, лишний аргумент, нет файла, не текст):

```
ls /nope
ls -x
ls -lx
cd /readme.txt
cd a b
tac
rev /home/user/data.bin
whoami x
```

**Этап 5 — `rmdir`, `rm`.** Все режимы скриптом, или вручную на `stage5.xml`:

```
.\run.bat --vfs examples/vfs/stage5.xml --script examples/stage5.txt
.\run.bat --vfs examples/vfs/stage5.xml
```

Команды для ручного ввода (удаление файла, нескольких файлов, нескольких пустых папок, папки с `-R` и `-r`):

```
vfs-info
rm old.txt
rm docs/a.txt docs/b.txt
rmdir empty1 docs
rm -R empty2
rm -r nested
vfs-info
```

Ошибки (запустите эмулятор заново, чтобы всё удалённое вернулось):

```
rm docs
rmdir nested
rmdir readme.txt
rm
rmdir -p x
cd empty1
rmdir .
```

Все эти запуски собраны и в готовых скриптах из таблицы выше (`scripts/test_stage4.bat`, `scripts/test_stage5.bat` и
другие).

## 4. Примеры использования

Интерактивные команды этапа 4 можно проверить так: `.\run.bat --vfs examples/vfs/sample.xml`, затем ввести команды
из примера. Ниже тот же набор команд выполнен скриптом, пользователь `alice`, компьютер `workstation`:

```
=== Virtual machine: shell emulator ===
[debug] command line: vfs=examples/vfs/sample.xml, script=demo.txt, config=None
[debug] config file : {}
[debug] used values : vfs=examples/vfs/sample.xml, script=demo.txt
VFS loaded: sample (folders: 3, files: 6)
alice@workstation:/$ cd /home/user
alice@workstation:/home/user$ ls
data.bin
docs/
notes.txt
report.txt
alice@workstation:/home/user$ ls -l
-        5 data.bin
d        - docs/
-        5 notes.txt
-     1639 report.txt
alice@workstation:/home/user$ ls -a
./
../
.profile
data.bin
docs/
notes.txt
report.txt
alice@workstation:/home/user$ ls -lh
-        5 data.bin
d        - docs/
-        5 notes.txt
-     1.6K report.txt
alice@workstation:/home/user$ ls -lah
d        - ./
d        - ../
-       18 .profile
-        5 data.bin
d        - docs/
-        5 notes.txt
-     1.6K report.txt
alice@workstation:/home/user$ cd docs
alice@workstation:/home/user/docs$ tac todo.txt
send to teacher
check the code
write the report
alice@workstation:/home/user/docs$ rev todo.txt
troper eht etirw
edoc eht kcehc
rehcaet ot dnes
alice@workstation:/home/user/docs$ cd ..
alice@workstation:/home/user$ rev data.bin
rev: data.bin: not a text file
alice@workstation:/home/user$ cd /nope
cd: /nope: No such file or directory
alice@workstation:/home/user$ ls /nope
ls: cannot access '/nope': No such file or directory
alice@workstation:/home/user$ ls -lx
ls: invalid option -- 'x'
alice@workstation:/home/user$ whoami
alice
alice@workstation:/home/user$ exit
```

Краткий скрипт со всеми командами (`.\run.bat --vfs examples/vfs/sample.xml --script examples/all_commands.txt`),
отладочные строки опущены:

```
VFS loaded: sample (folders: 3, files: 6)
alice@workstation:/$ whoami
alice
alice@workstation:/$ vfs-info
VFS: sample (folders: 3, files: 6)
/
  home/
    user/
      .profile (18 bytes)
      data.bin (5 bytes)
      docs/
        todo.txt (47 bytes)
      notes.txt (5 bytes)
      report.txt (1639 bytes)
  readme.txt (10 bytes)
alice@workstation:/$ ls
home/
readme.txt
alice@workstation:/$ ls -l /
d        - home/
-       10 readme.txt
alice@workstation:/$ tac readme.txt
sample VFS
alice@workstation:/$ rev readme.txt
SFV elpmas
alice@workstation:/$ rm readme.txt
alice@workstation:/$ rmdir nope
rmdir: failed to remove 'nope': No such file or directory
alice@workstation:/$ ls
home/
alice@workstation:/$ foo bar
foo: command not found
alice@workstation:/$ exit
```

Команды этапа 5 (`.\run.bat --vfs examples/vfs/stage5.xml`, затем эти команды). VFS меняется только в памяти:
`rm` без `-r` не удаляет папку, `rmdir` удаляет только пустую, текущую папку удалить нельзя:

```
VFS loaded: stage5 (folders: 5, files: 5)
alice@workstation:/$ ls
docs/
empty1/
empty2/
nested/
old.txt
readme.txt
alice@workstation:/$ rm old.txt
alice@workstation:/$ rm docs
rm: cannot remove 'docs': Is a directory
alice@workstation:/$ rmdir docs
rmdir: failed to remove 'docs': Directory not empty
alice@workstation:/$ rm docs/a.txt docs/b.txt
alice@workstation:/$ rmdir empty1 docs
alice@workstation:/$ cd empty2
alice@workstation:/empty2$ rmdir .
rmdir: failed to remove '.': Device or resource busy
alice@workstation:/empty2$ cd /
alice@workstation:/$ rm -r nested
alice@workstation:/$ vfs-info
VFS: stage5 (folders: 1, files: 1)
/
  empty2/
  readme.txt (7 bytes)
alice@workstation:/$ exit
```

Все режимы и ошибки `rmdir` и `rm` собраны в скрипте `examples/stage5.txt`
(`.\run.bat --vfs examples/vfs/stage5.xml --script examples/stage5.txt`).

Без VFS команды отвечают, что она не загружена (`.\run.bat`, затем команды), а `whoami` работает:

```
alice@workstation:~$ ls
ls: no VFS loaded (use --vfs or the config file)
alice@workstation:~$ whoami
alice
```

Ошибка формата VFS (`.\run.bat --vfs examples/vfs/bad_format.xml`), код завершения 1:

```
=== Virtual machine: shell emulator ===
[debug] command line: vfs=examples/vfs/bad_format.xml, script=None, config=None
[debug] config file : {}
[debug] used values : vfs=examples/vfs/bad_format.xml, script=None
VFS error: invalid format in 'examples/vfs/bad_format.xml': unknown element <folder>
```

Приоритет конфига. В командной строке указаны `minimal.xml` и `start_a.txt`, а в конфиге другие значения, поэтому
загружается `sample.xml` и выполняется `start_b.txt`
(`.\run.bat --vfs examples/vfs/minimal.xml --script examples/start_a.txt --config examples/config_full.yaml`):

```
=== Virtual machine: shell emulator ===
[debug] command line: vfs=examples/vfs/minimal.xml, script=examples/start_a.txt, config=examples/config_full.yaml
[debug] config file : {'vfs': 'examples/vfs/sample.xml', 'script': 'examples/start_b.txt'}
[debug] used values : vfs=examples/vfs/sample.xml, script=examples/start_b.txt
VFS loaded: sample (folders: 3, files: 6)
alice@workstation:/$ # Start script B: an alternative script
alice@workstation:/$ whoami
alice
alice@workstation:/$ vfs-info
VFS: sample (folders: 3, files: 6)
/
  home/
    user/
      .profile (18 bytes)
      data.bin (5 bytes)
      docs/
        todo.txt (47 bytes)
      notes.txt (5 bytes)
      report.txt (1639 bytes)
  readme.txt (10 bytes)
alice@workstation:/$ exit
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
scripts/              скрипты Windows для проверки параметров, VFS и команд
examples/             примеры: стартовые скрипты, конфиги YAML, XML-файлы VFS (папка vfs/)
requirements.txt      зависимости (PyYAML)
run.bat, run.sh       запуск (Windows / Linux, macOS)
```
