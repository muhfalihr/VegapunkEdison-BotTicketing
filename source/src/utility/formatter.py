import re

from typing import List, Dict, Tuple, Union, Optional
from dataclasses import dataclass
from enum import Enum, auto

@dataclass
class FormattingEntity:
    offset: int
    length: int
    type: str
    language: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None

class FormatType(Enum):
    CODE = auto()
    PRE = auto()
    BOLD = auto()
    ITALIC = auto()
    STRIKETHROUGH = auto()
    HEADER = auto()
    QUOTE = auto()
    BLOCKQUOTE = auto()

@dataclass
class TypeEntities:
    type: FormatType
    entity: tuple


class MarkdownFormatter:
    def __init__(self):
        self.formatting_types = {
            # Code formatting
            "code": {"start": "`", "end": "`", "type": FormatType.CODE},
            "pre": {"start": "```", "end": "```", "type": FormatType.PRE},
            
            # Text styling
            "bold": {"start": "*", "end": "*", "type": FormatType.BOLD},
            "italic": {"start": "_", "end": "_", "type": FormatType.ITALIC},
            "strikethrough": {"start": "~~", "end": "~~", "type": FormatType.STRIKETHROUGH},
            
            # Headers
            "h1": {"start": "# ", "end": "\n", "type": FormatType.HEADER},
            "h2": {"start": "## ", "end": "\n", "type": FormatType.HEADER},
            "h3": {"start": "### ", "end": "\n", "type": FormatType.HEADER},
            "h4": {"start": "#### ", "end": "\n", "type": FormatType.HEADER},
            "h5": {"start": "##### ", "end": "\n", "type": FormatType.HEADER},
            "h6": {"start": "###### ", "end": "\n", "type": FormatType.HEADER},
            
            # Quotes and horizontal rules
            "blockquote": {"start": "> ", "end": "\n", "type": FormatType.BLOCKQUOTE},
            "hr": {"start": "---", "end": "\n", "type": FormatType.QUOTE},
        }

    def _convert_to_formatting_entity(self, entity: Union[Dict, FormattingEntity]) -> FormattingEntity:
        """Convert dictionary to FormattingEntity if necessary."""
        if isinstance(entity, dict):
            return FormattingEntity(**entity)
        return entity


    def escape_markdown(self, text: str):
        escape_chars = r'[_*[]'
        return re.sub(escape_chars, lambda match: f'\\{match.group(0)}', text)


    def _apply_formatting(self, text_list: List[str], entity: FormattingEntity, count: int) -> Optional[TypeEntities]:
        format_type = self.formatting_types.get(entity.type)
        if not format_type:
            return None

        start = entity.offset + count
        end = start + entity.length
        entity_language = entity.language or "copy"

        len_start = len(format_type["start"])
        len_end = len(format_type["end"])

        if format_type["type"] == FormatType.PRE and entity_language:
            opening = f"{format_type['start']}{entity_language}\n"
            ending = f"\n{format_type['end']}"
            text_list.insert(end, ending)
            text_list.insert(start, opening)

            len_start = 1
            len_end = 1

            return TypeEntities(
                type=format_type["type"],
                entity=(end, start)
            ), (len_start+len_end)

        else:
            text_list.insert(end, format_type['end'])
            text_list.insert(start, format_type['start'])
            
            _start = start
            _end = _start + len_start + entity.length + len_end

            return TypeEntities(
                type=format_type["type"],
                entity=(_end, _start)
            ), (len_start+len_end)


    def format_text(self, text: str, entities: List[Union[Dict, FormattingEntity]]) -> str:
        """
        Format text according to the provided formatting entities.
        
        Args:
            text: The input text to format
            entities: List of formatting instructions
            
        Returns:
            Formatted text with markdown syntax
        """
        text_list = list(text)
        formatted_entities = [self._convert_to_formatting_entity(e) for e in entities]
        formatted_entities.sort(key=lambda e: e.offset, reverse=False)

        applied_ranges = []
        protected_indices = set()

        count = 0
        for entity in formatted_entities:
            if entity.type != "url":
                applied, plus = self._apply_formatting(text_list, entity, count)
                count += plus
                if applied:
                    applied_ranges.append(applied)

        protected_indices = set()
        for type_entities in applied_ranges:
            for i in range(type_entities.entity[-1], type_entities.entity[0]):
                protected_indices.add(i)

        for i, char in enumerate(text_list):
            if i in protected_indices:
                continue
            text_list[i] = self.escape_markdown(char)

        return ''.join(text_list)
