"""Test that sentences can be recognized in Home Assistant."""

import itertools
import sys
from collections.abc import Iterable
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import pytest
import voluptuous as vol
import yaml
from hassil import (
    Alternative,
    Expression,
    Group,
    IntentData,
    Intents,
    ListReference,
    Permutation,
    RangeSlotList,
    RuleReference,
    Sequence,
    TextChunk,
    TextSlotList,
    merge_dict,
    normalize_whitespace,
    parse_sentence,
    recognize,
)
from home_assistant_intents import get_intents

from speech_to_phrase import Language, Things

_DIR = Path(__file__).parent
_PROGRAM_DIR = _DIR.parent
_MODULE_DIR = _PROGRAM_DIR / "speech_to_phrase"
_SENTENCES_DIR = _MODULE_DIR / "sentences"
_TESTS_DIR = _PROGRAM_DIR / "tests"
_TEST_SENTENCES_DIR = _TESTS_DIR / "sentences"


def generate_sentences(
    e: Expression,
    intents: Intents,
    intent_data: IntentData,
    slots: Dict[str, Any],
) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """Generate possible text strings and slot values from an expression."""
    if isinstance(e, TextChunk):
        chunk: TextChunk = e
        yield (chunk.original_text, slots)
    elif isinstance(e, Group):
        grp: Group = e
        if isinstance(grp, Alternative):
            for item in grp.items:
                yield from generate_sentences(item, intents, intent_data, slots)
        elif isinstance(grp, Sequence):
            seq_sentences = map(
                partial(
                    generate_sentences,
                    intents=intents,
                    intent_data=intent_data,
                    slots=slots,
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
                yield from generate_sentences(
                    text_value.text_in,
                    intents,
                    intent_data,
                    {list_ref.slot_name: text_value.value_out},
                )
        elif isinstance(slot_list, RangeSlotList):
            range_list: RangeSlotList = slot_list

            yield TextChunk(str(range_list.start)), {
                **slots,
                list_ref.slot_name: range_list.start,
            }
            yield TextChunk(str(range_list.stop)), {
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

        yield from generate_sentences(rule_body.expression, intents, intent_data, slots)
    else:
        raise ValueError(f"Unexpected expression: {e}")


def generate_test_sentences(
    e: Expression,
    intents: Intents,
    intent_data: IntentData,
) -> Iterable[Optional[str]]:
    """Generate possible text strings from an expression."""
    if isinstance(e, TextChunk):
        chunk: TextChunk = e
        yield chunk.original_text
    elif isinstance(e, Group):
        grp: Group = e
        if isinstance(grp, Alternative):
            alt: Alternative = e
            # Skip optionals
            if alt.is_optional:
                yield ""
            else:
                for item in grp.items:
                    yield from generate_test_sentences(item, intents, intent_data)
        elif isinstance(grp, Sequence):
            seq_sentences = map(
                partial(
                    generate_test_sentences,
                    intents=intents,
                    intent_data=intent_data,
                ),
                grp.items,
            )
            for sentence_text in itertools.product(*seq_sentences):
                yield normalize_whitespace("".join(sentence_text))
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
                yield from generate_test_sentences(
                    text_value.text_in, intents, intent_data
                )
        elif isinstance(slot_list, RangeSlotList):
            range_list: RangeSlotList = slot_list

            yield TextChunk(str(range_list.start))
            yield TextChunk(str(range_list.stop))
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

        yield from generate_test_sentences(rule_body.expression, intents, intent_data)
    else:
        raise ValueError(f"Unexpected expression: {e}")


def _coerce_list(str_or_list: Union[str, List[str]]) -> List[str]:
    if isinstance(str_or_list, str):
        return [str_or_list]

    return str_or_list


@pytest.fixture
def intent_slots() -> Dict[str, Any]:
    intents_path = _PROGRAM_DIR / "intents.yaml"
    with open(intents_path, "r", encoding="utf-8") as intents_file:
        return yaml.safe_load(intents_file)


@pytest.mark.parametrize("language", (Language.ENGLISH,))
def test_sentences_recognized(language: Language, intent_slots) -> None:
    lang_code = language.value

    # Load tests for language
    lang_test_sentences_path = _TEST_SENTENCES_DIR / f"{lang_code}.yaml"
    with open(
        lang_test_sentences_path, "r", encoding="utf-8"
    ) as lang_test_sentences_file:
        lang_test_sentences_dict = yaml.safe_load(lang_test_sentences_file)

    lang_test_intents_dict = lang_test_sentences_dict["tests"]

    test_things = Things.from_dict(lang_test_sentences_dict)
    test_things_lists_dict = {"lists": test_things.to_lists_dict()}

    # Load Speech-to-Phrase intents
    lang_sentences_path = _SENTENCES_DIR / f"{lang_code}.yaml"
    with open(lang_sentences_path, "r", encoding="utf-8") as lang_sentences_file:
        lang_sentences_dict = yaml.safe_load(lang_sentences_file)

    # Add test entities/areas/floors
    merge_dict(lang_sentences_dict, test_things_lists_dict)
    lang_intents = Intents.from_dict(lang_sentences_dict)

    assert (
        lang_intents.intents.keys() == lang_test_intents_dict.keys()
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
            slot_combo_name = intent_data.metadata["slot_combination"]
            assert (
                slot_combo_name in possible_slot_combos
            ), f"No expected slot combination for intent '{intent_name}': '{slot_combo_name}'"
            slot_combo_info = possible_slot_combos[slot_combo_name]
            expected_slot_names = set(_coerce_list(slot_combo_info["slots"]))

            expected_domains: Optional[Set[str]] = None
            if "domain" in slot_combo_info:
                expected_domains = set(_coerce_list(slot_combo_info["domain"]))

            assert (
                slot_combo_name in test_intent_info
            ), f"No tests for slot combination '{slot_combo_name}' of intent '{intent_name}'"

            for sentence_text in test_intent_info[slot_combo_name]:
                result = recognize(sentence_text, lang_intents)
                assert (
                    result is not None
                ), f"Sentence not recognized with Speech-to-Phrase intents: '{sentence_text}'"
                assert result.entities.keys() == expected_slot_names
                if expected_domains:
                    # Verify that matched entity has an expected domain.
                    # The domain is stored in the metadata in Things.to_lists_dict()
                    assert "name" in result.entities
                    name_entity = result.entities["name"]
                    assert name_entity.metadata and ("domain" in name_entity.metadata)
                    assert name_entity.metadata["domain"] in expected_domains

            # Generate possible sentences and verify they can be recognized in Home Assistant
            for sentence in intent_data.sentences:
                possible_sentences = generate_sentences(
                    sentence.expression, lang_intents, intent_data, {}
                )
                for gen_text, gen_slots in possible_sentences:
                    result = recognize(gen_text, hass_intents)
                    assert (
                        result is not None
                    ), f"Sentence not recognized with Home Assistant intents: '{gen_text}'"
                    assert result.intent.name == intent_name
                    result_slots = {
                        e_name: e.value for e_name, e in result.entities.items()
                    }
                    assert result_slots == gen_slots


@pytest.mark.parametrize("language", (Language.ENGLISH,))
def test_sentences_tested(language: Language, intent_slots) -> None:
    lang_code = language.value

    # Load tests for language
    lang_test_sentences_path = _TEST_SENTENCES_DIR / f"{lang_code}.yaml"
    with open(
        lang_test_sentences_path, "r", encoding="utf-8"
    ) as lang_test_sentences_file:
        lang_test_sentences_dict = yaml.safe_load(lang_test_sentences_file)

    lang_test_intents_dict = lang_test_sentences_dict["tests"]

    test_things = Things.from_dict(lang_test_sentences_dict)
    test_things_lists_dict = {"lists": test_things.to_lists_dict()}

    # Load Speech-to-Phrase intents
    lang_sentences_path = _SENTENCES_DIR / f"{lang_code}.yaml"
    with open(lang_sentences_path, "r", encoding="utf-8") as lang_sentences_file:
        lang_sentences_dict = yaml.safe_load(lang_sentences_file)

    # Add test entities/areas/floors
    merge_dict(lang_sentences_dict, test_things_lists_dict)
    lang_intents = Intents.from_dict(lang_sentences_dict)

    for intent_name, intent_info in lang_intents.intents.items():
        test_intent_info = lang_test_intents_dict[intent_name]
        for intent_data in intent_info.data:
            slot_combo_name = intent_data.metadata["slot_combination"]
            actual_test_sentences = set(test_intent_info[slot_combo_name])

            # Generate test sentences and verify they are present
            expected_test_sentences: Set[str] = set()
            for sentence in intent_data.sentences:
                possible_sentences = generate_test_sentences(
                    sentence.expression, lang_intents, intent_data
                )
                expected_test_sentences.update(s.strip() for s in possible_sentences)

            assert expected_test_sentences == actual_test_sentences
