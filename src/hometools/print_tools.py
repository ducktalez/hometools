"""Terminal color helpers and text-diff highlighting."""

import difflib


class Colors:
    """ANSI escape codes for terminal coloring."""

    RESET = "\033[39m"
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"


def highlight_removed(old: str, new: str) -> str:
    """Mark parts removed from *old* compared to *new* in red."""
    matcher = difflib.SequenceMatcher(None, old, new)
    result = ""
    for op, i1, i2, _j1, _j2 in matcher.get_opcodes():
        if op == "equal":
            result += old[i1:i2]
        elif op in ("delete", "replace"):
            result += f"{Colors.RED}{old[i1:i2]}{Colors.ENDC}"
    return result


def color_demo_print():
    """Print a demo of all ANSI colors."""
    print(
        f"{Colors.RESET} RESET {Colors.HEADER} HEADER {Colors.OKBLUE} OKBLUE {Colors.OKGREEN} OKGREEN\n"
        f"{Colors.WARNING} WARNING {Colors.FAIL} FAIL {Colors.ENDC} ENDC {Colors.BOLD} BOLD "
        f"{Colors.UNDERLINE} UNDERLINE {Colors.BLACK} BLACK\n"
        f"{Colors.RED} RED {Colors.GREEN} GREEN {Colors.YELLOW} YELLOW {Colors.BLUE} BLUE "
        f"{Colors.MAGENTA} MAGENTA {Colors.CYAN} CYAN\n"
        f"{Colors.WHITE} WHITE {Colors.ENDC} ENDC {Colors.RESET} RESET"
    )
