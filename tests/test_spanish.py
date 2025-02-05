"""Spanish tests."""

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

LANGUAGE = Language.SPANISH.value
MODEL = MODELS[LANGUAGE]

WAV_DIR = TESTS_DIR / "wav" / LANGUAGE

THINGS = Things(
    entities=[
        Entity(names=["New York"], domain="weather"),
        Entity(names=["EcoBee"], domain="climate"),
        Entity(names=["Lámpara"], domain="light"),
        Entity(names=["Humedad Exterior"], domain="sensor"),
        Entity(names=["Puerta del Garaje"], domain="cover"),
        Entity(names=["Puerta Principal"], domain="lock"),
    ],
    areas=[Area(names=["Oficina"]), Area(names=["Cocina"])],
    floors=[Floor(names=["Primer Piso"])],
)

VAD = SileroVoiceActivityDetector()


@pytest.fixture(scope="session")
def spanish_intents() -> Intents:
    intents_dict = get_intents("es")
    lists_dict = intents_dict.get("lists", {})
    lists_dict.update(THINGS.to_lists_dict())
    intents_dict["lists"] = lists_dict

    return Intents.from_dict(intents_dict)


@pytest_asyncio.fixture(scope="session")
async def train_spanish() -> None:
    """Train Spanish Kaldi model once per session."""
    if SETTINGS.train_dir.exists():
        shutil.rmtree(SETTINGS.train_dir)

    await train(MODEL, SETTINGS, THINGS)


@pytest.mark.parametrize(
    "text",
    [
        "qué hora es",
        "qué día es",
        "qué tiempo hace",
        "qué tiempo hace en New York",
        "cuál es la temperatura",
        "cuál es la temperatura del EcoBee",
        "enciende la Lámpara",
        "apaga las luces de la Oficina",
        "enciende las luces del Primer Piso",
        "ajusta el color de las luces de la Cocina a verde",
        "ajusta el brillo de la Lámpara al 50 por ciento",
        "cuál es la Humedad Exterior",
        "cierra la Puerta del Garaje",
        "está la Puerta del Garaje abierta",
        "cierra con llave la Puerta Principal",
        "está cerrada con llave la Puerta Principal",
        "inicia un temporizador de 5 minutos",
        "inicia un temporizador de 30 segundos",
        "inicia un temporizador de 3 horas y 10 minutos",
        "pausa el temporizador",
        "continúa el temporizador",
        "cancela el temporizador",
        "cancela todos los temporizadores",
        "estado de temporizador",
        "pausa",
        "continúa",
        "siguiente canción",
        "no importa",
    ],
)
@pytest.mark.asyncio
async def test_transcribe(
    text: str,
    train_spanish,  # pylint: disable=redefined-outer-name
    spanish_intents: Intents,  # pylint: disable=redefined-outer-name
) -> None:
    """Test transcribing expected sentences."""
    assert recognize(
        text, spanish_intents, intent_context={"area": "Cocina"}
    ), f"Sentence not recognized: {text}"

    wav_path = WAV_DIR / f"{text}.wav"
    assert wav_path.exists(), f"Missing {wav_path}"

    transcript = await transcribe(MODEL, SETTINGS, wav_audio_stream(wav_path, VAD))
    assert text == transcript


# @pytest.mark.parametrize("wav_num", [1, 2, 3, 4])
# @pytest.mark.asyncio
# async def test_oov(
#     wav_num: int, train_spanish  # pylint: disable=redefined-outer-name
# ) -> None:
#     """Test transcribing out-of-vocabulary (OOV) sentences."""
#     wav_path = WAV_DIR / f"oov_{wav_num}.wav"
#     assert wav_path.exists(), f"Missing {wav_path}"

#     transcript = await transcribe(MODEL, SETTINGS, wav_audio_stream(wav_path, VAD))
#     assert not transcript
