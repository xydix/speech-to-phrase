"""Utility methods."""

import re


def get_language_family(language: str) -> str:
    """en_US -> en"""
    return re.split("[-_]", language, maxsplit=1)[0]
