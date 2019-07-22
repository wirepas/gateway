"""
    __MAIN__
    ========

    Package main file

    .. Copyright:
        Copyright 2019 Wirepas Ltd licensed under Apache License, Version 2.0
        See file LICENSE for full license details.
"""

from wirepas_gateway.transport_service import main as main_transport


def main():
    main_transport()


if __name__ == "__main__":
    main()
