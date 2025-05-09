from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class SentenceBlock:
    sentences: list[str]
    domains: Optional[set[str]] = None


@dataclass
class LanguageData:
    language: str
    sentence_blocks: list[SentenceBlock]
    list_values: dict[str, list[str]]
    wildcard_names: set[str]

    def to_intents_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "lists": {
                **{
                    list_name: {"values": list_values}
                    for list_name, list_values in self.list_values.items()
                },
                **{
                    wildcard_name: {"wildcard": True}
                    for wildcard_name in self.wildcard_names
                },
            },
            "intents": {
                "SpeechToPhrase": {
                    "data": [
                        {
                            "sentences": block.sentences,
                            "requires_context": (
                                {"domain": list(block.domains)} if block.domains else {}
                            ),
                        }
                        for block in self.sentence_blocks
                    ],
                }
            },
        }

    @staticmethod
    def from_dict(data_dict: dict[str, Any]) -> "LanguageData":
        sentence_blocks: list[SentenceBlock] = []

        for sentence_info in data_dict["data"]:
            if isinstance(sentence_info, str):
                sentence_blocks.append(SentenceBlock(sentences=[sentence_info]))
            else:
                sentence_blocks.append(
                    SentenceBlock(
                        sentences=sentence_info["sentences"],
                        domains=set(sentence_info["domains"]),
                    )
                )

        return LanguageData(
            language=data_dict["language"],
            sentence_blocks=sentence_blocks,
            list_values=data_dict.get("lists", {}),
            wildcard_names=set(data_dict.get("wildcards", [])),
        )


def load_shared_lists(lists_dict: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Convert shared lists to hassil format."""
    slot_lists: dict[str, Any] = {}

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

        slot_lists[list_name] = {
            "values": [
                str(number)
                for range_from, range_to, range_step in ranges
                for number in range(range_from, range_to + 1, range_step)
            ]
        }

    return slot_lists
