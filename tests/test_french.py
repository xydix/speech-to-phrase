"""French tests."""

import shutil

import pytest
import pytest_asyncio
from hassil.intents import Intents
from hassil.recognize import recognize
from home_assistant_intents import get_intents
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
        Entity(names=["Porte d'entrée"], domain="lock"),
    ],
    areas=[Area(names=["Bureau"]), Area(names=["Salon"]), Area(names=["Chambre"])],
    floors=[Floor(names=["Premier Étage"]), Floor(names=["Rez-de-chaussée"])],
)

VAD = SileroVoiceActivityDetector()


@pytest.fixture(scope="session")
def french_intents() -> Intents:
    intents_dict = get_intents("fr")
    lists_dict = intents_dict.get("lists", {})
    lists_dict.update(THINGS.to_lists_dict())
    intents_dict["lists"] = lists_dict

    return Intents.from_dict(intents_dict)


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
        "lecture",
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
async def test_transcribe(
    text: str,
    train_french,  # pylint: disable=redefined-outer-name
    french_intents: Intents,  # pylint: disable=redefined-outer-name
) -> None:
    """Test transcribing expected sentences."""
    assert recognize(
        text, french_intents, intent_context={"area": "Salon"}
    ), f"Sentence not recognized: {text}"

    wav_path = WAV_DIR / f"{text}.wav"
    assert wav_path.exists(), f"Missing {wav_path}"

    transcript = await transcribe(MODEL, SETTINGS, wav_audio_stream(wav_path, VAD))
    assert text == transcript


@pytest.mark.parametrize("wav_num", [1, 2, 3, 4])
@pytest.mark.asyncio
async def test_oov(
    wav_num: int, train_french  # pylint: disable=redefined-outer-name
) -> None:
    """Test transcribing out-of-vocabulary (OOV) sentences."""
    wav_path = WAV_DIR / f"oov_{wav_num}.wav"
    assert wav_path.exists(), f"Missing {wav_path}"

    transcript = await transcribe(MODEL, SETTINGS, wav_audio_stream(wav_path, VAD))
    assert not transcript
