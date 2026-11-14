from datetime import datetime
from multiprocessing import Lock
import subprocess
import os
import html
import traceback
from typing import Callable
from consts import *
from .caldav import process_notification_lines
from .sanitizer import *

class FileConflict(Exception):
    pass
class FileContentTooBig(Exception):
    pass
class CalendarNotificationFailure(Exception):
    pass

class TaskList:
    def __init__(self, file_name, profile_name) -> None:
        self.file_path:str = FILE_PATH + "/" + file_name
        if not os.path.isfile(self.file_path):
            print("!!! file does not exist, creating and empty one!")
            open(self.file_path, "a").close()

        with open(self.file_path, "r") as fd:
            self.lines:list[str] = fd.readlines()

        self.name:str = profile_name
        self.last_write:datetime = datetime.now()

    def get_file_str(self) -> str:
        return "".join(self.lines)

    def write_file(self, new_content:str, last_seen_ts:float) -> bool:
        last_seen_dt = datetime.fromtimestamp(last_seen_ts)
        global write_lock

        with write_lock:
            if last_seen_dt < self.last_write:
                raise FileConflict()
            elif last_seen_dt == self.last_write:  # we are in sync
                pass # we only append at the end to guard for exceptions
            else:
                assert False, "This cannot happen"

            if SANITIZE_JS:
                new_content = sanitize_html(new_content)
                new_content = html.unescape(new_content)  # nh3 does not offer the option of not escaping ">"

            new_content_lst = [line + "\n" for line in new_content.splitlines()]

            if len(new_content_lst) > FILE_MAX_LINES:
                raise FileContentTooBig()

            try:
                updated_lines = process_notification_lines(new_content_lst)
            except Exception as exc:
                print("Err", exc)
                traceback.print_exc()
                raise CalendarNotificationFailure(
                    "CalDAV notification processing failed"
                ) from exc

            with open(self.file_path, mode="w") as write_file:
                write_file.writelines(updated_lines)

            refresh_working_copy = updated_lines != new_content_lst
            self.last_write = datetime.now()
            self.lines = updated_lines
            return refresh_working_copy

    def write(self, new_content: list[str]):
        global write_lock
        with write_lock:
            write_file = open(self.file_path, mode="w")
            write_file.writelines(new_content)
            write_file.close()

            self.lines = new_content
            self.last_write = datetime.now()

    def do_in_txn(self, fn: Callable[[list[str]], list[str]]):
        def _write(new_content:list[str]):
            write_file = open(self.file_path, mode="w")
            write_file.writelines(new_content)
            write_file.close()
            self.lines = new_content
            self.last_write = datetime.now()

        global write_lock
        with write_lock:
            _write(fn(self.lines))




# Startup: read files
profiles = dict()
for prof in PROFILES:
    profiles[prof['profile_name']] = TaskList(prof['file'], prof['profile_name'])

# This prevents conflicts and modifications overriding
write_lock = Lock()

def get_profiles() -> list[str]:
    return list(profiles.keys())

def get_profile_or_default(key:str|None) -> TaskList :
    return profiles.get(key) or get_default_profile()

def get_profile(key:str) -> TaskList :
    return profiles[key]

def get_default_profile() -> TaskList:
    return profiles[DEFAULT_PROFILE_RULE(PROFILES)]


# ---------------------------------
# Git Operations
# ---------------------------------

def do_backup():
    print("starting backup")

    if not ENABLE_GIT:
        return

    with write_lock:
        # check if the data directory has its own git repository so that it doesn't
        # commit the file to the source code repo
        if not os.path.exists(FILE_PATH + "/.git"):
            raise Exception("This is not a git repository")

        # fmt: off
        subprocess.run(['git -C '+FILE_PATH+f' add {' '.join([p['file'] for p in PROFILES])} && git -C '+FILE_PATH+' commit -m "{}"'
                        .format(datetime.now().strftime("%d-%m-%Y-%H-%M"))] ,shell=True)
        if len(list(filter(None, subprocess.run(["git -C "+FILE_PATH+" remote"],shell=True,capture_output=True)
                        .stdout.decode('UTF-8').split('\n')))) > 0:
            subprocess.run(['git -C '+FILE_PATH+' push'], shell=True)
    print("done")

def get_commit_hash() -> str:
    if not ENABLE_GIT or not os.path.exists(FILE_PATH + "/.git"):
        return ""
    result = subprocess.run(
        ["git -C " + FILE_PATH + ' log -1 --pretty=format:"%h %as"'],
        capture_output=True,
        shell=True,
    )
    return result.stdout.decode("UTF-8")
