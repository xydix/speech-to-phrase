"""Test transcribing and recognition for each language."""

import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import pytest
import pytest_asyncio
from hassil import Intents, recognize_best
from home_assistant_intents import get_intents
from pysilero_vad import SileroVoiceActivityDetector

from speech_to_phrase import MODELS, Language, Model, Things, train, transcribe
from speech_to_phrase.audio import wav_audio_stream

from . import SETTINGS, TESTS_DIR, get_test_things, load_test_sentences

LANGUAGES = [Language.ENGLISH.value]


@dataclass
class Resources:
    """Resources for a language."""

    language: str
    test_things: Things
    hass_intents: Intents
    model: Model
    wav_dir: Path
    vad: SileroVoiceActivityDetector


@pytest_asyncio.fixture(params=LANGUAGES, scope="session")
async def lang_resources(request) -> Resources:
    """Load language resources and train STP model."""
    language = request.param

    test_things = get_test_things(language)
    test_lists_dict = test_things.to_lists_dict()

    hass_intents_dict = get_intents("en")
    hass_intents_dict["lists"].update(test_lists_dict)

    # Train STP model
    model = MODELS[language]
    model_train_dir = SETTINGS.model_train_dir(model.id)
    if model_train_dir.exists():
        shutil.rmtree(model_train_dir)

    await train(model, SETTINGS, test_things)

    return Resources(
        language=language,
        test_things=test_things,
        hass_intents=Intents.from_dict(hass_intents_dict),
        model=model,
        wav_dir=TESTS_DIR / "wav" / language,
        vad=SileroVoiceActivityDetector(),
    )


@pytest.mark.parametrize("wav_num", [1, 2, 3, 4])
@pytest.mark.asyncio
async def test_oov(
    wav_num: int,
    lang_resources: Resources,  # pylint: disable=redefined-outer-name
) -> None:
    """Test transcribing out-of-vocabulary (OOV) sentences."""
    wav_path = lang_resources.wav_dir / f"oov_{wav_num}.wav"
    assert wav_path.exists(), f"Missing {wav_path}"

    transcript = await transcribe(
        lang_resources.model, SETTINGS, wav_audio_stream(wav_path, lang_resources.vad)
    )
    assert not transcript


async def do_transcribe_recognize(
    lang_resources: Resources,  # pylint: disable=redefined-outer-name
    text: str,
    intent_info: Dict[str, Any],
) -> None:
    """Test transcribing expected sentences."""
    wav_path = lang_resources.wav_dir / f"{text}.wav"
    if not wav_path.exists():
        generated_wav_path = lang_resources.wav_dir / "generated" / f"{text}.wav"
        assert (
            generated_wav_path.exists()
        ), f"Missing {wav_path} or {generated_wav_path}"

        if generated_wav_path.exists():
            wav_path = generated_wav_path

    transcript = await transcribe(
        lang_resources.model,
        SETTINGS,
        wav_audio_stream(wav_path, lang_resources.vad),
    )
    assert transcript, f"No transcript for: '{text}'"

    context_area = lang_resources.test_things.areas[0].names[0]
    result = recognize_best(
        text,
        lang_resources.hass_intents,
        best_slot_name="name",
        intent_context={"area": context_area},
    )
    assert result is not None, f"Not recognized: '{text}'"

    assert result.intent.name == intent_info["intent"]
    result_slots = {e_name: e.value for e_name, e in result.entities.items()}

    if intent_info.get("context_area"):
        assert "area" in result_slots, "Missing context area"
        assert result_slots.pop("area") == context_area

    assert result_slots == intent_info["slots"]


def gen_test(language: str, text: str, intent_info: Dict[str, Any]) -> None:
    """Generate a test function for each test sentence per language."""

    @pytest.mark.parametrize("lang_resources", [language], indirect=True)
    @pytest.mark.asyncio
    async def test_func(
        lang_resources: Resources,  # pylint: disable=redefined-outer-name
    ) -> None:
        await do_transcribe_recognize(lang_resources, text, intent_info)

    text_sanitized = text.lower()
    text_sanitized = re.sub(r"\s+", "_", text_sanitized)
    text_sanitized = re.sub(r"[^a-z0-9_]", "", text_sanitized)

    test_func.__name__ = f"test_transcribe_{language}_{text_sanitized}"
    setattr(sys.modules[__name__], test_func.__name__, test_func)


def gen_tests() -> None:
    """Generate test functions for all languages."""
    for language in LANGUAGES:
        test_sentences = load_test_sentences(language)
        for text, intent_info in test_sentences:
            gen_test(language, text, intent_info)


gen_tests()
