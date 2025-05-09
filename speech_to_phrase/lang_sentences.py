import re
from dataclasses import dataclass
from typing import Any, Optional

from hassil import SlotList, TextChunk, TextSlotList, TextSlotValue


@dataclass
class SentenceBlock:
    sentences: list[str]
    domains: Optional[set[str]] = None


@dataclass
class Transformation:
    outputs: list[str]
    match_regex: Optional[re.Pattern] = None


@dataclass
class TransformedList:
    source_list_name: str
    transformations: list[Transformation]

    def apply(self, value: str) -> list[str]:
        for transformation in self.transformations:
            if transformation.match_regex is not None:
                if not transformation.match_regex.search(value):
                    continue

            return [
                output_str.format(value=value) for output_str in transformation.outputs
            ]

        return [value]


@dataclass
class LanguageData:
    language: str
    sentence_blocks: list[SentenceBlock]
    list_values: dict[str, list[str]]
    wildcard_names: set[str]
    transformed_lists: dict[str, TransformedList]

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
        transformed_lists: dict[str, TransformedList] = {}

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

        transformations: dict[str, list[Transformation]] = {}
        for tr_name, tr_info in data_dict.get("transformations", {}).items():
            tr_list: list[Transformation] = []
            for tr_dict in tr_info:
                match_regex = tr_dict.get("match")
                tr_list.append(
                    Transformation(
                        outputs=tr_dict["outputs"],
                        match_regex=re.compile(match_regex) if match_regex else None,
                    )
                )

            transformations[tr_name] = tr_list

        for tr_list_name, tr_list_info in data_dict.get(
            "transformed_lists", {}
        ).items():
            transformed_lists[tr_list_name] = TransformedList(
                source_list_name=tr_list_info["source"],
                transformations=[
                    tr
                    for tr_name in tr_list_info["transformations"]
                    for tr in transformations[tr_name]
                ],
            )

        return LanguageData(
            language=data_dict["language"],
            sentence_blocks=sentence_blocks,
            list_values=data_dict.get("lists", {}),
            wildcard_names=set(data_dict.get("wildcards", [])),
            transformed_lists=transformed_lists,
        )

    def get_transformed_lists(
        self, slot_lists: dict[str, SlotList]
    ) -> dict[str, TextSlotList]:
        tr_slot_lists: dict[str, TextSlotList] = {}

        for list_name, slot_list in slot_lists.items():
            if not isinstance(slot_list, TextSlotList):
                continue

            for tr_list_name, tr_list in self.transformed_lists.items():
                if tr_list.source_list_name != list_name:
                    continue

                tr_slot_lists[tr_list_name] = TextSlotList(
                    name=tr_list_name,
                    values=[
                        TextSlotValue(
                            TextChunk(output_value),
                            output_value,
                            context=value.context,
                            metadata=value.metadata,
                        )
                        for value in slot_list.values
                        for output_value in tr_list.apply(value.text_in.text)
                    ],
                )

        return tr_slot_lists


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
