
from pathlib import Path
import time


class BColors:
    RESET = '\033[39m'
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    BLACK2 = '\033[40m'
    RED2 = '\033[41m'

    OKBLUE_F = '\033[94m{}\033[39m'


# def color_str_gbr(txt, weights=None):
#     weights = weights or [0.85, 0.6, 0.3]
#     if



def color_demo_print():
    print('\033[39m RESET \033[95m HEADER \033[94m OKBLUE \033[92m OKGREEN \n'
          '\033[93m WARNING \033[91m FAIL \033[0m ENDC \033[1m BOLD \033[4m UNDERLINE \033[30m BLACK \n'
          '\033[31m RED \033[32m GREEN \033[33m YELLOW \033[34m BLUE \033[35m MAGENTA \033[36m CYAN \n'
          '\033[37m WHITE \033[40m BLACK2 \033[41m RED2 \033[0m ENDC \033[39m RESET')
