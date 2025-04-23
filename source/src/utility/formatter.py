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

    def find_code_blocks(self, text: str) -> List[Tuple[int, int, bool]]:
        """
        Find both inline and multiline code blocks in the text.
        Returns a list of tuples (start, end, is_multiline).
        Properly handles nested code blocks.
        """
        code_blocks = []
        
        # First, find all multiline code blocks
        multiline_blocks = []
        for match in re.finditer(r'```(?:[^\n]*\n)?(.*?)```', text, re.DOTALL):
            multiline_blocks.append((match.start(), match.end()))
            code_blocks.append((match.start(), match.end(), True))
        
        # Helper function to check if a position is inside any multiline block
        def is_inside_multiline_block(pos):
            return any(start <= pos < end for start, end in multiline_blocks)
        
        # Now find inline code blocks, but only if they're not inside multiline blocks
        inline_pattern = r'`([^`]+)`'
        
        i = 0
        while i < len(text):
            # Skip checking inside multiline blocks
            if is_inside_multiline_block(i):
                i += 1
                continue
            
            # Look for inline code block
            match = re.search(inline_pattern, text[i:])
            if not match:
                break
                
            start = i + match.start()
            end = i + match.end()
            
            # Make sure this inline block doesn't overlap with any multiline block
            if not is_inside_multiline_block(start) and not is_inside_multiline_block(end - 1):
                code_blocks.append((start, end, False))
            
            # Move past this match
            i = i + match.end()
        
        return sorted(code_blocks)

    # def _escape_markdown(self, text_list: List[str], format_ranges: List[TypeEntities]) -> None:
    def _escape_markdown(self, text):
        """Escape only markdown-related _ and * characters outside of normal words."""
        code_blocks = self.find_code_blocks(text)
        if not code_blocks:
            # No code blocks found, just escape underscores
            return text.replace("_", "\\_").replace("[", "\\[")
        
        # Process the text in chunks
        result = []
        last_end = 0
        
        for start, end, is_multiline in code_blocks:
            # Add escaped text before this code block
            before_part = text[last_end:start]
            escaped_before = before_part.replace("_", "\\_").replace("[", "\\[")
            result.append(escaped_before)
            
            # Add the code block unchanged - do not escape underscores inside code blocks
            result.append(text[start:end])
            last_end = end
        
        # Handle text after the last code block
        if last_end < len(text):
            final_part = text[last_end:]
            result.append(final_part.replace("_", "\\_").replace("[", "\\["))
        
        return ''.join(result)
    
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

        text = ''.join(text_list)
        text_escaped = self._escape_markdown(text)
        return text_escaped
    
    def escape_markdown(self, text: str) -> str:
        """Escape undescores."""
        return text.replace("_", "\\_").replace("[", "\\[")

    def escape_markdownv2(self, text: str):
        return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)
