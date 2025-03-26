"""Test that sentences can be recognized in Home Assistant."""

import itertools
import json
from collections.abc import Iterable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import pytest
import yaml
from hassil import (
    Alternative,
    Expression,
    Group,
    IntentData,
    Intents,
    ListReference,
    RangeSlotList,
    RuleReference,
    Sequence,
    TextChunk,
    TextSlotList,
    check_excluded_context,
    check_required_context,
    merge_dict,
    normalize_whitespace,
    recognize_best,
)
from home_assistant_intents import get_intents

from speech_to_phrase import Language, Things

_DIR = Path(__file__).parent
_PROGRAM_DIR = _DIR.parent
_MODULE_DIR = _PROGRAM_DIR / "speech_to_phrase"
_SENTENCES_DIR = _MODULE_DIR / "sentences"
_TESTS_DIR = _PROGRAM_DIR / "tests"
_TEST_SENTENCES_DIR = _TESTS_DIR / "sentences"
_EXAMPLE_SENTENCES_DIR = _TESTS_DIR / "example_sentences"


@dataclass
class SentenceToTest:
    text: str
    slots: Optional[Dict[str, Any]] = None
    context_area: bool = False


def generate_sentences(
    e: Expression,
    intents: Intents,
    intent_data: IntentData,
    slots: Dict[str, Any],
    skip_optionals: bool = False,
) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """Generate possible text strings and slot values from an expression."""
    if isinstance(e, TextChunk):
        chunk: TextChunk = e
        yield (chunk.original_text, slots)
    elif isinstance(e, Group):
        grp: Group = e
        if isinstance(grp, Alternative):
            alt: Alternative = grp
            if alt.is_optional:
                yield ("", slots)
            else:
                for item in grp.items:
                    yield from generate_sentences(
                        item, intents, intent_data, slots, skip_optionals
                    )
        elif isinstance(grp, Sequence):
            seq_sentences = map(
                partial(
                    generate_sentences,
                    intents=intents,
                    intent_data=intent_data,
                    slots=slots,
                    skip_optionals=skip_optionals,
                ),
                grp.items,
            )
            sentence_combos = itertools.product(*seq_sentences)
            for sentence_combo in sentence_combos:
                combo_words, combo_slots = zip(*sentence_combo)
                combined_slots = dict(slots)
                for partial_slots in combo_slots:
                    combined_slots.update(partial_slots)

                yield normalize_whitespace("".join(combo_words)), combined_slots
        else:
            raise ValueError(f"Unexpected group type: {grp}")
    elif isinstance(e, ListReference):
        # {list}
        list_ref: ListReference = e

        slot_list = intent_data.slot_lists.get(list_ref.list_name)
        if slot_list is None:
            slot_list = intents.slot_lists.get(list_ref.list_name)

        if slot_list is None:
            raise ValueError(f"Missing slot list: {list_ref.list_name}")

        if isinstance(slot_list, TextSlotList):
            text_list: TextSlotList = slot_list

            for text_value in text_list.values:
                if intent_data.requires_context and (
                    not check_required_context(
                        intent_data.requires_context,
                        text_value.context,
                        allow_missing_keys=True,
                    )
                ):
                    continue

                if intent_data.excludes_context and (
                    not check_excluded_context(
                        intent_data.excludes_context, text_value.context
                    )
                ):
                    continue

                yield from generate_sentences(
                    text_value.text_in,
                    intents,
                    intent_data,
                    {list_ref.slot_name: text_value.value_out},
                    skip_optionals,
                )
        elif isinstance(slot_list, RangeSlotList):
            range_list: RangeSlotList = slot_list

            yield str(range_list.start), {
                **slots,
                list_ref.slot_name: range_list.start,
            }
            yield str(range_list.stop), {
                **slots,
                list_ref.slot_name: range_list.stop,
            }
        else:
            raise ValueError(f"Unexpected slot list type: {slot_list}")
    elif isinstance(e, RuleReference):
        # <rule>
        rule_ref: RuleReference = e
        rule_body = intent_data.expansion_rules.get(rule_ref.rule_name)
        if rule_body is None:
            rule_body = intents.expansion_rules.get(rule_ref.rule_name)

        if rule_body is None:
            raise ValueError(f"Missing expansion rule: {rule_ref.rule_name}")

        yield from generate_sentences(
            rule_body.expression, intents, intent_data, slots, skip_optionals
        )
    else:
        raise ValueError(f"Unexpected expression: {e}")


def _coerce_list(str_or_list: Union[str, List[str]]) -> List[str]:
    if isinstance(str_or_list, str):
        return [str_or_list]

    return str_or_list


def _get_format_values(
    values: List[Union[str, Dict[str, str]]]
) -> List[Tuple[str, str]]:
    values_in_out: List[Tuple[str, str]] = []

    for str_or_dict in values:
        if isinstance(str_or_dict, str):
            values_in_out.append((str_or_dict, str_or_dict))
        else:
            values_in_out.append((str_or_dict["in"], str_or_dict["out"]))

    return values_in_out


def _unpack_test_sentences(
    test_sentences: List[Union[str, Dict[str, Any]]],
    test_format_values: Dict[str, List[Union[str, Dict[str, str]]]],
) -> Iterable[SentenceToTest]:
    for str_or_dict in test_sentences:
        if isinstance(str_or_dict, str):
            yield SentenceToTest(str_or_dict)
        else:
            str_or_list = str_or_dict["sentences"]
            test_slots = str_or_dict.get("slots", {})
            test_context_area = str_or_dict.get("context_area", False)
            uses_format_values = str_or_dict.get("uses_format_values")

            if isinstance(str_or_list, str):
                sentence_list = [str_or_list]
            else:
                sentence_list = str_or_list

            if isinstance(uses_format_values, str):
                uses_format_values = [uses_format_values]

            if uses_format_values:
                # Requires formatting test sentences/slots
                for test_sentence_text in sentence_list:
                    for format_value_combo in itertools.product(
                        *(
                            _get_format_values(test_format_values[values_key])
                            for values_key in uses_format_values
                        )
                    ):
                        format_args_in = dict(
                            zip(uses_format_values, (v[0] for v in format_value_combo))
                        )
                        format_args_out = dict(
                            zip(uses_format_values, (v[1] for v in format_value_combo))
                        )
                        formatted_text = test_sentence_text.format(**format_args_in)
                        formatted_slots = {
                            slot_key: (
                                slot_value.format(**format_args_out)
                                if isinstance(slot_value, str)
                                else slot_value
                            )
                            for slot_key, slot_value in test_slots.items()
                        }
                        yield SentenceToTest(
                            formatted_text, formatted_slots, test_context_area
                        )

            else:
                # No format values
                for test_sentence_text in sentence_list:
                    yield SentenceToTest(
                        test_sentence_text, test_slots, test_context_area
                    )


@pytest.fixture
def intent_slots() -> Dict[str, Any]:
    intents_path = _PROGRAM_DIR / "intents.yaml"
    with open(intents_path, "r", encoding="utf-8") as intents_file:
        return yaml.safe_load(intents_file)


@pytest.mark.parametrize("language", (Language.ENGLISH,))
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

    assert set(intent_slots.keys()) == set(
        lang_test_intents_dict.keys()
    ), "Tests and known intents must match"

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

    assert set(lang_intents.intents.keys()) == set(
        lang_test_intents_dict.keys()
    ), "Tests and supported intents must match"

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
        possible_slot_combos = intent_slots[intent_name]["slot_combinations"]

        assert (
            intent_name in lang_test_intents_dict
        ), f"No tests for intent: '{intent_name}'"
        test_intent_info = lang_test_intents_dict[intent_name]

        for intent_data in intent_info.data:
            # Check that test sentences can be recognized by Speech-to-Phrase
            assert intent_data.metadata, f"No metadata for intent: '{intent_name}'"
            assert (
                "slot_combination" in intent_data.metadata
            ), f"No slot combination for in metadata for intent: '{intent_name}'"
            slot_combo_name = intent_data.metadata["slot_combination"]

            context_area = intent_data.metadata.get("context_area", False)
            assert (
                slot_combo_name in possible_slot_combos
            ), f"No expected slot combination for intent '{intent_name}': '{slot_combo_name}'"
            slot_combo_info = possible_slot_combos[slot_combo_name]

            expected_domains: Optional[Set[str]] = None
            if "domain" in slot_combo_info:
                expected_domains = set(_coerce_list(slot_combo_info["domain"]))

            actual_domains: Set[str] = set()

            assert (
                slot_combo_name in test_intent_info
            ), f"No tests for slot combination '{slot_combo_name}' of intent '{intent_name}'"

            for test_sentence in _unpack_test_sentences(
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

                    assert result_slots == gen_slots, gen_text


@pytest.mark.parametrize("language", (Language.ENGLISH,))
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

    example_sentences_path = _EXAMPLE_SENTENCES_DIR / f"{lang_code}.json"
    example_sentences_path.parent.mkdir(parents=True, exist_ok=True)

    example_sentences_dict: dict[str, Any] = {}
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
                for ts in _unpack_test_sentences(
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
                    for slot_key, slot_value in possible_slots.items():
                        assert (
                            slot_key in test_slots
                        ), f"Missing {slot_key} for {possible_text}"
                        assert test_slots[slot_key] == slot_value, possible_text

                    example_sentences_dict[possible_text] = {
                        "intent": intent_name,
                        "slots": test_slots,
                        "context_area": intent_data.metadata.get("context_area", False),
                    }

    with open(example_sentences_path, "w", encoding="utf-8") as example_sentences_file:
        json.dump(
            example_sentences_dict, example_sentences_file, ensure_ascii=False, indent=2
        )
