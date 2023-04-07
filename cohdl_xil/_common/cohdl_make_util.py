import os
import sys
import shutil


def path_exists(path):
    if os.path.exists(path):
        return 0
    return 1


def remove_old(source, target, *to_delete):
    if not os.path.exists(target):
        return 0

    if os.path.getmtime(source) > os.path.getmtime(target):
        for path in to_delete:
            shutil.rmtree(path)
    return 0


def run_command():
    path, cmd, *args = sys.argv

    print(sys.argv)

    if cmd == "remove_old":
        return remove_old(*args)
    if cmd == "file_exists":
        return path_exists(*args)


if __name__ == "__main__":
    exit(run_command())
