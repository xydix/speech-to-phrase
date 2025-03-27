"""Generate JSON with example sentences and their corresponding intents."""

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from hassil import Intents, merge_dict

from speech_to_phrase import Things

from .util import SentenceToTest, generate_sentences, unpack_test_sentences

_DIR = Path(__file__).parent
_PROGRAM_DIR = _DIR.parent
_MODULE_DIR = _PROGRAM_DIR / "speech_to_phrase"
_SENTENCES_DIR = _MODULE_DIR / "sentences"
_TESTS_DIR = _PROGRAM_DIR / "tests"
_TEST_SENTENCES_DIR = _TESTS_DIR / "sentences"
_EXAMPLE_SENTENCES_DIR = _TESTS_DIR / "example_sentences"

_LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    lang_code = args.language

    # Load tests for language
    lang_test_sentences_path = _TEST_SENTENCES_DIR / f"{lang_code}.yaml"
    with open(
        lang_test_sentences_path, "r", encoding="utf-8"
    ) as lang_test_sentences_file:
        lang_test_sentences_dict = yaml.safe_load(lang_test_sentences_file)

    lang_test_intents_dict = lang_test_sentences_dict["tests"]
    lang_test_format_values = lang_test_sentences_dict.get("test_format_values", {})

    test_things = Things.from_dict(lang_test_sentences_dict)
    test_things_lists_dict = {"lists": test_things.to_lists_dict()}

    # Add wildcard values
    test_wildcard_lists = {
        "lists": {
            list_name: {"wildcard": False, "values": list_values}
            for list_name, list_values in lang_test_sentences_dict.get(
                "test_wildcard_values", {}
            ).items()
        }
    }
    merge_dict(test_things_lists_dict, test_wildcard_lists)

    # Load Speech-to-Phrase intents
    lang_sentences_path = _SENTENCES_DIR / f"{lang_code}.yaml"
    with open(lang_sentences_path, "r", encoding="utf-8") as lang_sentences_file:
        lang_sentences_dict = yaml.safe_load(lang_sentences_file)

    # Add test entities/areas/floors
    merge_dict(lang_sentences_dict, test_things_lists_dict)
    lang_intents = Intents.from_dict(lang_sentences_dict)

    example_sentences_path = _EXAMPLE_SENTENCES_DIR / f"{lang_code}.json"
    example_sentences_path.parent.mkdir(parents=True, exist_ok=True)

    example_sentences_dict: Dict[str, Any] = {}
    for intent_name, intent_info in lang_intents.intents.items():
        test_intent_info = lang_test_intents_dict[intent_name]
        for intent_data in intent_info.data:
            assert intent_data.metadata, f"No metadata for intent: '{intent_name}'"
            slot_combo_name = intent_data.metadata["slot_combination"]
            assert (
                slot_combo_name in test_intent_info
            ), f"No tests for slot combination of intent '{intent_name}': {slot_combo_name}"

            actual_test_sentences: Dict[str, SentenceToTest] = {
                ts.text: ts
                for ts in unpack_test_sentences(
                    test_intent_info[slot_combo_name], lang_test_format_values
                )
            }

            # Generate test sentences and verify they are present
            for sentence in intent_data.sentences:
                possible_sentences = generate_sentences(
                    sentence.expression,
                    lang_intents,
                    intent_data,
                    {},
                    skip_optionals=True,
                )
                for possible_text, possible_slots in possible_sentences:
                    possible_text = possible_text.strip()
                    test_sentence = actual_test_sentences.get(possible_text)
                    assert test_sentence, f"Missing test sentence: {possible_text}"

                    test_slots = test_sentence.slots or {}
                    example_domain: Optional[str] = None
                    for slot_key, slot_value in possible_slots.items():
                        assert (
                            slot_key in test_slots
                        ), f"Missing {slot_key} for {possible_text}"
                        assert test_slots[slot_key] == slot_value.value, possible_text

                        if slot_value.metadata:
                            example_domain = slot_value.metadata.get(
                                "domain", example_domain
                            )

                    if (not example_domain) and ("domain" in test_slots):
                        example_domain = test_slots["domain"]

                    example = {
                        "intent": intent_name,
                        "slots": test_slots,
                        "context_area": intent_data.metadata.get("context_area", False),
                        "slot_combination": slot_combo_name,
                    }

                    if example_domain:
                        example["domain"] = example_domain

                    example_sentences_dict[possible_text] = example

    with open(example_sentences_path, "w", encoding="utf-8") as example_sentences_file:
        json.dump(
            {k: example_sentences_dict[k] for k in sorted(example_sentences_dict)},
            example_sentences_file,
            ensure_ascii=False,
            indent=2,
        )

    _LOGGER.info("Wrote %s", example_sentences_path)


if __name__ == "__main__":
    main()
