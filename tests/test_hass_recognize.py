"""Test that Speech-to-Phrase sentences will be recognized by Home Assistant."""

import itertools
import re
import sys
from dataclasses import dataclass

import pytest
from hassil import (
    Intents,
    SlotList,
    TextSlotList,
    parse_sentence,
    recognize_all,
    sample_expression,
)
from home_assistant_intents import get_intents

from speech_to_phrase.lang_sentences import LanguageData, SentenceBlock
from speech_to_phrase.util import yaml

from . import SETTINGS, TEST_LANGUAGES


@dataclass
class Resources:
    """Resources for a language."""

    language: str
    intents: Intents


@pytest.fixture(name="lang_resources", params=TEST_LANGUAGES, scope="session")
def lang_resources_fixture(request) -> Resources:
    language = request.param
    lang_intents_dict = get_intents(language)
    assert lang_intents_dict, f"No intents for language: {language}"

    lang_lists = lang_intents_dict.setdefault("lists", {})

    # Only test edges of ranges
    lang_lists["brightness"] = {"values": ["10", "100"]}
    lang_lists["seconds"] = {"values": ["10", "100"]}
    lang_lists["minutes"] = {"values": ["2", "100"]}
    lang_lists["hours"] = {"values": ["2", "100"]}

    with open(
        SETTINGS.sentences / f"{language}.yaml", "r", encoding="utf-8"
    ) as sentences_file:
        sentences_dict = yaml.load(sentences_file)

    for list_name, list_values in sentences_dict.get("lists", {}).items():
        lang_lists[list_name] = {"values": list_values}

    lang_intents = Intents.from_dict(lang_intents_dict)

    # Placeholders
    for list_name in itertools.chain(
        ("name", "area", "floor"), sentences_dict.get("wildcards", [])
    ):
        lang_intents.slot_lists[list_name] = TextSlotList.from_strings(
            (f"{{{list_name}}}",), allow_template=False, name=list_name
        )

    return Resources(language=language, intents=lang_intents)


def do_recognize(
    lang_resources: Resources,
    lang_data: LanguageData,
    sen_block: SentenceBlock,
    sentence_text: str,
) -> None:
    error_info = f"language={lang_resources.language}, sentence={sentence_text}"
    sentence = parse_sentence(sentence_text)
    sen_slot_lists: dict[str, SlotList] = {}
    intent_context = {"area": "{area}"}

    if sen_block.domains:
        # Create a {name} entity for each possible domain.
        sen_slot_lists = {
            **lang_resources.intents.slot_lists,
            "name": TextSlotList.from_tuples(
                (
                    ("{name}", "{name}", {"domain": domain}, {"domain": domain})
                    for domain in sen_block.domains
                ),
                allow_template=False,
                name="name",
            ),
        }
    else:
        sen_slot_lists = lang_resources.intents.slot_lists

    domains_to_check: set[str] = set(sen_block.domains or [])
    found_result = False

    for example_text in sample_expression(sentence.expression, sen_slot_lists):
        for result in recognize_all(
            example_text,
            lang_resources.intents,
            slot_lists=sen_slot_lists,
            intent_context=intent_context,
        ):
            found_result = True
            if (not sen_block.domains) or (not domains_to_check):
                # Only need one result
                break

            name_entity = result.entities.get("name")
            assert name_entity is not None
            assert name_entity.metadata
            name_domain = name_entity.metadata["domain"]
            assert name_domain in sen_block.domains
            domains_to_check.discard(name_domain)

    assert found_result, f"Sentence was not recognized: {error_info}"
    assert (
        not domains_to_check
    ), f"Domains were not checked: domains={domains_to_check}, {error_info}"


def gen_test(
    language: str, lang_data: LanguageData, sen_block: SentenceBlock, sentence_text: str
) -> None:

    @pytest.mark.parametrize("lang_resources", [language], indirect=True)
    def test_func(lang_resources: Resources) -> None:
        do_recognize(lang_resources, lang_data, sen_block, sentence_text)

    text = sentence_text
    text_sanitized = text.lower()
    text_sanitized = re.sub(r"(?:\s+)|(?:[-|]+)", "_", text_sanitized)
    text_sanitized = re.sub(r"[_]+", "_", text_sanitized)
    text_sanitized = re.sub(r"[^a-zàâäéèêëîïôöùûüÿ0-9_]", "", text_sanitized)

    test_func.__name__ = f"test_transcribe_{text_sanitized}"
    setattr(sys.modules[__name__], test_func.__name__, test_func)


def gen_tests() -> None:
    """Generate test functions for all languages."""
    for sentences_path in SETTINGS.sentences.glob("*.yaml"):
        language = sentences_path.stem
        if language not in TEST_LANGUAGES:
            continue

        with open(sentences_path, "r", encoding="utf-8") as sentences_file:
            sentences_dict = yaml.load(sentences_file)

        lang_data = LanguageData.from_dict(sentences_dict)
        for sen_block in lang_data.sentence_blocks:
            for sentence_text in sen_block.sentences:
                gen_test(language, lang_data, sen_block, sentence_text)


gen_tests()
