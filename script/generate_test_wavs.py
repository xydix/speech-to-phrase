"""Generate test WAV files using Home Assistant."""

import argparse
import itertools
import json
import logging
import shutil
import subprocess
import tempfile
from collections.abc import Iterable
from functools import partial
from pathlib import Path
from urllib.request import Request, urlopen

from hassil import (
    Alternative,
    Expression,
    Group,
    ListReference,
    Permutation,
    Sequence,
    TextChunk,
    normalize_whitespace,
    parse_sentence,
)
from ruamel.yaml import YAML

_DIR = Path(__file__).parent
_REPO_DIR = _DIR.parent
_STP_DIR = _REPO_DIR / "speech_to_phrase"
_SENTENCES_DIR = _STP_DIR / "sentences"
_TESTS_DIR = _REPO_DIR / "tests"
_FIXTURES_DIR = _TESTS_DIR / "fixtures"
_BACKGROUND_NOISE_WAV = _TESTS_DIR / "wav" / "background_noise.wav"

_LOGGER = logging.getLogger(__name__)

TTS_LANG = {
    "en": "en-US",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hass-url", default="http://localhost:8123")
    parser.add_argument("--hass-token", required=True)
    parser.add_argument("--engine", default="tts.home_assistant_cloud")
    parser.add_argument(
        "--output-dir", default=_TESTS_DIR / "wav", help="Path to output directory"
    )
    parser.add_argument("--language", help="Only generate WAV files for language")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    output_dir = Path(args.output_dir)

    if not shutil.which("sox"):
        _LOGGER.fatal("sox must be installed")
        return 1

    yaml = YAML(typ="safe")
    slot_lists: dict[str, list[str]] = {
        "brightness": ["10", "20", "100"],
        "seconds": ["10", "15", "100"],
        "minutes": ["2", "20", "45", "100"],
        "hours": ["2", "24"],
    }

    for sentences_path in _SENTENCES_DIR.glob("*.yaml"):
        language = sentences_path.stem

        if args.language and (language != args.language):
            continue

        if language in TTS_LANG:
            tts_language = TTS_LANG[language]
        else:
            tts_language = f"{language}-{language.upper()}"

        lang_wav_dir = output_dir / language
        lang_gen_wav_dir = lang_wav_dir / "generated"
        lang_gen_wav_dir.mkdir(parents=True, exist_ok=True)

        lang_slot_lists = dict(slot_lists)

        with open(sentences_path, "r", encoding="utf-8") as sentences_file:
            sentences_dict = yaml.load(sentences_file)

        for list_name, list_info in sentences_dict.get("lists", {}).items():
            if list_name not in lang_slot_lists:
                lang_slot_lists[list_name] = list_info["values"]

        # Add test fixtures
        fixtures_path = _FIXTURES_DIR / f"{language}.yaml"
        with open(fixtures_path, "r", encoding="utf-8") as fixtures_file:
            fixtures_dict = yaml.load(fixtures_file)["fixtures"]

        if "areas" in fixtures_dict:
            lang_slot_lists["area"] = [a["name"] for a in fixtures_dict["areas"]]

        if "floors" in fixtures_dict:
            lang_slot_lists["floor"] = [a["name"] for a in fixtures_dict["floors"]]

        for list_name, list_values in fixtures_dict.get("lists", {}).items():
            if list_name not in lang_slot_lists:
                lang_slot_lists[list_name] = list_values

        for sentence_info in sentences_dict["intents"]["SpeechToPhrase"]["data"]:
            name_domains = sentence_info.get("requires_context", {}).get("domain")
            if name_domains:
                sen_slot_lists = {
                    **lang_slot_lists,
                    "name": [
                        e["name"]
                        for e in fixtures_dict["entities"]
                        if e["domain"] in name_domains
                    ],
                }
            else:
                sen_slot_lists = lang_slot_lists

            for template_text in sentence_info["sentences"]:
                sentence = parse_sentence(template_text)
                for example_text in generate_sentences(
                    sentence.expression, sen_slot_lists
                ):
                    example_text = example_text.strip()
                    # print(example_text)
                    wav_path = lang_wav_dir / f"{example_text}.wav"
                    gen_wav_path = lang_gen_wav_dir / f"{example_text}.wav"

                    if wav_path.exists() or gen_wav_path.exists():
                        continue

                    generate_wav(
                        args.hass_url,
                        args.hass_token,
                        args.engine,
                        tts_language,
                        example_text,
                        gen_wav_path,
                    )
                    print(wav_path)

    return 0


# -----------------------------------------------------------------------------


def generate_wav(
    hass_url: str,
    hass_token: str,
    engine: str,
    language: str,
    text: str,
    wav_path: Path,
) -> None:
    request = Request(
        f"{hass_url}/api/tts_get_url",
        data=json.dumps(
            {"engine_id": engine, "message": text, "language": language}
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {hass_token}",
        },
    )
    with urlopen(request) as response:
        audio_url = json.load(response)["url"]

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        wav_no_noise = temp_dir / "no_noise.wav"
        wav_bg_noise = temp_dir / "bg_noise.wav"

        with urlopen(audio_url) as response:
            subprocess.check_call(
                [
                    "sox",
                    "-t",
                    "mp3",
                    "-",
                    "-r",
                    "16000",
                    "-c",
                    "1",
                    "-e",
                    "signed-integer",
                    "-b",
                    "16",
                    "-t",
                    "wav",
                    str(wav_no_noise),
                    "lowpass",
                    "5000",
                    "highpass",
                    "200",
                    "reverb",
                    "50",
                    "50",
                    "100",
                    "pad",
                    "0.2",
                ],
                stdin=response,
            )

        wav_duration = (
            subprocess.check_output(["soxi", "-D", str(wav_no_noise)]).decode().strip()
        )

        # Add background noise
        subprocess.check_call(
            [
                "sox",
                str(_BACKGROUND_NOISE_WAV),
                str(wav_bg_noise),
                "vol",
                "2",
                "trim",
                "0",
                wav_duration,
            ]
        )
        subprocess.check_call(
            [
                "sox",
                "-m",
                str(wav_bg_noise),
                str(wav_no_noise),
                "-b",
                "16",
                str(wav_path),
            ]
        )


# -----------------------------------------------------------------------------


def generate_sentences(
    expression: Expression, slot_lists: dict[str, list[str]]
) -> Iterable[str]:
    """Sample possible text strings from an expression."""
    if isinstance(expression, TextChunk):
        chunk: TextChunk = expression
        yield chunk.original_text
    elif isinstance(expression, Group):
        grp: Group = expression
        if isinstance(grp, Alternative):
            alt: Alternative = grp
            if alt.is_optional:
                yield ""
            else:
                for item in alt.items:
                    yield from generate_sentences(item, slot_lists)
        elif isinstance(grp, Sequence):
            seq_sentences = map(
                partial(
                    generate_sentences,
                    slot_lists=slot_lists,
                ),
                grp.items,
            )
            sentence_texts = itertools.product(*seq_sentences)
            for sentence_words in sentence_texts:
                yield normalize_whitespace("".join(sentence_words))
        elif isinstance(grp, Permutation):
            # Need to make lists instead because itertools does multiple passes.
            grp_sentences = [
                list(generate_sentences(item, slot_lists)) for item in grp.items
            ]
            for perm_sentences in itertools.permutations(grp_sentences):
                sentence_texts = itertools.product(*perm_sentences)
                for sentence_words in sentence_texts:
                    # Strip added whitespace
                    yield normalize_whitespace("".join(sentence_words)).strip()
        else:
            raise ValueError(f"Unexpected group type: {grp}")
    elif isinstance(expression, ListReference):
        # {list}
        list_ref: ListReference = expression

        list_values = slot_lists.get(list_ref.list_name)
        assert list_values, list_ref

        for list_value in list_values:
            yield list_value


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
