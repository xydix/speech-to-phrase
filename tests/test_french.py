"""English tests."""

import shutil
from pathlib import Path

import pytest
import pytest_asyncio
from pysilero_vad import SileroVoiceActivityDetector

from speech_to_phrase import MODELS, Language, Things, train, transcribe
from speech_to_phrase.audio import wav_audio_stream
from speech_to_phrase.hass_api import Area, Entity, Floor

from . import SETTINGS, TESTS_DIR

LANGUAGE = Language.FRENCH.value
MODEL = MODELS[LANGUAGE]

WAV_DIR = TESTS_DIR / "wav" / LANGUAGE

THINGS = Things(
    entities=[
        Entity(names=["New York"], domain="weather"),
        # Entity(names=["EcoBee"], domain="climate"),
        # Entity(names=["Standing Light"], domain="light"),
        # Entity(names=["Bed Light"], domain="light"),
        # Entity(names=["Outdoor Humidity"], domain="sensor"),
        # Entity(names=["Garage Door"], domain="cover"),
        # Entity(names=["Front Door"], domain="lock"),
        # Entity(names=["Party Time"], domain="script"),
        # Entity(names=["Mood Lighting"], domain="scene"),
    ],
    areas=[Area(names=["Bureau"]), Area(names=["Salon"])],
    floors=[Floor(names=["Premier Étage"])],
)

VAD = SileroVoiceActivityDetector()


@pytest_asyncio.fixture(scope="session")
async def train_french() -> None:
    """Train English Kaldi model once per session."""
    if SETTINGS.train_dir.exists():
        shutil.rmtree(SETTINGS.train_dir)

    await train(MODEL, SETTINGS, THINGS)


@pytest.mark.parametrize(
    "text",
    [
        "quelle heure est-il",
        "quel jour sommes-nous",
        "quel temps fait-il",
        "quel temps fait-il à New York",
        "combien fait-il",
        "combien fait-il dans le Salon",
        # "turn on Standing Light",
        # "turn off lights in the Office",
        # "turn on lights on the First Floor",
        # "set Kitchen lights to green",
        # "set Bed Light brightness to 50 percent",
        # "what is the Outdoor Humidity",
        # "close the Garage Door",
        # "is the Garage Door open",
        # "lock the Front Door",
        # "is the Front Door locked",
        "minuteur 5 minutes",
        "minuteur 30 secondes",
        "minuteur 3 heures et 10 minutes",
        # "pause timer",
        # "resume timer",
        # "cancel timer",
        # "cancel all timers",
        "combien de temps reste-t-il",
        "pause",
        # "resume",
        "suivant",
        # "run Party Time",
        # "activate Mood Lighting",
        # "never mind",
    ],
)
@pytest.mark.asyncio
async def test_transcribe(text: str, train_french) -> None:
    """Test transcribing expected sentences."""
    wav_path = WAV_DIR / f"{text}.wav"
    assert wav_path.exists(), f"Missing {wav_path}"

    transcript = await transcribe(MODEL, SETTINGS, wav_audio_stream(wav_path, VAD))
    assert text == transcript


# @pytest.mark.parametrize("wav_num", [1, 2, 3])
# @pytest.mark.asyncio
# async def test_oov(wav_num: int, train_english) -> None:
#     """Test transcribing out-of-vocabulary (OOV) sentences."""
#     wav_path = WAV_DIR / f"oov_{wav_num}.wav"
#     assert wav_path.exists(), f"Missing {wav_path}"

#     transcript = await transcribe(MODEL, SETTINGS, wav_audio_stream(wav_path, VAD))
#     assert not transcript
