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
    URL = auto()
    LINK = auto()
    IMAGE = auto()
    QUOTE = auto()
    BLOCKQUOTE = auto()

@dataclass
class TypeEntities:
    type: FormatType
    entity: Dict[tuple, tuple]

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
            "url": {"start": "", "end": "", "type": FormatType.URL},
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

    def _escape_underscores(self, text_list: List[str], format_ranges: List[TypeEntities]) -> None:
        """Escape underscores within the specified ranges."""
        underscore_indices = [i for i, char in enumerate(text_list) if char == "_"]
        if not underscore_indices:
            return
        
        protected_indices = set()
        
        for entity in format_ranges:
            try:
                format_type = entity.type
                start_idx = entity.entity[1][0]
                end_idx = entity.entity[0][-1]

                for idx in underscore_indices:
                    if start_idx <= idx < end_idx:
                        if format_type == FormatType.URL:
                            text_list[idx] = "\\_"
                        protected_indices.add(idx)
            except (IndexError, AttributeError, TypeError) as e:
                continue
        
        for idx in underscore_indices:
            if idx not in protected_indices:
                text_list[idx] = "\\_"
    
    def escape_undescores(self, text: str) -> str:
        """Escape undescores."""
        return text.replace("_", "\\_")

    def _apply_formatting(self, text_list: List[str], entity: FormattingEntity) -> tuple:
        """Apply formatting for a single entity and return the affected range."""
        format_type = self.formatting_types.get(entity.type)
        if not format_type:
            return None

        start = entity.offset
        end = start + entity.length
        start_ = None
        end_ = None

        entity_language = entity.language or "copy"

        if format_type["type"] == FormatType.PRE and entity_language:
            opening = f"{format_type['start']}{entity_language}\n"
            ended = f"\n{format_type['end']}"
            text_list.insert(end, ended)
            end_ = ( ( end + len(ended) ) - 1 )
            text_list.insert(start, opening)
            start_ = ( ( start + len(opening)) - 1 )

        elif format_type["type"] in {FormatType.LINK, FormatType.IMAGE}:
            title = f' "{entity.title}"' if entity.title else ''
            text_list.insert(end, format_type['middle'] + entity.url + title + format_type['end'])
            text_list.insert(start, format_type['start'])
        else:
            text_list.insert(end, format_type['end'])
            text_list.insert(start, format_type['start'])
        
        return TypeEntities(**{
            "type": format_type["type"],
            "entity": ( (end, end_,), (start, start_,) ) if end_ and start_ else ( (end,), (start,) )
        })

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
        
        formatted_entities = [self._convert_to_formatting_entity(entity) for entity in entities]
        formatted_entities.sort(key=lambda x: x.offset, reverse=True)
        
        detail_applyings = []
        for entity in formatted_entities:                  
            detail_applying = self._apply_formatting(text_list, entity)
            if detail_applying:
                detail_applyings.append(detail_applying)
        
        self._escape_underscores(text_list, detail_applyings)
        return ''.join(text_list)
    
    def escape_markdown(self, text: str):
        escape_chars = r"\`*_{}[]()#+-.!|>"
        return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)
    
    def escape_markdownv2(self, text: str):
        return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)
