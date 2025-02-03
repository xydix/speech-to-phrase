"""German tests."""

import shutil

import pytest
import pytest_asyncio
from hassil.intents import Intents
from hassil.recognize import recognize
from pysilero_vad import SileroVoiceActivityDetector

from speech_to_phrase import MODELS, Language, Things, train, transcribe
from speech_to_phrase.audio import wav_audio_stream
from speech_to_phrase.hass_api import Area, Entity, Floor

from . import SETTINGS, TESTS_DIR

LANGUAGE = Language.GERMAN.value
MODEL = MODELS[LANGUAGE]

WAV_DIR = TESTS_DIR / "wav" / LANGUAGE

THINGS = Things(
    entities=[
        Entity(names=["New York"], domain="weather"),
        Entity(names=["EcoBee"], domain="climate"),
        Entity(names=["Lampe"], domain="light"),
        Entity(names=["Außenluftfeuchtigkeit"], domain="sensor"),
        Entity(names=["Garagentor"], domain="cover"),
        Entity(names=["Vordertür"], domain="lock"),
    ],
    areas=[Area(names=["Büro"]), Area(names=["Küchen"])],
    floors=[Floor(names=["erster Stock", "ersten Stock"])],
)

VAD = SileroVoiceActivityDetector()


@pytest_asyncio.fixture(scope="session")
async def train_german() -> Intents:
    """Train German Kaldi model once per session."""
    if SETTINGS.train_dir.exists():
        shutil.rmtree(SETTINGS.train_dir)

    await train(MODEL, SETTINGS, THINGS)

    # Load training sentences
    with open(
        SETTINGS.training_sentences_path(MODEL.id), "r", encoding="utf-8"
    ) as training_sentences_file:
        return Intents.from_yaml(training_sentences_file)


@pytest.mark.parametrize(
    "text",
    [
        "wie spät ist es",
        "welches datum ist heute",
        "wie ist das Wetter",
        "wie ist das Wetter in New York",
        "wie hoch ist die Temperatur",
        "Wie hoch ist die Temperatur des EcoBee",
        "schalte das Licht an",
        "schalte die Lampe an",
        "schalte das Licht im Büro aus",
        "setze die Farbe Küchen der Lichter auf grün",
        "schalte die Lichter im ersten Stock aus",
        "stelle die Helligkeit von der Lampe auf 50 Prozent",
        "wie ist die Außenluftfeuchtigkeit",
        "schließ das Garagentor",
        "ist das Garagentor offen",
        "schließ die Vordertür ab",
        "schließ die Vordertür auf",
        "ist die Vordertür abgeschlossen",
        "starte einen Timer für 5 Minuten",
        "starte einen Timer für 30 Sekunden",
        "starte einen Timer für 3 Stunden und 10 Minuten",
        "pausiere Timer",
        "setze den Timer fort",
        "stoppe den Timer",
        "beende alle Timer",
        "Timer Status",
        "pause",
        "fortsetzen",
        "nächsten Song",
        "vergiss es",
    ],
)
@pytest.mark.asyncio
async def test_transcribe(
    text: str, train_german: Intents  # pylint: disable=redefined-outer-name
) -> None:
    """Test transcribing expected sentences."""
    # Verify that sentence is part of training set
    assert recognize(text, train_german), f"Sentence not recognized: {text}"

    # Check transcript
    wav_path = WAV_DIR / f"{text}.wav"
    assert wav_path.exists(), f"Missing {wav_path}"

    transcript = await transcribe(MODEL, SETTINGS, wav_audio_stream(wav_path, VAD))
    assert text == transcript


@pytest.mark.parametrize("wav_num", [1, 2, 3, 4])
@pytest.mark.asyncio
async def test_oov(
    wav_num: int, train_german  # pylint: disable=redefined-outer-name
) -> None:
    """Test transcribing out-of-vocabulary (OOV) sentences."""
    wav_path = WAV_DIR / f"oov_{wav_num}.wav"
    assert wav_path.exists(), f"Missing {wav_path}"

    transcript = await transcribe(MODEL, SETTINGS, wav_audio_stream(wav_path, VAD))
    assert not transcript
