"""Match Speech-to-Phrase sentences with templates in the intents repo."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Optional

from hassil import (
    Intents,
    TextSlotList,
    parse_sentence,
    recognize_all,
    sample_expression,
)
from home_assistant_intents import get_intents
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

_DIR = Path(__file__).parent
_REPO_DIR = _DIR.parent
_GRAPHS_DIR = _REPO_DIR / "graphs"
_SENTENCES_DIR = _REPO_DIR / "sentences"
_STP_DIR = _REPO_DIR / "speech_to_phrase"
_TIMER_INTENTS = {
    "HassStartTimer",
    "HassCancelTimer",
    "HassCancelAllTimers",
    "HassPauseTimer",
    "HassUnpauseTimer",
    "HassIncreaseTimer",
    "HassDecreaseTimer",
    "HassTimerStatus",
}
_CLIMATE_INTENTS = {
    "HassClimateGetTemperature",
    "HassClimateSetTemperature",
}
_DEFAULT_NAME_DOMAINS = {"light", "switch", "fan", "media_player", "input_boolean"}
_GET_STATE_DOMAINS = {"sensor"}
_RECOGNIZE_NAME_DOMAINS = {
    "light",
    "switch",
    "fan",
    "media_player",
    "input_boolean",
    "lock",
    "cover",
    "sensor",
    "scene",
    "script",
    "weather",
    "climate",
    "binary_sensor",
    "valve",
    "vacuum",
    "todo",
}

_LOGGER = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", default=_STP_DIR / "sentences", help="Path to output directory"
    )
    parser.add_argument("--language", help="Only match sentences for language")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    yaml = YAML()
    yaml.default_flow_style = False
    yaml.indent(sequence=4, offset=2)

    slot_lists = {
        "area": TextSlotList.from_strings(("{area}",), allow_template=False),
        "floor": TextSlotList.from_strings(("{floor}",), allow_template=False),
    }
    intent_context = {"area": "{area}"}

    with open(_STP_DIR / "shared_lists.yaml", "r", encoding="utf-8") as lists_file:
        lists_dict = yaml.load(lists_file)
        for list_name, list_info in lists_dict.items():
            ranges = []
            if list_range := list_info.get("range"):
                ranges.append(
                    (list_range["from"], list_range["to"], list_range.get("step", 1))
                )
            elif list_multi_range := list_info.get("multi_range"):
                for list_range in list_multi_range:
                    ranges.append(
                        (
                            list_range["from"],
                            list_range["to"],
                            list_range.get("step", 1),
                        )
                    )

            slot_lists[list_name] = TextSlotList.from_strings(
                (
                    str(number)
                    for range_from, range_to, range_step in ranges
                    for number in range(range_from, range_to + 1, range_step)
                ),
                allow_template=False,
                name=list_name,
            )

    errors = []
    for sentences_path in _SENTENCES_DIR.glob("*.yaml"):
        language = sentences_path.stem
        lang_has_errors = False

        if args.language and (language != args.language):
            continue

        lang_intents_dict = get_intents(language)
        if not lang_intents_dict:
            errors.append(f"{language}: no intents")
            lang_has_errors = True
            continue

        lang_intents = Intents.from_dict(lang_intents_dict)

        possible_name_domains: set[str] = set()
        for intent in lang_intents.intents.values():
            for intent_data in intent.data:
                if not intent_data.requires_context:
                    continue

                requires_domain = intent_data.requires_context.get("domain")
                if not requires_domain:
                    continue

                if isinstance(requires_domain, str):
                    # Single domain
                    possible_name_domains.add(requires_domain)
                else:
                    # Multiple domains
                    possible_name_domains.update(requires_domain)

        ignored_name_domains = possible_name_domains - _RECOGNIZE_NAME_DOMAINS
        if ignored_name_domains:
            _LOGGER.info("Ignored name domains: %s", ignored_name_domains)

        # Create a {name} entity for each possible domain.
        # This will match because with generate examples with
        # expand_lists=False, so {name} will be the actual entity name.
        lang_slot_lists = {
            "name": TextSlotList.from_tuples(
                (
                    ("{name}", "{name}", {"domain": domain})
                    for domain in _RECOGNIZE_NAME_DOMAINS
                ),
                allow_template=False,
                name="name",
            ),
            **slot_lists,
        }

        lang_output_dict = {
            "language": language,
            "intents": {"SpeechToPhrase": {"data": []}},
        }
        lang_stp_data = lang_output_dict["intents"]["SpeechToPhrase"]["data"]

        with open(sentences_path, "r", encoding="utf-8") as f:
            sentences_dict = yaml.load(f)
            sen_slot_lists: Optional[dict[str, Any]] = None
            for list_name, list_values in sentences_dict.get("lists", {}).items():
                if not list_values:
                    continue

                if sen_slot_lists is None:
                    sen_slot_lists = dict(lang_slot_lists)

                sen_slot_lists[list_name] = TextSlotList.from_strings(
                    list_values, name="name"
                )

            if sen_slot_lists is None:
                sen_slot_lists = lang_slot_lists

            lang_output_dict["lists"] = {
                list_name: {"values": [v.text_in.text for v in slot_list.values]}
                for list_name, slot_list in sen_slot_lists.items()
                if list_name not in ("name", "area", "floor")
            }

            for sentence_text in sentences_dict["sentences"]:
                sentence = parse_sentence(sentence_text, keep_text=True)
                missing_texts = []
                name_domains: set[str] = set()

                for example_text in sample_expression(
                    sentence.expression, sen_slot_lists
                ):
                    found_result = False
                    for result in recognize_all(
                        example_text,
                        lang_intents,
                        slot_lists=sen_slot_lists,
                        intent_context=intent_context,
                    ):
                        found_result = True

                        if "name" not in result.entities:
                            continue

                        if result.intent.name in _TIMER_INTENTS:
                            # Ignore timer names since they aren't real entities
                            continue

                        if result.intent.name in _CLIMATE_INTENTS:
                            # Fix climate intents (broken in intents repo)
                            name_domains = {"climate"}
                            continue

                        if result.intent_data.requires_context:
                            requires_domain = result.intent_data.requires_context.get(
                                "domain"
                            )
                            if not requires_domain:
                                continue

                            if isinstance(requires_domain, str):
                                # Single domain
                                result_name_domains = {requires_domain}
                            else:
                                # Multiple domains
                                result_name_domains = set(requires_domain)
                        else:
                            # Default name domains.
                            # These should really be explicit in the intents repo.
                            if result.intent.name == "HassGetState":
                                result_name_domains = _GET_STATE_DOMAINS
                            else:
                                result_name_domains = _DEFAULT_NAME_DOMAINS

                        name_domains.update(result_name_domains)

                    if not found_result:
                        missing_texts.append(example_text)

                if missing_texts:
                    errors.append(
                        f"{language}: {sentence_text} missing {missing_texts}"
                    )
                    lang_has_errors = True

                if name_domains:
                    lang_stp_data.append(
                        {
                            "sentences": [sentence_text],
                            "requires_context": {"domain": list(name_domains)},
                        }
                    )
                else:
                    lang_stp_data.append({"sentences": [sentence_text]})

        if not lang_has_errors:
            with open(
                output_dir / f"{language}.yaml", "w", encoding="utf-8"
            ) as output_file:
                yaml.dump(quote_strings(lang_output_dict), output_file)

    if errors:
        for error_message in errors:
            _LOGGER.error(error_message)

        return 1

    return 0


def quote_strings(data):
    if isinstance(data, str):
        return DoubleQuotedScalarString(data)
    elif isinstance(data, list):
        return [quote_strings(item) for item in data]
    elif isinstance(data, dict):
        return {key: quote_strings(value) for key, value in data.items()}
    else:
        return data


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
