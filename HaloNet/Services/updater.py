import subprocess
import sys
from time import sleep
import os

from win32con import DETACHED_PROCESS


def main(this_executable, python_executable, parent, *args):
    print("ran", this_executable)
    sleep(1.)
    print('open', python_executable, parent)
    with open("test.txt", 'w') as f:
        f.write(f"~ {python_executable, parent, args}\n")
    subprocess.Popen([python_executable, parent] + args, creationflags=DETACHED_PROCESS)
    # os.execv("C:/Python36/" + python_executable, [parent])
    print('stopped')



if __name__ == '__main__':
    main(*sys.argv)
