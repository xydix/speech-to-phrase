"""English tests."""

import shutil
from typing import Any, Dict

import pytest
import pytest_asyncio
from hassil import Intents, recognize_best
from home_assistant_intents import get_intents
from pysilero_vad import SileroVoiceActivityDetector

from speech_to_phrase import MODELS, Language, Things, train, transcribe
from speech_to_phrase.audio import wav_audio_stream

from . import SETTINGS, TESTS_DIR, get_test_things, load_test_sentences

# from speech_to_phrase.hass_api import Area, Entity, Floor


LANGUAGE = Language.ENGLISH.value
TEST_SENTENCES = load_test_sentences(LANGUAGE)
MODEL = MODELS[LANGUAGE]

WAV_DIR = TESTS_DIR / "wav" / LANGUAGE

VAD = SileroVoiceActivityDetector()


@pytest.fixture(scope="session")
def english_things() -> Things:
    """Get HA things from tests."""
    return get_test_things("en")


@pytest.fixture(scope="session")
def english_intents(
    english_things: Things,  # pylint: disable=redefined-outer-name
) -> Intents:
    """Get HA intents for English."""
    intents_dict = get_intents("en")
    lists_dict = intents_dict.get("lists", {})
    lists_dict.update(english_things.to_lists_dict())
    intents_dict["lists"] = lists_dict

    return Intents.from_dict(intents_dict)


@pytest_asyncio.fixture(scope="session")
async def train_english(
    english_things: Things,  # pylint: disable=redefined-outer-name
) -> None:
    """Train English Kaldi model once per session."""
    if SETTINGS.train_dir.exists():
        shutil.rmtree(SETTINGS.train_dir)

    await train(MODEL, SETTINGS, english_things)


@pytest.mark.parametrize("text,intent_info", TEST_SENTENCES)
@pytest.mark.asyncio
async def test_transcribe(
    text: str,
    intent_info: Dict[str, Any],
    train_english,  # pylint: disable=redefined-outer-name
    english_intents: Intents,  # pylint: disable=redefined-outer-name
    english_things: Things,  # pylint: disable=redefined-outer-name
) -> None:
    """Test transcribing expected sentences."""
    wav_path = WAV_DIR / f"{text}.wav"
    if not wav_path.exists():
        generated_wav_path = WAV_DIR / "generated" / f"{text}.wav"
        assert (
            generated_wav_path.exists()
        ), f"Missing {wav_path} or {generated_wav_path}"

        if generated_wav_path.exists():
            wav_path = generated_wav_path

    transcript = await transcribe(MODEL, SETTINGS, wav_audio_stream(wav_path, VAD))
    assert transcript, f"No transcript for: '{text}'"

    context_area = english_things.areas[0].names[0]
    result = recognize_best(
        text,
        english_intents,
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


@pytest.mark.parametrize("wav_num", [1, 2, 3, 4])
@pytest.mark.asyncio
async def test_oov(
    wav_num: int, train_english  # pylint: disable=redefined-outer-name
) -> None:
    """Test transcribing out-of-vocabulary (OOV) sentences."""
    wav_path = WAV_DIR / f"oov_{wav_num}.wav"
    assert wav_path.exists(), f"Missing {wav_path}"

    transcript = await transcribe(MODEL, SETTINGS, wav_audio_stream(wav_path, VAD))
    assert not transcript
