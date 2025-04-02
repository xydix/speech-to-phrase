"""Tests."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from speech_to_phrase import Language, Settings, Things

TESTS_DIR = Path(__file__).parent
ROOT_DIR = TESTS_DIR.parent

LOCAL_DIR = ROOT_DIR / "local"
SETTINGS = Settings(
    models_dir=LOCAL_DIR / "models",
    train_dir=TESTS_DIR / "train",
    tools_dir=LOCAL_DIR,
    hass_token="",
    hass_websocket_uri="",
    retrain_on_connect=False,
    custom_sentences_dirs=[TESTS_DIR / "custom_sentences"],
)

TEST_LANGUAGES = [Language.ENGLISH]


def get_test_things(language: str) -> Things:
    lang_test_sentences_path = TESTS_DIR / "sentences" / f"{language}.yaml"
    with open(
        lang_test_sentences_path, "r", encoding="utf-8"
    ) as lang_test_sentences_file:
        lang_test_sentences_dict = yaml.safe_load(lang_test_sentences_file)

    return Things.from_dict(lang_test_sentences_dict)


def load_test_sentences(language: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Load test sentences for a language."""
    example_sentences_path = TESTS_DIR / "example_sentences" / f"{language}.json"
    with open(example_sentences_path, "r", encoding="utf-8") as example_sentences_file:
        example_sentences_dict = json.load(example_sentences_file)
        return example_sentences_dict.items()
