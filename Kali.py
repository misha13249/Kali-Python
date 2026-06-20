#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
             MONOLITHIC KALI LINUX SUBSYSTEM SIMULATOR (v4.0)
=============================================================================
Добавлены: nano, touch, mkdir, rm, cp, mv, find, grep, htop, hostname,
           tree, history, df, free, автодополнение, улучшенный APT с
           зависимостями и расширенная VFS.
=============================================================================
"""

import os
import sys
import time
import random
import re
import hashlib
import readline
from datetime import datetime

# =============================================================================
# РЕПОЗИТОРИИ УДАЛЕННЫХ СЕРВЕРОВ (с зависимостями)
# =============================================================================

APT_REMOTE_REPOSITORY = {
    "python3": {
        "version": "3.11.2-1",
        "size": "34.2 MB",
        "desc": "Interactive high-level object-oriented language",
        "deps": ["libpython3.11", "python3-minimal"]
    },
    "nmap": {
        "version": "7.93+dfsg1-1",
        "size": "5.8 MB",
        "desc": "The Network Mapper",
        "deps": ["libpcap0.8", "liblua5.3"]
    },
    "hydra": {
        "version": "9.4-1",
        "size": "1.2 MB",
        "desc": "Very fast network logon cracker",
        "deps": ["libssl3", "libc6"]
    },
    "macchanger": {
        "version": "1.7.0-1",
        "size": "220 KB",
        "desc": "MAC address manipulator",
        "deps": []
    },
    "curl": {
        "version": "7.88.1-10",
        "size": "410 KB",
        "desc": "Command line tool for transferring data",
        "deps": ["libcurl4"]
    },
    "htop": {
        "version": "3.2.2-1",
        "size": "1.1 MB",
        "desc": "Interactive process viewer",
        "deps": ["libncursesw6", "libc6"]
    },
    "tree": {
        "version": "2.1.0-1",
        "size": "120 KB",
        "desc": "List contents of directories in a tree-like format",
        "deps": []
    },
    "nano": {
        "version": "7.2-1",
        "size": "450 KB",
        "desc": "GNU nano text editor",
        "deps": ["libncursesw6"]
    }
}

PIP_REMOTE_REPOSITORY = {
    "requests": {"version": "2.31.0", "deps": [], "desc": "Python HTTP for Humans."},
    "scapy": {"version": "2.5.0", "deps": [], "desc": "Packet manipulation library."},
    "impacket": {"version": "0.11.0", "deps": ["pycryptodome"], "desc": "Network protocols pooling."},
    "pycryptodome": {"version": "3.19.0", "deps": [], "desc": "Cryptographic tools."},
    "pwntools": {"version": "4.11.0", "deps": ["requests"], "desc": "CTF framework and exploit development."}
}

# =============================================================================
# ВИРТУАЛЬНАЯ ФАЙЛОВАЯ СИСТЕМА (VFS) – расширенная
# =============================================================================

class VirtualFileSystem:
    def __init__(self):
        self.root = {
            "bin": {"ls": "sys_bin", "cat": "sys_bin", "cd": "sys_bin", "pwd": "sys_bin", "echo": "sys_bin"},
            "usr": {"bin": {}, "share": {"wordlists": {"rockyou.txt": "admin\npassword\n123456\nqwerty\nletmein"}}},
            "etc": {"apt": {"sources.list": "deb http://http.kali.org/kali kali-rolling main contrib non-free"}, "passwd": "root:x:0:0:\nkali:x:1000:1000:"},
            "home": {
                "kali": {
                    "Desktop": {},
                    "Downloads": {},
                    "scripts": {
                        "test.py": "print('Hello from virtual Python inside Kali!')\nx = 10\ny = 20\nprint('Result:', x + y)"
                    }
                }
            },
            "var": {"log": {"apt": {"history.log": "Log started.\n"}}}
        }
        self.current_path = ["home", "kali"]

    def get_node(self, path_list):
        curr = self.root
        for step in path_list:
            if isinstance(curr, dict) and step in curr:
                curr = curr[step]
            else:
                return None
        return curr

    def change_dir(self, target):
        if not target or target == "~":
            self.current_path = ["home", "kali"]
            return True
        if target == "/":
            self.current_path = []
            return True

        parts = target.split("/")
        temp = list(self.current_path) if not target.startswith("/") else []
        
        for p in parts:
            if p == "" or p == ".": continue
            if p == "..":
                if temp: temp.pop()
            else:
                temp.append(p)
                if not isinstance(self.get_node(temp), dict):
                    return False
        self.current_path = temp
        return True

    def write_file(self, filename, content):
        node = self.get_node(self.current_path)
        if isinstance(node, dict):
            node[filename] = content
            return True
        return False

    def read_file(self, filename):
        # Поиск в текущей директории
        node = self.get_node(self.current_path)
        if isinstance(node, dict) and filename in node and not isinstance(node[filename], dict):
            return node[filename]
        
        # Поиск по абсолютному/относительному пути, если передан путь
        if "/" in filename:
            parts = filename.split("/")
            f_name = parts.pop()
            temp_path = list(self.current_path) if not filename.startswith("/") else []
            for p in parts:
                if p == "" or p == ".": continue
                if p == "..": 
                    if temp_path: temp_path.pop()
                else: temp_path.append(p)
            target_node = self.get_node(temp_path)
            if isinstance(target_node, dict) and f_name in target_node:
                return target_node[f_name]
        return None

    def mkdir(self, dirname):
        node = self.get_node(self.current_path)
        if isinstance(node, dict):
            if dirname in node:
                return f"mkdir: cannot create directory '{dirname}': File exists"
            node[dirname] = {}
            return ""
        return "mkdir: cannot create directory: no such file or directory"

    def touch(self, filename):
        node = self.get_node(self.current_path)
        if isinstance(node, dict):
            if filename not in node:
                node[filename] = ""
            return ""
        return "touch: cannot touch file: no such file or directory"

    def rm(self, name, recursive=False):
        node = self.get_node(self.current_path)
        if isinstance(node, dict) and name in node:
            if isinstance(node[name], dict) and not recursive:
                return f"rm: cannot remove '{name}': Is a directory"
            del node[name]
            return ""
        return f"rm: cannot remove '{name}': No such file or directory"

    def cp(self, src, dst):
        # Поддерживаем только копирование в текущей директории
        node = self.get_node(self.current_path)
        if not isinstance(node, dict):
            return "cp: error"
        if src not in node:
            return f"cp: cannot stat '{src}': No such file or directory"
        if dst in node:
            return f"cp: will not overwrite just created '{dst}'"
        # Простое копирование содержимого
        node[dst] = node[src]
        return ""

    def mv(self, src, dst):
        node = self.get_node(self.current_path)
        if not isinstance(node, dict):
            return "mv: error"
        if src not in node:
            return f"mv: cannot stat '{src}': No such file or directory"
        if dst in node:
            return f"mv: will not overwrite '{dst}'"
        node[dst] = node[src]
        del node[src]
        return ""

    def find(self, name, start_path=None):
        # Поиск файла/директории по имени начиная с start_path (или текущей)
        if start_path is None:
            start_path = self.current_path
        else:
            # Парсим путь
            parts = start_path.split("/")
            start_path = parts if start_path.startswith("/") else self.current_path + parts
        result = []
        self._find_recursive(self.get_node(start_path), start_path, name, result)
        return result

    def _find_recursive(self, node, path_parts, name, result):
        if not isinstance(node, dict):
            return
        for key, val in node.items():
            full_path = "/" + "/".join(path_parts + [key])
            if key == name:
                result.append(full_path)
            if isinstance(val, dict):
                self._find_recursive(val, path_parts + [key], name, result)

    def grep(self, pattern, filename):
        content = self.read_file(filename)
        if content is None:
            return f"grep: {filename}: No such file or directory"
        lines = content.split("\n")
        matches = []
        for i, line in enumerate(lines):
            if re.search(pattern, line):
                matches.append(f"{filename}:{i+1}:{line}")
        return "\n".join(matches) if matches else ""

    def tree(self, start_path=None):
        if start_path is None:
            start_path = self.current_path
        else:
            parts = start_path.split("/")
            start_path = parts if start_path.startswith("/") else self.current_path + parts
        node = self.get_node(start_path)
        if not isinstance(node, dict):
            return "tree: no such directory"
        out = [start_path[-1] if start_path else "/"]
        self._tree_recursive(node, start_path, out, "")
        return "\n".join(out)

    def _tree_recursive(self, node, path_parts, out, prefix):
        items = list(node.keys())
        for i, key in enumerate(items):
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            out.append(prefix + connector + key)
            if isinstance(node[key], dict):
                new_prefix = prefix + ("    " if is_last else "│   ")
                self._tree_recursive(node[key], path_parts + [key], out, new_prefix)

    def df(self):
        # Симуляция использования диска
        total = 1024 * 1024  # 1 ГБ в блоках (симуляция)
        used = 0
        # Подсчёт размера всех файлов (упрощённо)
        def count_size(node):
            if not isinstance(node, dict):
                return len(node.encode('utf-8'))
            total_size = 0
            for v in node.values():
                total_size += count_size(v)
            return total_size
        used = count_size(self.root)
        used_kb = used // 1024
        total_kb = total // 1024
        available = total_kb - used_kb
        return f"Filesystem     1K-blocks      Used Available Use% Mounted on\n/dev/sda1         {total_kb:10} {used_kb:10} {available:10} {round(used_kb/total_kb*100)}% /"

    def free(self):
        # Симуляция памяти
        total = 8192  # 8 ГБ
        used = random.randint(3000, 6000)
        free = total - used
        shared = random.randint(200, 800)
        buff_cache = random.randint(500, 1500)
        available = free + buff_cache
        return f"              total        used        free      shared  buff/cache   available\nMem:          {total:10} {used:10} {free:10} {shared:10} {buff_cache:10} {available:10}\nSwap:         2048       0       2048"

# =============================================================================
# СЕТЕВАЯ ПОДСИСТЕМА И ИНСТРУМЕНТЫ БЕЗОПАСНОСТИ
# =============================================================================

class NetworkInterface:
    def __init__(self, name, ip, mac, state="UP"):
        self.name = name
        self.ip = ip
        self.mac = mac
        self.state = state

class NetworkAndSecurityEngine:
    def __init__(self):
        self.interfaces = {
            "lo": NetworkInterface("lo", "127.0.0.1", "00:00:00:00:00:00"),
            "eth0": NetworkInterface("eth0", "192.168.1.15", "00:0c:29:ed:14:a2")
        }
        self.dns = {"kali.org": "192.124.249.10", "google.com": "142.250.185.78"}
        self.hostname = "kali"

    def ip_cmd(self, args):
        if not args or args[0] not in ["addr", "a"]:
            return "Использование: ip addr"
        out = []
        for name, iface in self.interfaces.items():
            out.append(f"{name}: <BROADCAST,MULTICAST,{iface.state}> mtu 1500")
            out.append(f"    link/ether {iface.mac} brd ff:ff:ff:ff:ff:ff")
            if iface.state == "UP":
                out.append(f"    inet {iface.ip}/24 brd {iface.ip.rpartition('.')[0]}.255 scope global {name}")
        return "\n".join(out)

    def ping_cmd(self, args):
        if not args: return "ping: missing host operand"
        host = args[0]
        ip = self.dns.get(host, host)
        print(f"PING {host} ({ip}) 56(84) bytes of data.")
        for i in range(3):
            time.sleep(0.5)
            print(f"64 bytes from {ip}: icmp_seq={i+1} ttl=64 time={round(random.uniform(15, 40), 1)} ms")
        return f"--- {host} ping statistics --- \n3 packets transmitted, 3 received, 0% packet loss"

    def macchanger_cmd(self, args):
        if not args or args[0] != "-r":
            return "Использование: macchanger -r [interface]\nПример: macchanger -r eth0"
        iface = args[1] if len(args) > 1 else "eth0"
        if iface not in self.interfaces:
            return f"Interface {iface} not found."
        old_mac = self.interfaces[iface].mac
        new_mac = ":".join([f"{random.randint(0, 255):02x}" for _ in range(6)])
        self.interfaces[iface].mac = new_mac
        return f"Current MAC:   {old_mac}\nNew MAC:       {new_mac}\nAddress successfully changed."

    def nmap_cmd(self, args):
        if not args: return "Использование: nmap [target IP/Host]"
        target = args[-1]
        print(f"Starting Nmap 7.93 at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        time.sleep(1.5)
        print(f"Nmap scan report for {target}\nHost is up.\n\nPORT     STATE SERVICE")
        print("22/tcp   open  ssh\n80/tcp   open  http\n443/tcp  open  https")
        return "Nmap done: 1 IP address scanned in 1.52 seconds."

    def hydra_cmd(self, args, vfs):
        if len(args) < 4:
            return "Использование: hydra -l [user] -P [wordlist] [target] ssh\nПример: hydra -l root -P /usr/share/wordlists/rockyou.txt 192.168.1.15 ssh"
        try:
            wl_path = args[args.index("-P") + 1]
            user = args[args.index("-l") + 1]
        except (ValueError, IndexError):
            return "Ошибка синтаксиса. Проверьте флаги -l и -P."
        
        words = vfs.read_file(wl_path)
        if not words:
            return f"hydra: Ошибка: Словник {wl_path} не найден."
        
        passwords = words.strip().split("\n")
        print(f"Hydra v9.4 initialized. Attacking target {args[-2]}...")
        for p in passwords:
            time.sleep(0.3)
            print(f"[Attempt] User: {user} | Password: {p:<10} -> Access Denied")
            if p == "letmein":
                return f"\n[+][DATA] target un-locked!\nHost: {args[-2]} | User: {user} | Password: {p}"
        return "Attack finished: No credentials found."

# =============================================================================
# СИСТЕМА КОНТРОЛЯ ВЕРСИЙ (GIT ENGINE)
# =============================================================================

class GitEngine:
    def __init__(self):
        self.repo_active = False
        self.staged = []
        self.history = []

    def execute(self, args, current_files):
        if not args: return "git: missing command. Commands: init, add, commit, log"
        action = args[0]
        
        if action == "init":
            self.repo_active = True
            return "Initialized empty Git repository in current directory."
        
        if not self.repo_active:
            return "fatal: not a git repository (or any of the parent directories): .git"

        if action == "add":
            files = args[1:]
            if not files: return "Nothing specified, nothing added."
            if files[0] == ".":
                self.staged.extend([f for f in current_files if not f.startswith(".")])
            else:
                for f in files:
                    if f in current_files: self.staged.append(f)
                    else: return f"fatal: pathspec '{f}' did not match any files"
            return f"Staged {len(self.staged)} files."

        elif action == "commit":
            if "-m" not in args or len(args) < 3: return "error: switch 'm' requires a value"
            if not self.staged: return "nothing to commit, working tree clean"
            msg = " ".join(args[args.index("-m")+1:]).strip('"')
            c_hash = hashlib.md5(str(time.time()).encode()).hexdigest()[:7]
            self.history.append({"hash": c_hash, "msg": msg, "date": datetime.now().strftime("%c"), "files": list(self.staged)})
            self.staged.clear()
            return f"[main {c_hash}] {msg}\n Files committed into local tree."

        elif action == "log":
            if not self.history: return "No commits yet."
            return "\n".join([f"\033[1;33mcommit {c['hash']}\033[0m\nDate: {c['date']}\n\n    {c['msg']}\n" for c in reversed(self.history)])
        
        return f"git: '{action}' is not a valid command."

# =============================================================================
# МЕНЕДЖЕРЫ ПАКЕТОВ (APT & PIP) – с зависимостями
# =============================================================================

class PackageManagerSystem:
    def __init__(self):
        self.installed_apt = ["ls", "cat", "cd", "pwd", "echo"] # Предустановленный базовый софт
        self.installed_pip = {"pip": "23.0.1"}
        self.apt_updated = False

    def apt_execute(self, args):
        if not args: return "Advanced Package Tool. Commands: update, install [pkg], remove [pkg]"
        action = args[0]
        
        if action == "update":
            print("Get:1 http://http.kali.org/kali kali-rolling InRelease [41.2 kB]")
            time.sleep(0.5)
            print("Get:2 http://http.kali.org/kali kali-rolling/main amd64 Packages [19.5 MB]")
            time.sleep(1.0)
            self.apt_updated = True
            return "Reading package lists... Done.\nBuilding dependency tree... Done."
        
        if action == "install":
            if len(args) < 2: return "E: You must specify at least one package to install"
            pkg = args[1]
            if pkg in self.installed_apt:
                return f"{pkg} is already the newest version."
            if pkg in APT_REMOTE_REPOSITORY:
                # Установка зависимостей
                deps = APT_REMOTE_REPOSITORY[pkg].get("deps", [])
                for dep in deps:
                    if dep not in self.installed_apt:
                        print(f"Installing dependency: {dep}")
                        self.apt_execute(["install", dep])  # рекурсивно
                # Установка самого пакета
                print(f"Reading package lists... Done\nBuilding dependency tree... Done")
                print(f"The following NEW packages will be installed:\n  {pkg}")
                print(f"Need to get {APT_REMOTE_REPOSITORY[pkg]['size']} of archives.")
                time.sleep(1.2)
                print(f"Unpacking {pkg} ({APT_REMOTE_REPOSITORY[pkg]['version']})...")
                time.sleep(0.5)
                print(f"Setting up {pkg}...")
                self.installed_apt.append(pkg)
                return "Processing triggers for man-db (2.11.2-1)... Done."
            else:
                return f"E: Unable to locate package {pkg}"
        elif action == "remove":
            if len(args) < 2: return "E: You must specify at least one package to remove"
            pkg = args[1]
            if pkg in self.installed_apt:
                self.installed_apt.remove(pkg)
                return f"Removing {pkg}... Done."
            return f"Package {pkg} is not installed."
        return f"Unknown apt command: {action}"

    def pip_execute(self, args):
        if "python3" not in self.installed_apt:
            return "bash: pip: command not found (Установите python3 через apt install)"
        if not args: return "Pip Core Interface. Commands: list, install [package]"
        
        action = args[0]
        if action == "list":
            return "\n".join([f"{k:<15} {v}" for k, v in self.installed_pip.items()])
        if action == "install":
            if len(args) < 2: return "error: Minimum arguments not reached."
            pkg = args[1].lower()
            if pkg in self.installed_pip: return f"Requirement already satisfied: {pkg}"
            if pkg in PIP_REMOTE_REPOSITORY:
                print(f"Collecting {pkg}...\n  Downloading {pkg}-{PIP_REMOTE_REPOSITORY[pkg]['version']}-py3-none-any.whl")
                time.sleep(1.0)
                self.installed_pip[pkg] = PIP_REMOTE_REPOSITORY[pkg]['version']
                return f"Successfully installed {pkg}"
            return f"ERROR: Could not find a version that satisfies the requirement {pkg}"
        return f"Unknown pip command."

    def run_python_runtime(self, filename, vfs):
        if "python3" not in self.installed_apt:
            return "bash: python3: command not found (Установите python3 с помощью apt install)"
        
        code = vfs.read_file(filename)
        if not code:
            return f"python3: can't open file '{filename}': [Errno 2] No such file or directory"
        
        print(f"--- [Executing {filename} via Python Virtual Runtime] ---")
        lines = code.split("\n")
        local_vars = {}
        
        for index, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith("#"): continue
            
            if line.startswith("print("):
                content_match = re.match(r"print\((.*)\)", line)
                if content_match:
                    args_str = content_match.group(1)
                    parts = re.split(r",(?=(?:[^']*'[^']*')*[^']*$)", args_str)
                    out_parts = []
                    for p in parts:
                        p = p.strip()
                        if (p.startswith("'") and p.endswith("'")) or (p.startswith('"') and p.endswith('"')):
                            out_parts.append(p[1:-1])
                        elif p in local_vars:
                            out_parts.append(str(local_vars[p]))
                        else:
                            try:
                                out_parts.append(str(eval(p, {}, local_vars)))
                            except:
                                out_parts.append(p)
                    print(" ".join(out_parts))
                    
            elif "=" in line:
                var_name, expr = line.split("=", 1)
                var_name = var_name.strip()
                expr = expr.strip()
                try:
                    local_vars[var_name] = eval(expr, {}, local_vars)
                except Exception as e:
                    print(f"Python Runtime Error [Line {index+1}]: Сбой парсинга выражения '{expr}'")
        return "--- [Process completed with exit code 0] ---"

# =============================================================================
# АВТОДОПОЛНЕНИЕ (readline)
# =============================================================================

class Completer:
    def __init__(self, commands, vfs):
        self.commands = commands
        self.vfs = vfs

    def complete(self, text, state):
        # Разбиваем строку на слова, учитывая пробелы
        line = readline.get_line_buffer()
        words = line.split()
        if not words:
            # Дополнение команд
            options = [c for c in self.commands if c.startswith(text)]
        elif len(words) == 1 and text == words[-1]:
            # Дополнение команд
            options = [c for c in self.commands if c.startswith(text)]
        else:
            # Дополнение путей для аргументов (просто имена файлов/папок в текущей директории)
            prefix = words[-1] if text else ""
            node = self.vfs.get_node(self.vfs.current_path)
            if isinstance(node, dict):
                options = [k for k in node.keys() if k.startswith(prefix)]
            else:
                options = []
        try:
            return options[state]
        except IndexError:
            return None

# =============================================================================
# ЦЕНТРАЛЬНАЯ ОПЕРАЦИОННАЯ СИСТЕМА (MAIN INTERACTIVE SHELL CONTEXT)
# =============================================================================

class KaliOperatingSystem:
    def __init__(self):
        self.vfs = VirtualFileSystem()
        self.net_sec = NetworkAndSecurityEngine()
        self.git = GitEngine()
        self.pkg = PackageManagerSystem()
        self.running = True
        self.history = []  # история команд
        self.commands = [
            "help", "clear", "exit", "ls", "cd", "pwd", "cat", "echo",
            "apt", "pip", "python3", "ip", "ping", "macchanger", "nmap", "hydra",
            "git", "nano", "touch", "mkdir", "rm", "cp", "mv", "find", "grep",
            "htop", "hostname", "tree", "history", "df", "free"
        ]
        # Установка автодополнения
        completer = Completer(self.commands, self.vfs)
        readline.set_completer(completer.complete)
        readline.parse_and_bind("tab: complete")

    def boot(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\033[1;31m")
        print(r"  _  __     _ _   _     _                     ____   ____  ")
        print(r" | |/ /__ _| (_) | |   (_)_ __  _   ___  __  / ___| / ___| ")
        print(r" | ' // _` | | | | |   | | '_ \| | | \ \/ /  \___ \| |     ")
        print(r" | . \ (_| | | | | |___| | | | | |_| |>  <    ___) | |___  ")
        print(r" |_|\_\__,_|_|_| |_____|_|_| |_|\__,_/_/\_\  |____/ \____| ")
        print("\033[0m")
        print(f" Kali Linux OS Core Simulation Ecosystem [Kernel: 6.1.0-kali7-amd64] (v4.0)")
        print(f" Текущее время системы: {datetime.now().strftime('%A, %B %d, %Y')}")
        print(f" ПРЕДУПРЕЖДЕНИЕ: Инструменты хакинга (nmap, hydra) заблокированы, пока не будут установлены.")
        print(f" Введите '\033[1;32mhelp\033[0m' для получения списка команд.\n")

    def show_matrix_help(self):
        print("""
 Доступные команды в сборке v4.0:
 -----------------------------------------------------------------
 [Система и ФС]       ls, cd [dir], pwd, cat [file], clear, exit
 [Работа с файлами]   echo "текст" > [файл], touch [файл], mkdir [dir]
                      rm [файл/папка], rm -r [папка], cp [src] [dst]
                      mv [src] [dst], find [имя], grep [pattern] [file]
 [Текстовый редактор] nano [файл]
 [Менеджер APT]       apt update, apt install [python3/nmap/hydra/...]
 [Менеджер PIP]       pip list, pip install [requests/scapy/...]
 [Интерпретатор]      python3 [файл.py] (Запуск скриптов)
 [Сеть и Линки]       ip addr, ping [host], hostname
 [Инструменты Kali]   macchanger -r [iface], nmap [IP], hydra -l [u] -P [w] [IP] ssh
 [Мониторинг]         htop, df, free
 [Дерево и история]   tree [dir], history
 [Локальный Git]      git init, git add ., git commit -m "msg", git log
 -----------------------------------------------------------------
        """)

    def enforce_execution_security(self, command_name):
        """Проверка, установлен ли пакет в системе."""
        if command_name in ["nmap", "hydra", "macchanger", "python3", "htop", "tree", "nano"]:
            if command_name not in self.pkg.installed_apt:
                print(f"bash: {command_name}: command not found. Попробуйте выполнить: apt install {command_name}")
                return False
        return True

    def process_input(self):
        curr_path_string = "/" + "/".join(self.vfs.current_path)
        prompt = f"\033[1;31m┌──(kali💀kali)-[{curr_path_string}]\n└─$ \033[0m"
        
        try:
            raw_line = input(prompt)
        except (KeyboardInterrupt, EOFError):
            print("\nВведите 'exit' для завершения сессии.")
            return

        if not raw_line.strip(): return
        
        # Сохраняем в историю
        self.history.append(raw_line)

        tokens = raw_line.strip().split()
        cmd = tokens[0]
        args = tokens[1:]

        # Валидация установки пакета перед запуском
        if not self.enforce_execution_security(cmd):
            return

        # Логика обработки глобальных команд
        if cmd == "help":
            self.show_matrix_help()
        elif cmd == "clear":
            os.system('cls' if os.name == 'nt' else 'clear')
        elif cmd == "exit":
            print("\nShutting down virtualization cores safely... Goodbye!")
            self.running = False
            
        elif cmd == "ls":
            node = self.vfs.get_node(self.vfs.current_path)
            if isinstance(node, dict):
                for k, v in node.items():
                    if isinstance(v, dict): print(f"\033[1;34m{k}/\033[0m  ", end="")
                    else: print(f"{k}  ", end="")
                print()
                
        elif cmd == "cd":
            target = args[0] if args else "~"
            if not self.vfs.change_dir(target):
                print(f"bash: cd: {target}: No such file or directory")
                
        elif cmd == "pwd":
            print("/" + "/".join(self.vfs.current_path))
            
        elif cmd == "cat":
            if not args:
                print("cat: missing file operand")
                return
            res = self.vfs.read_file(args[0])
            if res is not None: print(res)
            else: print(f"cat: {args[0]}: No such file or directory")

        elif cmd == "echo":
            line_str = " ".join(args)
            if " > " in line_str:
                content, filename = line_str.split(" > ", 1)
                content = content.strip('"').strip("'")
                self.vfs.write_file(filename.strip(), content)
            else:
                print(line_str.strip('"').strip("'"))

        # Новые команды
        elif cmd == "touch":
            if not args:
                print("touch: missing file operand")
            else:
                for f in args:
                    res = self.vfs.touch(f)
                    if res: print(res)

        elif cmd == "mkdir":
            if not args:
                print("mkdir: missing operand")
            else:
                for d in args:
                    res = self.vfs.mkdir(d)
                    if res: print(res)

        elif cmd == "rm":
            if not args:
                print("rm: missing operand")
                return
            recursive = False
            if args[0] == "-r":
                recursive = True
                args = args[1:]
                if not args:
                    print("rm: missing operand")
                    return
            for item in args:
                res = self.vfs.rm(item, recursive)
                if res: print(res)

        elif cmd == "cp":
            if len(args) < 2:
                print("cp: missing file operand")
            else:
                src, dst = args[0], args[1]
                res = self.vfs.cp(src, dst)
                if res: print(res)

        elif cmd == "mv":
            if len(args) < 2:
                print("mv: missing file operand")
            else:
                src, dst = args[0], args[1]
                res = self.vfs.mv(src, dst)
                if res: print(res)

        elif cmd == "find":
            if not args:
                print("find: missing operand")
            else:
                name = args[0]
                results = self.vfs.find(name)
                if results:
                    print("\n".join(results))
                else:
                    print(f"find: '{name}' not found")

        elif cmd == "grep":
            if len(args) < 2:
                print("grep: missing pattern or file")
            else:
                pattern = args[0]
                filename = args[1]
                res = self.vfs.grep(pattern, filename)
                if res:
                    print(res)
                else:
                    print(f"grep: no matches in {filename}")

        elif cmd == "htop":
            if "htop" not in self.pkg.installed_apt:
                print("htop not installed. Run 'apt install htop'")
                return
            # Симуляция htop
            print("\033[2J\033[H", end="")  # очистка
            print("  PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND")
            for i in range(20):
                pid = random.randint(1000, 9999)
                user = random.choice(["root", "kali", "www-data"])
                mem = random.randint(1000, 50000)
                cpu = random.randint(0, 100)
                cmd = random.choice(["python3", "nano", "bash", "sshd", "nginx", "systemd"])
                print(f"{pid:6} {user:8} {random.randint(10,30):3} {random.randint(0,10):3} {mem:8} {mem:8} {random.randint(1000,5000):6} S {cpu:5} {random.randint(0,100):5} {random.random():6.2f} {cmd}")
            time.sleep(3)
            print("\nPress any key to exit htop...")
            input()

        elif cmd == "hostname":
            print(self.net_sec.hostname)

        elif cmd == "tree":
            if "tree" not in self.pkg.installed_apt:
                print("tree not installed. Run 'apt install tree'")
                return
            if args:
                res = self.vfs.tree(args[0])
            else:
                res = self.vfs.tree()
            print(res)

        elif cmd == "history":
            for i, line in enumerate(self.history, 1):
                print(f"{i:4}  {line}")

        elif cmd == "df":
            print(self.vfs.df())

        elif cmd == "free":
            print(self.vfs.free())

        elif cmd == "nano":
            if "nano" not in self.pkg.installed_apt:
                print("nano not installed. Run 'apt install nano'")
                return
            if not args:
                print("nano: missing file operand")
                return
            filename = args[0]
            existing = self.vfs.read_file(filename)
            if existing is None:
                existing = ""
            print(f"--- nano: editing {filename} (press Ctrl+X to save and exit) ---")
            print("Enter new content (finish with empty line):")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            content = "\n".join(lines)
            self.vfs.write_file(filename, content)
            print(f"Saved to {filename}")

        # Модули расширения
        elif cmd == "apt":
            print(self.pkg.apt_execute(args))
        elif cmd == "pip":
            print(self.pkg.pip_execute(args))
        elif cmd == "python3":
            if not args:
                print("Python 3.11.2 (default, Feb 12 2026)\nType 'exit' to leave interactive shell simulation (only files execution supported now).")
                return
            print(self.pkg.run_python_runtime(args[0], self.vfs))
        elif cmd == "ip":
            print(self.net_sec.ip_cmd(args))
        elif cmd == "ping":
            print(self.net_sec.ping_cmd(args))
        elif cmd == "macchanger":
            print(self.net_sec.macchanger_cmd(args))
        elif cmd == "nmap":
            print(self.net_sec.nmap_cmd(args))
        elif cmd == "hydra":
            print(self.net_sec.hydra_cmd(args, self.vfs))
        elif cmd == "git":
            files = list(self.vfs.get_node(self.vfs.current_path).keys())
            print(self.git.execute(args, files))
        else:
            print(f"bash: {cmd}: command not found")

    def run(self):
        self.boot()
        while self.running:
            self.process_input()

# =============================================================================
# ТОЧКА ВХОДА (START RUNTIME)
# =============================================================================
if __name__ == "__main__":
    kali_env = KaliOperatingSystem()
    kali_env.run()
