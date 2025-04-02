"""Test that sentences can be recognized in Home Assistant."""

import warnings
from pathlib import Path
from typing import Any, Dict, Optional, Set

import pytest
import yaml
from hassil import Intents, merge_dict, recognize_best
from home_assistant_intents import get_intents

from speech_to_phrase import Language, Things

from . import TEST_LANGUAGES
from .util import (
    SentenceToTest,
    ValueWithMetadata,
    coerce_list,
    generate_sentences,
    unpack_test_sentences,
)

_DIR = Path(__file__).parent
_PROGRAM_DIR = _DIR.parent
_MODULE_DIR = _PROGRAM_DIR / "speech_to_phrase"
_SENTENCES_DIR = _MODULE_DIR / "sentences"
_TESTS_DIR = _PROGRAM_DIR / "tests"
_TEST_SENTENCES_DIR = _TESTS_DIR / "sentences"
_EXAMPLE_SENTENCES_DIR = _TESTS_DIR / "example_sentences"


@pytest.fixture
def intent_slots() -> Dict[str, Any]:
    intents_path = _PROGRAM_DIR / "intents.yaml"
    with open(intents_path, "r", encoding="utf-8") as intents_file:
        return yaml.safe_load(intents_file)


@pytest.mark.parametrize("language", TEST_LANGUAGES)
def test_sentences_recognized(
    language: Language,
    intent_slots: Dict[str, Any],  # pylint: disable=redefined-outer-name
) -> None:
    lang_code = language.value

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

    # Load Home Assistant intents
    hass_intents_dict = get_intents(lang_code)
    assert (
        hass_intents_dict is not None
    ), f"No Home Assistant intents for language: '{lang_code}'"

    # Add test entities/areas/floors
    merge_dict(hass_intents_dict, test_things_lists_dict)
    hass_intents = Intents.from_dict(hass_intents_dict)

    for intent_name, intent_info in lang_intents.intents.items():
        assert (
            intent_name in intent_slots
        ), f"No expected slot combinations for intent: '{intent_name}'"
        known_slot_combos = intent_slots[intent_name]["slot_combinations"]
        test_intent_info = lang_test_intents_dict.get(intent_name, {})

        for intent_data in intent_info.data:
            # Check that test sentences can be recognized by Speech-to-Phrase
            assert (
                intent_data.metadata
            ), f"No metadata for sentence block of intent '{intent_name}' in {lang_sentences_path}: {intent_data.sentence_texts}"
            assert (
                "slot_combination" in intent_data.metadata
            ), f"No slot combination for in metadata for intent: '{intent_name}'"
            slot_combo_name = intent_data.metadata["slot_combination"]

            context_area = intent_data.metadata.get("context_area", False)
            assert (
                slot_combo_name in known_slot_combos
            ), f"Unknown slot combination for intent '{intent_name}': '{slot_combo_name}'"
            slot_combo_info = known_slot_combos[slot_combo_name]
            is_slot_combo_required = slot_combo_info.get("required", False)

            expected_domains: Optional[Set[str]] = None
            if "domain" in slot_combo_info:
                expected_domains = set(coerce_list(slot_combo_info["domain"]))

            actual_domains: Set[str] = set()

            if is_slot_combo_required:
                assert (
                    slot_combo_name in test_intent_info
                ), f"No tests for slot combination '{slot_combo_name}' of intent '{intent_name}'"
            elif slot_combo_name not in test_intent_info:
                warnings.warn(
                    UserWarning(
                        f"Missing tests for slot combination '{slot_combo_name}' of intent '{intent_name}'"
                    )
                )
                continue

            for test_sentence in unpack_test_sentences(
                test_intent_info[slot_combo_name], lang_test_format_values
            ):
                assert (
                    context_area == test_sentence.context_area
                ), "Test sentence context_area must match sentence template metadata"

                result = recognize_best(
                    test_sentence.text, lang_intents, best_slot_name="name"
                )
                assert (
                    result is not None
                ), f"Sentence not recognized with Speech-to-Phrase intents: '{test_sentence.text}'"
                assert result.intent.name == intent_name, test_sentence
                result_slots = {
                    e_name: e.value for e_name, e in result.entities.items()
                }

                assert result_slots == (test_sentence.slots or {}), test_sentence
                if expected_domains:
                    assert ("name" in result.entities) or ("domain" in result.entities)
                    if name_entity := result.entities.get("name"):
                        # Verify that matched entity has an expected domain.
                        # The domain is stored in the metadata in Things.to_lists_dict()
                        assert name_entity.metadata and (
                            "domain" in name_entity.metadata
                        )
                        entity_domain = name_entity.metadata["domain"]
                        assert entity_domain in expected_domains
                        actual_domains.add(entity_domain)
                    else:
                        # Verify that the domain was inferred from the sentence itself
                        actual_domains.add(result.entities["domain"].value)

            if expected_domains:
                assert (
                    actual_domains == expected_domains
                ), f"Missing tests for some domains in intent '{intent_name}' for slot combination: '{slot_combo_name}'"

            # Generate possible sentences and verify they can be recognized in Home Assistant
            for sentence in intent_data.sentences:
                possible_sentences = generate_sentences(
                    sentence.expression, lang_intents, intent_data, intent_data.slots
                )
                for gen_text, gen_slots in possible_sentences:
                    result = recognize_best(
                        gen_text,
                        hass_intents,
                        intent_context=({"area": "_"} if context_area else None),
                        best_slot_name="name",
                    )
                    assert (
                        result is not None
                    ), f"Sentence not recognized with Home Assistant intents: '{gen_text}'"
                    assert result.intent.name == intent_name, sentence.text
                    result_slots = {
                        e_name: e.value for e_name, e in result.entities.items()
                    }
                    if context_area:
                        # Don't match against real slots
                        result_slots.pop("area", None)

                    assert result_slots == {
                        k: v.value if isinstance(v, ValueWithMetadata) else v
                        for k, v in gen_slots.items()
                    }, gen_text


@pytest.mark.parametrize("language", TEST_LANGUAGES)
def test_sentences_tested(
    language: Language,
    intent_slots: Dict[str, Any],  # pylint: disable=redefined-outer-name
) -> None:
    lang_code = language.value

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

    for intent_name, intent_info in lang_intents.intents.items():
        known_slot_combos = intent_slots[intent_name]["slot_combinations"]
        test_intent_info = lang_test_intents_dict.get(intent_name, {})
        for intent_data in intent_info.data:
            assert (
                intent_data.metadata
            ), f"No metadata for sentence block of intent '{intent_name}' in {lang_sentences_path}: {intent_data.sentence_texts}"
            slot_combo_name = intent_data.metadata["slot_combination"]
            assert (
                slot_combo_name in known_slot_combos
            ), f"Unknown slot combination for intent '{intent_name}': '{slot_combo_name}'"
            slot_combo_info = known_slot_combos[slot_combo_name]
            is_slot_combo_required = slot_combo_info.get("required", False)

            if is_slot_combo_required:
                assert (
                    slot_combo_name in test_intent_info
                ), f"No tests for slot combination of intent '{intent_name}': {slot_combo_name}"
            elif slot_combo_name not in test_intent_info:
                warnings.warn(
                    UserWarning(
                        f"Missing tests for slot combination '{slot_combo_name}' of intent '{intent_name}'"
                    )
                )
                continue

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
                    assert (
                        test_sentence
                    ), f"No test for sentence in intent '{intent_name}' for slot combination '{slot_combo_name}': {possible_text}"

                    test_slots = test_sentence.slots or {}
                    for slot_key, slot_value in possible_slots.items():
                        assert (
                            slot_key in test_slots
                        ), f"Missing {slot_key} for {possible_text}"
                        assert test_slots[slot_key] == slot_value.value, possible_text
