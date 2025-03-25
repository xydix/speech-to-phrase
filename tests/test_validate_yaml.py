"""Validate sentence YAML files."""

from pathlib import Path
from typing import Any

import pytest
import voluptuous as vol
import yaml
from hassil import (
    Alternative,
    Expression,
    Group,
    ListReference,
    RuleReference,
    parse_sentence,
)
from voluptuous.humanize import validate_with_humanized_errors

from speech_to_phrase import Language

_TESTS_DIR = Path(__file__).parent
_PROGRAM_DIR = _TESTS_DIR.parent
_MODULE_DIR = _PROGRAM_DIR / "speech_to_phrase"
_SENTENCES_DIR = _MODULE_DIR / "sentences"
_TEST_SENTENCES_DIR = _TESTS_DIR / "sentences"


def _visit_expression(e: Expression, visitor, visitor_arg: Any):
    result = visitor(e, visitor_arg)
    if isinstance(e, Group):
        grp: Group = e
        for item in grp.items:
            _visit_expression(item, visitor, result)


def no_list_or_rule_references(sentence: str):
    """Validator that doesn't allow for {list} or <rule> references in a sentence template."""

    def visitor(e: Expression, arg: Any):
        if isinstance(e, ListReference):
            list_ref: ListReference = e
            raise vol.Invalid(
                f"List references not allow in expansion rules ({{{list_ref.list_name}}})"
            )

        if isinstance(e, RuleReference):
            rule_ref: RuleReference = e
            raise vol.Invalid(
                f"Rule references not allow in expansion rules ({{{rule_ref.rule_name}}})"
            )

    _visit_expression(parse_sentence(sentence).expression, visitor, None)
    return sentence


def not_optional(sentence: str):
    """Validator that ensures a sentence is not completely optional."""

    top_expression = parse_sentence(sentence).expression
    if isinstance(top_expression, Alternative):
        alt: Alternative = top_expression
        if alt.is_optional:
            raise vol.Invalid("Expansion rule must have some required text")

    return sentence


def no_alternative_list_references(sentence: str):
    """Validator that doesn't allow for {list} references in (an|alternative) or [an optional]."""

    def visitor(e: Expression, arg: Any):
        if isinstance(e, Alternative):
            return True

        in_alternative: bool = arg

        if isinstance(e, ListReference) and in_alternative:
            list_ref: ListReference = e
            raise vol.Invalid(
                f"List references not allow in alternatives (a|b) or optionals [c] ({{{list_ref.list_name}}})"
            )

        return in_alternative

    _visit_expression(parse_sentence(sentence).expression, visitor, False)
    return sentence


INTENTS_SCHEMA = vol.Schema(
    {
        # intent name
        str: {
            vol.Required("description"): str,
            vol.Required("slot_combinations"): {
                # slot combination name
                str: {
                    vol.Required("slots"): vol.Any(str, [str]),
                    vol.Required("example"): vol.Any(str, [str]),
                    vol.Optional("domain"): vol.Any(str, [str]),
                    vol.Optional("context_area"): bool,
                }
            },
            vol.Optional("slots"): {
                # slot name and description
                str: str
            },
        }
    },
)

SENTENCES_SCHEMA = vol.Schema(
    {
        vol.Required("language"): str,
        vol.Optional("lists"): {
            str: vol.Any(
                {
                    vol.Required("values"): [
                        vol.Any(
                            str,
                            {
                                vol.Required("in"): str,
                                vol.Required("out"): vol.Any(str, int),
                            },
                        )
                    ]
                },
                {
                    vol.Required("range"): {
                        vol.Required("from"): int,
                        vol.Required("to"): int,
                        vol.Optional("step"): int,
                    }
                },
            )
        },
        vol.Optional("expansion_rules"): {
            str: vol.All(no_list_or_rule_references, not_optional)
        },
        vol.Optional("intents"): {
            str: {
                vol.Required("data"): [
                    {
                        vol.Required("sentences"): [no_alternative_list_references],
                        vol.Optional("requires_context"): {
                            vol.Required("domain"): vol.Any(str, [str])
                        },
                        vol.Optional("slots"): {
                            # slot name
                            str: vol.Any(str, int)
                        },
                        vol.Required("metadata"): {
                            vol.Required("slot_combination"): str,
                            vol.Optional("context_area"): bool,
                        },
                    }
                ]
            }
        },
    }
)

TEST_SENTENCES_SCHEMA = vol.Schema(
    {
        vol.Required("language"): str,
        vol.Required("floors"): [{vol.Required("name"): vol.Any(str, [str])}],
        vol.Required("areas"): [{vol.Required("name"): vol.Any(str, [str])}],
        vol.Required("entities"): [
            {
                vol.Required("name"): vol.Any(str, [str]),
                vol.Required("domain"): str,
                vol.Optional("light_supports_brightness"): bool,
                vol.Optional("light_supports_color"): bool,
            }
        ],
        # Format arguments used in test sentences/slots.
        # Requires "uses_format_values: <list of keys>" and "{key}" in sentence/slot.
        vol.Optional("test_format_values"): {
            # values key
            str: [vol.Any(str, {vol.Required("in"): str, vol.Required("out"): str})]
        },
        vol.Optional("tests"): {
            # intent name
            str: {
                # slot combination name
                str: [
                    vol.Any(
                        str,  # sentence
                        {
                            vol.Required("sentences"): vol.Any(str, [str]),
                            vol.Optional("slots"): {
                                # slot name
                                str: vol.Any(str, int)
                            },
                            vol.Optional("context_area"): bool,
                            vol.Optional("uses_format_values"): vol.Any(str, [str]),
                        },
                    )
                ]
            }
        },
    }
)


def test_validate_intents() -> None:
    """Test that the intents YAML file matches expected schema."""
    intents_path = _PROGRAM_DIR / "intents.yaml"
    with open(intents_path, "r", encoding="utf-8") as intents_file:
        intents_dict = yaml.safe_load(intents_file)
        validate_with_humanized_errors(intents_dict, INTENTS_SCHEMA)


@pytest.mark.parametrize("language", (Language.ENGLISH,))
def test_validate_sentences(language: Language) -> None:
    """Test that sentence YAML files match expected schema."""
    lang_code = language.value

    lang_sentences_path = _SENTENCES_DIR / f"{lang_code}.yaml"
    assert (
        lang_sentences_path.exists()
    ), f"Missing sentences file for language '{lang_code}' at '{lang_sentences_path}'"

    with open(lang_sentences_path, "r", encoding="utf-8") as lang_sentences_file:
        lang_sentences_dict = yaml.safe_load(lang_sentences_file)
        validate_with_humanized_errors(lang_sentences_dict, SENTENCES_SCHEMA)


@pytest.mark.parametrize("language", (Language.ENGLISH,))
def test_validate_tests(language: Language) -> None:
    """Test that test YAML files match expected schema."""
    lang_code = language.value

    lang_test_sentences_path = _TEST_SENTENCES_DIR / f"{lang_code}.yaml"
    assert (
        lang_test_sentences_path.exists()
    ), f"Missing test sentences file for language '{lang_code}' at '{lang_test_sentences_path}'"

    with open(
        lang_test_sentences_path, "r", encoding="utf-8"
    ) as lang_test_sentences_file:
        lang_test_sentences_dict = yaml.safe_load(lang_test_sentences_file)
        validate_with_humanized_errors(lang_test_sentences_dict, TEST_SENTENCES_SCHEMA)
