"""Utility methods."""

import re

from ruamel.yaml import YAML

yaml = YAML(typ="safe")


def get_language_family(language: str) -> str:
    """en_US -> en"""
    return re.split("[-_]", language, maxsplit=1)[0]
