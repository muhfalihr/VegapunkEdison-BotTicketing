import re

from typing import List, Dict, Any, Union, Optional
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
    # URL = auto()
    LINK = auto()
    IMAGE = auto()
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
            
            # Url, Links and images
            # "url": {"start": "", "end": "", "type": FormatType.URL},
            "link": {"start": "[", "middle": "](", "end": ")", "type": FormatType.LINK},
            "image": {"start": "![", "middle": "](", "end": ")", "type": FormatType.IMAGE},

            # Quotes and horizontal rules
            "blockquote": {"start": "> ", "end": "\n", "type": FormatType.BLOCKQUOTE},
            "hr": {"start": "---", "end": "\n", "type": FormatType.QUOTE},
        }

    def _convert_to_formatting_entity(self, entity: Union[Dict, FormattingEntity]) -> FormattingEntity:
        """Convert dictionary to FormattingEntity if necessary."""
        if isinstance(entity, dict):
            return FormattingEntity(**entity)
        return entity

    def _escape_markdown(self, text_list: List[str], format_ranges: List[TypeEntities]) -> None:
        """Escape only markdown-related _ and * characters outside of normal words."""
        protected_indices = set()
        
        for entity in format_ranges:
            try:
                start_idx = entity.entity[1]
                end_idx = entity.entity[0]
                for i in range(start_idx, end_idx):
                    protected_indices.add(i)
            except Exception:
                continue

        text = ''.join(text_list)

        url_pattern = re.compile(r"\b(?:https?|ftp):\/\/(?=[^ \n]*_)[a-zA-Z0-9.\-]+(?::\d+)?(?:\/[a-zA-Z0-9\-._~%!$&'()*+,;=:@\/?#[\]=]*)?")
        for match in url_pattern.finditer(text):
            start, end = match.start(), match.end()
            for i in range(start, end):
                protected_indices.add(i)

            escaped_url = match.group(0).replace("_", "\\_")
            text_list[start:end] = list(escaped_url)

        for i, char in enumerate(text_list):
            if i in protected_indices:
                continue
            if char == "_" and not (i > 0 and text_list[i-1].isalnum() and i+1 < len(text_list) and text_list[i+1].isalnum()):
                text_list[i] = "\\_"
            elif char == "_" and (i > 0 and text_list[i-1].isalnum() and i+1 < len(text_list) and text_list[i+1].isalnum()):
                text_list[i] = "\\_"
            elif char == "*" and not (i > 0 and text_list[i-1].isalnum() and i+1 < len(text_list) and text_list[i+1].isalnum()):
                text_list[i] = "\\*"

    def escape_undescores(self, text: str) -> str:
        """Escape undescores."""
        return text.replace("_", "\\_")

    def _apply_formatting(self, text_list: List[str], entity: FormattingEntity) -> Optional[TypeEntities]:
        format_type = self.formatting_types.get(entity.type)
        if not format_type:
            return None

        start = entity.offset
        end = start + entity.length
        entity_language = entity.language or "copy"

        if format_type["type"] == FormatType.PRE and entity_language:
            opening = f"{format_type['start']}{entity_language}\n"
            ending = f"\n{format_type['end']}"
            text_list.insert(end, ending)
            text_list.insert(start, opening)
            return TypeEntities(
                type=format_type["type"],
                entity=((end + len(opening) + len(ending)), (start))
            )

        elif format_type["type"] in {FormatType.LINK, FormatType.IMAGE}:
            title = f' "{entity.title}"' if entity.title else ''
            text_list.insert(end, f"{format_type['middle']}{entity.url}{title}{format_type['end']}")
            text_list.insert(start, format_type['start'])
            return TypeEntities(
                type=format_type["type"],
                entity=((end + end + len(format_type['middle'] + entity.url + title + format_type['end'])), (start))
            )

        else:
            text_list.insert(end, format_type['end'])
            text_list.insert(start, format_type['start'])
            return TypeEntities(
                type=format_type["type"],
                entity=((end + end + len(format_type['start']) + len(format_type['end'])), (start))
            )
        
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
        formatted_entities.sort(key=lambda e: e.offset, reverse=True)

        applied_ranges = []
        for entity in formatted_entities:
            applied = self._apply_formatting(text_list, entity)
            if applied:
                applied_ranges.append(applied)

        self._escape_markdown(text_list, applied_ranges)
        return ''.join(text_list)
    
    def escape_markdown(self, text: str):
        # escape_chars = r"\`*_{}[]()#+-.!|>"
        escape_chars = r"*_"
        return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)
    
    def escape_markdownv2(self, text: str):
        return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)
