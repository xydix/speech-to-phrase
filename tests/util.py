"""Test utilities."""

import itertools
from collections.abc import Iterable
from dataclasses import dataclass
from functools import partial
from typing import Any, Dict, List, Optional, Tuple, Union

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
    normalize_whitespace,
)


@dataclass
class SentenceToTest:
    """Text and metadata for a test sentence."""

    text: str
    slots: Optional[Dict[str, Any]] = None
    context_area: bool = False


@dataclass
class ValueWithMetadata:
    """Slot value with optional metadata."""

    value: Any
    metadata: Optional[Dict[str, Any]] = None


def generate_sentences(
    e: Expression,
    intents: Intents,
    intent_data: IntentData,
    slots: Dict[str, Any],
    skip_optionals: bool = False,
) -> Iterable[Tuple[str, Dict[str, ValueWithMetadata]]]:
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
                    {
                        list_ref.slot_name: ValueWithMetadata(
                            text_value.value_out, text_value.metadata
                        )
                    },
                    skip_optionals,
                )
        elif isinstance(slot_list, RangeSlotList):
            range_list: RangeSlotList = slot_list

            yield str(range_list.start), {
                **slots,
                list_ref.slot_name: ValueWithMetadata(range_list.start),
            }

            # Also generate second value to test the step size.
            # If this value is past the end of the range, skip it.
            second_value = range_list.start + range_list.step
            if second_value < range_list.stop:
                yield str(second_value), {
                    **slots,
                    list_ref.slot_name: ValueWithMetadata(second_value),
                }

            if range_list.stop > range_list.start:
                yield str(range_list.stop), {
                    **slots,
                    list_ref.slot_name: ValueWithMetadata(range_list.stop),
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


def coerce_list(str_or_list: Union[str, List[str]]) -> List[str]:
    if isinstance(str_or_list, str):
        return [str_or_list]

    return str_or_list


def get_format_values(
    values: List[Union[str, Dict[str, str]]]
) -> List[Tuple[str, str]]:
    values_in_out: List[Tuple[str, str]] = []

    for str_or_dict in values:
        if isinstance(str_or_dict, str):
            values_in_out.append((str_or_dict, str_or_dict))
        else:
            values_in_out.append((str_or_dict["in"], str_or_dict["out"]))

    return values_in_out


def unpack_test_sentences(
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
                            get_format_values(test_format_values[values_key])
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
