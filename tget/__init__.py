"""
Copyright (c) 2016-2020 we-get developers (https://github.com/rachmadaniHaryono/we-get/)
See the file 'LICENSE' for copying permission
"""

from tget.core.we_get import WG
from tget.core.utils import msg_error


def main():
    we_get = WG()
    we_get.parse_arguments()
    try:
        we_get.start()
    except (EOFError, KeyboardInterrupt):
        msg_error("[KeyboardInterrupt]", True)
