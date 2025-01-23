"""English tests."""

import shutil
from pathlib import Path

import pytest
import pytest_asyncio
from pysilero_vad import SileroVoiceActivityDetector

from speech_to_phrase import train, transcribe, MODELS, Language, Things, Settings
from speech_to_phrase.audio import wav_audio_stream
from speech_to_phrase.hass_api import Entity, Area, Floor

LANGUAGE = Language.ENGLISH.value
MODEL = MODELS[LANGUAGE]

TESTS_DIR = Path(__file__).parent
ROOT_DIR = TESTS_DIR.parent

LOCAL_DIR = ROOT_DIR / "local"
WAV_DIR = TESTS_DIR / "wav" / LANGUAGE

THINGS = Things(
    entities=[
        Entity(names=["New York"], domain="weather"),
        Entity(names=["EcoBee"], domain="climate"),
        Entity(names=["Standing Light"], domain="light"),
        Entity(names=["Bed Light"], domain="light"),
        Entity(names=["Outdoor Humidity"], domain="sensor"),
        Entity(names=["Garage Door"], domain="cover"),
        Entity(names=["Front Door"], domain="lock"),
        Entity(names=["Party Time"], domain="script"),
        Entity(names=["Mood Lighting"], domain="scene"),
    ],
    areas=[Area(names=["Office"]), Area(names=["Kitchen"])],
    floors=[Floor(names=["First Floor"])],
)
SETTINGS = Settings(
    models_dir=LOCAL_DIR / "models",
    train_dir=TESTS_DIR / "train",
    tools_dir=LOCAL_DIR,
)

VAD = SileroVoiceActivityDetector()


@pytest_asyncio.fixture(scope="session")
async def train_english() -> None:
    """Train English Kaldi model once per session."""
    if SETTINGS.train_dir.exists():
        shutil.rmtree(SETTINGS.train_dir)

    await train(MODEL, SETTINGS, THINGS)


@pytest.mark.parametrize(
    "text",
    [
        "what time is it",
        "what's the date",
        "what's the weather",
        "what's the weather like in New York",
        "what's the temperature",
        "what's the temperature of the EcoBee",
        "turn on Standing Light",
        "turn off lights in the Office",
        "turn on lights on the First Floor",
        "set Kitchen lights to green",
        "set Bed Light brightness to 50 percent",
        "what is the Outdoor Humidity",
        "close the Garage Door",
        "is the Garage Door open",
        "lock the Front Door",
        "is the Front Door locked",
        "set a timer for 5 minutes",
        "set a timer for 30 seconds",
        "set a timer for 3 hours and 10 minutes",
        "pause timer",
        "resume timer",
        "cancel timer",
        "cancel all timers",
        "timer status",
        "pause",
        "resume",
        "next",
        "run Party Time",
        "activate Mood Lighting",
        "never mind",
    ],
)
@pytest.mark.asyncio
async def test_transcribe(text: str, train_english) -> None:
    """Test transcribing expected sentences."""
    wav_path = WAV_DIR / f"{text}.wav"
    assert wav_path.exists(), f"Missing {wav_path}"

    transcript = await transcribe(MODEL, SETTINGS, wav_audio_stream(wav_path, VAD))
    assert text == transcript


@pytest.mark.parametrize("wav_num", [1, 2, 3])
@pytest.mark.asyncio
async def test_oov(wav_num: int, train_english) -> None:
    """Test transcribing out-of-vocabulary (OOV) sentences."""
    wav_path = WAV_DIR / f"oov_{wav_num}.wav"
    assert wav_path.exists(), f"Missing {wav_path}"

    transcript = await transcribe(MODEL, SETTINGS, wav_audio_stream(wav_path, VAD))
    assert not transcript
