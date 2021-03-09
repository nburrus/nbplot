# This file is part of nbplot. See LICENSE for details.

import logging
import string
import sys

# Extending string.Template to add the . to the idpattern
# expression and support ${input.xxx}
class StringTemplateWithDot(string.Template):
    idpattern = '(?a:[_a-z][._a-z0-9]*)'

class LoggingLevelContext(object):
    """Temporarily change the logging level"""
    def __init__(self, new_level):
        self.prev_level = logging.getLogger().level
        self.new_level = new_level

    def __enter__(self):
        logging.getLogger().setLevel(self.new_level)

    def __exit__(self, type, value, traceback):
        logging.getLogger().setLevel(self.prev_level)

class TermColor:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def ask_confirmation(msg):
    if not sys.stdin.isatty():
        return True
    return input(f"{TermColor.BOLD}{msg}? (Y/n) {TermColor.END}").lower() != 'n'
