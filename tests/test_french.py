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
        Entity(names=["Porte d'entrée"], domain="lock"),
        # Entity(names=["Party Time"], domain="script"),
        # Entity(names=["Mood Lighting"], domain="scene"),
    ],
    areas=[Area(names=["Bureau"]), Area(names=["Salon"]), Area(names=["Chambre"])],
    floors=[Floor(names=["Premier Étage"]), Floor(names=["Rez-de-chaussée"])],
)

VAD = SileroVoiceActivityDetector()


@pytest_asyncio.fixture(scope="session")
async def train_french() -> None:
    """Train English Kaldi model once per session."""
    if SETTINGS.train_dir.exists():
        shutil.rmtree(SETTINGS.train_dir)

    await train(MODEL, SETTINGS, THINGS)


# Some of these sentences have incorrect grammar. This is on purpose because:
# 1. There is no way speech-to-phrase is going to get it exactly correct
# 2. It doesn't matter anyways because the intent recognizer is flexible
@pytest.mark.parametrize(
    "text",
    [
        "allume la Chambre à 80 pourcent",
        "allume la lumière",
        "allume le Bureau en rouge",
        "allume le Premier Étage en vert",
        "allume le Rez-de-chaussée à 80 pourcent",
        "allume les lumières dans la Chambre",
        "allume les lumières en bleu",
        "allume toutes les lumières",
        "allume toutes les lumières dans le Rez-de-chaussée",
        "annuler",
        "combien de temps reste-t-il",
        "combien fait-il",
        "combien fait-il dans le Bureau",
        "combien fait-il dans le Salon",
        "déverrouille la Porte d'entrée",
        "éteins la lumière",
        "éteins les lumières dans le Salon",
        "éteins toutes les lumières",
        "éteins toutes les lumières du Premier Étage",
        "ferme les rideau du Bureau",
        "fermer les rideau",
        "ferme tous les volet",
        "média suivant",
        "minuteur 10 minutes",
        "minuteur 1 heures",
        "minuteur 20 secondes",
        "minuteur 30 secondes",
        "minuteur 3 heures et 10 minutes",
        "minuteur 5 minutes",
        "ouvre les rideau du Rez-de-chaussée",
        "ouvre les volet",
        "ouvre les volet du Premier Étage",
        "ouvre tous les volet",
        "pause",
        "quel jour sommes-nous",
        "quelle heure est-il",
        "quel temps fait-il",
        "quel temps fait-il à New York",
        "règle la luminosité dans le Bureau à 50 pourcent",
        "silence",
        "suivant",
        "supprime le minuteur",
        "supprime tous les minuteurs",
        "verrouille la Porte d'entrée",
    ],
)
@pytest.mark.asyncio
async def test_transcribe(text: str, train_french) -> None:
    """Test transcribing expected sentences."""
    wav_path = WAV_DIR / f"{text}.wav"
    assert wav_path.exists(), f"Missing {wav_path}"

    transcript = await transcribe(MODEL, SETTINGS, wav_audio_stream(wav_path, VAD))
    assert text == transcript


@pytest.mark.parametrize("wav_num", [1, 2, 3, 4])
@pytest.mark.asyncio
async def test_oov(wav_num: int, train_french) -> None:
    """Test transcribing out-of-vocabulary (OOV) sentences."""
    wav_path = WAV_DIR / f"oov_{wav_num}.wav"
    assert wav_path.exists(), f"Missing {wav_path}"

    transcript = await transcribe(MODEL, SETTINGS, wav_audio_stream(wav_path, VAD))
    assert not transcript
