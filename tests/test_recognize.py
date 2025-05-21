"""Test that Speech-to-Phrase sentences will be recognized by Home Assistant."""

from dataclasses import dataclass
from typing import Any

import pytest
from hassil import Intents, recognize_all
from home_assistant_intents import get_intents

from speech_to_phrase import Things
from speech_to_phrase.lang_sentences import LanguageData, load_shared_lists
from speech_to_phrase.util import get_language_family, yaml

from . import SETTINGS, TEST_LANGUAGES, TESTS_DIR

INTENT_CONTEXT = {"area": "<context area>"}


@dataclass
class Resources:
    """Resources for a language."""

    language: str
    stp_intents: Intents
    hass_intents: Intents
    test_sentences: list[str]


@pytest.fixture(name="shared_lists", scope="session")
def shared_lists_fixture() -> dict[str, Any]:
    with open(SETTINGS.shared_lists_path, "r", encoding="utf-8") as shared_lists_file:
        return load_shared_lists(yaml.load(shared_lists_file))


@pytest.fixture(name="lang_resources", params=TEST_LANGUAGES, scope="session")
def lang_resources_fixture(request, shared_lists: dict[str, Any]) -> Resources:
    language = request.param
    hass_intents_dict = get_intents(language)
    if not hass_intents_dict:
        hass_intents_dict = get_intents(get_language_family(language))

    assert hass_intents_dict, f"No intents for language: {language}"

    hass_lists = hass_intents_dict.setdefault("lists", {})

    # Load language sentences
    with open(
        SETTINGS.sentences / f"{language}.yaml", "r", encoding="utf-8"
    ) as sentences_file:
        sentences_dict = yaml.load(sentences_file)

    for list_name, list_values in sentences_dict.get("lists", {}).items():
        hass_lists[list_name] = {"values": list_values}

    stp_intents_dict = LanguageData.from_dict(sentences_dict).to_intents_dict()
    stp_lists = stp_intents_dict.setdefault("lists", {})
    stp_lists.update(shared_lists)

    # Load test fixtures
    with open(
        TESTS_DIR / "fixtures" / f"{language}.yaml", "r", encoding="utf-8"
    ) as fixtures_file:
        fixtures_dict = yaml.load(fixtures_file)

    test_things = Things.from_dict(fixtures_dict["fixtures"])
    test_things_dict = test_things.to_lists_dict()
    hass_lists.update(test_things_dict)
    stp_lists.update(test_things_dict)

    hass_intents = Intents.from_dict(hass_intents_dict)
    stp_intents = Intents.from_dict(stp_intents_dict)

    with open(
        TESTS_DIR / "sentences" / f"{language}.yaml", "r", encoding="utf-8"
    ) as test_file:
        test_sentences_dict = yaml.load(test_file)

    return Resources(
        language=language,
        stp_intents=stp_intents,
        hass_intents=hass_intents,
        test_sentences=test_sentences_dict["sentences"],
    )


def test_recognize(lang_resources: Resources) -> None:
    stp_sentences_to_check: set[str] = {
        template.text
        for intent in lang_resources.stp_intents.intents.values()
        for data in intent.data
        for template in data.sentences
    }
    for sentence in lang_resources.test_sentences:
        error_info = f"sentence='{sentence}', language={lang_resources.language}"

        # STP
        result = next(
            recognize_all(
                sentence, lang_resources.stp_intents, intent_context=INTENT_CONTEXT
            ),
            None,
        )
        assert (
            result is not None
        ), f"Sentence not recognized by Speech-to-Phrase: {error_info}"
        stp_sentences_to_check.discard(result.intent_sentence.text)

        # Home Assistant
        result = next(
            recognize_all(
                sentence, lang_resources.hass_intents, intent_context=INTENT_CONTEXT
            ),
            None,
        )
        assert (
            result is not None
        ), f"Sentence not recognized by Home Assistant: {error_info}"

    assert not stp_sentences_to_check, (
        "Speech-to-Phrase sentence templates were not tested: "
        f"language={lang_resources.language}, "
        f"templates={stp_sentences_to_check}"
    )
