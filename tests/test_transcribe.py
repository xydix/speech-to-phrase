"""Test transcribing and recognition for each language."""

import re
import shutil
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path

import pytest
import pytest_asyncio
import yaml
from pysilero_vad import SileroVoiceActivityDetector

from speech_to_phrase import MODELS, Model, Things, train, transcribe
from speech_to_phrase.audio import wav_audio_stream

from . import SETTINGS, TESTS_DIR


@dataclass
class Resources:
    """Resources for a language."""

    language: str
    test_things: Things
    model: Model
    wav_dir: Path
    vad: SileroVoiceActivityDetector


TEST_LANGUAGES = ["en"]


@pytest_asyncio.fixture(name="lang_resources", params=TEST_LANGUAGES, scope="session")
async def lang_resources_fixture(request) -> Resources:
    """Load language resources and train STP model."""
    language = request.param

    with open(
        TESTS_DIR / "fixtures" / f"{language}.yaml", "r", encoding="utf-8"
    ) as fixtures_file:
        fixtures_dict = yaml.safe_load(fixtures_file)

    assert fixtures_dict["language"] == language
    test_things = Things.from_dict(fixtures_dict["fixtures"])

    # Train STP model
    model = MODELS[language]
    model_train_dir = SETTINGS.model_train_dir(model.id)
    if model_train_dir.exists():
        shutil.rmtree(model_train_dir)

    await train(model, SETTINGS, test_things)

    return Resources(
        language=language,
        test_things=test_things,
        model=model,
        wav_dir=TESTS_DIR / "wav" / language,
        vad=SileroVoiceActivityDetector(),
    )


async def do_transcribe_recognize(
    lang_resources: Resources, wav_path: Path, generated: bool
) -> None:
    """Test transcribing expected sentences."""
    if wav_path.name.startswith("oov_"):
        expected_texts = {""}
    else:
        text_path = wav_path.with_suffix(".txt")
        if text_path.exists():
            expected_texts = set(
                filter(
                    None,
                    text_path.read_text(encoding="utf-8").splitlines(keepends=False),
                )
            )
        else:
            expected_texts = {wav_path.stem}

    actual_text = await transcribe(
        lang_resources.model,
        SETTINGS,
        wav_audio_stream(wav_path, lang_resources.vad),
    )

    if generated:
        if actual_text not in expected_texts:
            warnings.warn(
                UserWarning(
                    "Got unexpected transcript: "
                    f"actual={actual_text}, "
                    f"expected={expected_texts}, "
                    f"file={wav_path}"
                )
            )
    else:
        assert (
            actual_text in expected_texts
        ), f"Got unexpected transcript for: {wav_path}"


def gen_test(language: str, wav_path: Path, generated: bool) -> None:
    """Generate a test function for each test WAV per language."""

    @pytest.mark.parametrize("lang_resources", [language], indirect=True)
    @pytest.mark.asyncio
    async def test_func(lang_resources: Resources) -> None:
        await do_transcribe_recognize(lang_resources, wav_path, generated)

    text = wav_path.stem
    text_sanitized = text.lower()
    text_sanitized = re.sub(r"\s+", "_", text_sanitized)
    text_sanitized = re.sub(r"[^a-z0-9_]", "", text_sanitized)

    if generated:
        gen = "gen_"
    else:
        gen = ""

    test_func.__name__ = f"test_transcribe_{language}_{gen}{text_sanitized}"
    setattr(sys.modules[__name__], test_func.__name__, test_func)


def gen_tests() -> None:
    """Generate test functions for all languages."""
    for lang_dir in (TESTS_DIR / "wav").iterdir():
        if not lang_dir.is_dir():
            continue

        language = lang_dir.name
        if language not in TEST_LANGUAGES:
            continue

        for wav_path in lang_dir.glob("*.wav"):
            gen_test(language, wav_path, generated=False)

        for wav_path in (lang_dir / "generated").glob("*.wav"):
            gen_test(language, wav_path, generated=True)


gen_tests()
