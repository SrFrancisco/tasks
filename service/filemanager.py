from datetime import datetime
from multiprocessing import Lock
import subprocess
import os
import html
from consts import *
from .sanitizer import *

# Startup: read file
read_file = open(FILE_PATH + "/" + FILE_NAME, mode="r")
lines = read_file.readlines()
read_file.close()

# This prevents conflicts and modifications overriding
last_write = datetime.now()
write_lock = Lock()


class FileConflict(Exception):
    pass
class FileContentTooBig(Exception):
    pass


def do_backup():
    print("starting backup")

    if not ENABLE_GIT:
        return

    # check if the data directory has its own git repository so that it doesn't
    # commit the file to the source code repo
    if not os.path.exists(FILE_PATH + "/.git"):
        raise Exception("This is not a git repository")

    # fmt: off
    subprocess.run(['git -C '+FILE_PATH+' add todo.txt && git -C '+FILE_PATH+' commit -m "{}"'
                    .format(datetime.now().strftime("%d-%m-%Y-%H-%M"))] ,shell=True)
    if len(list(filter(None, subprocess.run(["git remote"],shell=True,capture_output=True)
                       .stdout.decode('UTF-8').split('\n')))) > 0:
        subprocess.run(['git -C '+FILE_PATH+' push'], shell=True)
    print("done")


def get_file_str() -> str:
    return "".join(lines)


def get_commit_hash() -> str:
    if not ENABLE_GIT or not os.path.exists(FILE_PATH + "/.git"):
        return ""
    result = subprocess.run(
        ["git -C " + FILE_PATH + ' log -1 --pretty=format:"%h %as"'],
        capture_output=True,
        shell=True,
    )
    return result.stdout.decode("UTF-8")


def write_file(new_content:str, last_seen_ts:float):
    last_seen_dt = datetime.fromtimestamp(last_seen_ts)

    with write_lock:
        global last_write, lines

        if last_seen_dt < last_write:
            raise FileConflict()
        elif last_seen_dt == last_write:  # we are in sync
            last_write = datetime.now()
        else:
            assert False, "This cannot happen" 

        if SANITIZE_JS:
            new_content = sanitize_html(new_content)
            new_content = html.unescape(new_content)  # nh3 does not offer the option of not escaping ">"  

        new_content_lst = [line + "\n" for line in new_content.splitlines()]

        if len(new_content_lst) > FILE_MAX_LINES:
            raise FileContentTooBig()
        
        with open(f"{FILE_PATH}/{FILE_NAME}", mode="w") as write_file:
            write_file.writelines(new_content_lst)
        
        lines = new_content_lst
        