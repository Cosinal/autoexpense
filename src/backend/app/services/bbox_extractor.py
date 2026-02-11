"""
Bounding box spatial extraction for receipt parsing.

This module implements spatial search algorithms to extract receipt fields
using OCR bounding box coordinates instead of regex patterns.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass
class BboxMatch:
    """A matched field with bbox coordinates and confidence."""
    value: str
    label: str
    label_bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    value_bbox: Tuple[int, int, int, int]
    distance: float
    confidence: float


@dataclass
class Word:
    """A word with its bounding box and metadata."""
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: int
    index: int  # Original index in bbox_data


class BboxExtractor:
    """Extract receipt fields using bounding box spatial search."""

    def __init__(self, bbox_data: Dict[str, List]):
        """
        Args:
            bbox_data: Dict from pytesseract.image_to_data()
                      {'text': [...], 'left': [...], 'top': [...], 'width': [...],
                       'height': [...], 'conf': [...]}
        """
        self.bbox_data = bbox_data
        self.words: List[Word] = []
        self._build_word_index()

    def _build_word_index(self):
        """Build index of words with their bbox coordinates."""
        if not self.bbox_data or 'text' not in self.bbox_data:
            return

        n_boxes = len(self.bbox_data['text'])

        for i in range(n_boxes):
            text = self.bbox_data['text'][i].strip()

            # Skip empty text
            if not text:
                continue

            # Skip very low confidence (likely noise)
            conf = int(self.bbox_data['conf'][i])
            if conf < 0:
                continue

            word = Word(
                text=text,
                x=int(self.bbox_data['left'][i]),
                y=int(self.bbox_data['top'][i]),
                width=int(self.bbox_data['width'][i]),
                height=int(self.bbox_data['height'][i]),
                confidence=conf,
                index=i
            )
            self.words.append(word)

    def find_label(self, keywords: List[str], case_sensitive: bool = False) -> Optional[Word]:
        """
        Find a label keyword in the receipt.

        Args:
            keywords: List of keywords to search (e.g., ["HST", "GST", "Tax"])
            case_sensitive: Whether to match case

        Returns:
            Word if found, None otherwise
        """
        if not case_sensitive:
            keywords = [k.lower() for k in keywords]

        for word in self.words:
            word_text = word.text if case_sensitive else word.text.lower()

            for keyword in keywords:
                if keyword in word_text:
                    return word

        return None

    def find_nearest_number(
        self,
        label_word: Word,
        direction: str = 'right-then-down',
        max_distance_x: int = 300,
        max_distance_y: int = 50,
        pattern: str = r'\d{1,3}(?:,\d{3})*\.\d{2}'
    ) -> Optional[Tuple[str, Word]]:
        """
        Find nearest number to a label within search region.

        Args:
            label_word: The label word to search from
            direction: 'right', 'down', or 'right-then-down'
            max_distance_x: Maximum horizontal distance in pixels
            max_distance_y: Maximum vertical distance in pixels
            pattern: Regex pattern for number format

        Returns:
            Tuple of (matched_value, word) if found, None otherwise
        """
        label_x = label_word.x
        label_y = label_word.y
        label_right = label_x + label_word.width
        label_bottom = label_y + label_word.height

        candidates = []

        for word in self.words:
            # Skip the label itself
            if word.index == label_word.index:
                continue

            # Check if word matches number pattern
            match = re.search(pattern, word.text)
            if not match:
                continue

            matched_value = match.group(0)

            # Calculate spatial relationship
            word_x = word.x
            word_y = word.y

            # Calculate distances
            dx = word_x - label_right  # Distance to the right
            dy = word_y - label_y      # Vertical distance

            # Filter by direction and distance
            if direction == 'right':
                # Must be to the right and roughly on same line
                if dx > 0 and dx <= max_distance_x and abs(dy) <= max_distance_y:
                    # Euclidean distance for scoring
                    distance = (dx ** 2 + dy ** 2) ** 0.5
                    candidates.append((matched_value, word, distance))

            elif direction == 'down':
                # Must be below and roughly aligned
                if dy > 0 and dy <= max_distance_y and abs(dx) <= max_distance_x:
                    distance = (dx ** 2 + dy ** 2) ** 0.5
                    candidates.append((matched_value, word, distance))

            elif direction == 'right-then-down':
                # Prefer right, but also check below
                if dx > 0 and dx <= max_distance_x and abs(dy) <= max_distance_y:
                    # To the right on same line (preferred)
                    distance = (dx ** 2 + dy ** 2) ** 0.5
                    candidates.append((matched_value, word, distance * 0.8))  # Boost right
                elif dy > 0 and dy <= max_distance_y and abs(dx) <= max_distance_x:
                    # Below (fallback)
                    distance = (dx ** 2 + dy ** 2) ** 0.5
                    candidates.append((matched_value, word, distance))

        if not candidates:
            return None

        # Return closest candidate
        candidates.sort(key=lambda x: x[2])
        return (candidates[0][0], candidates[0][1])

    def extract_tax(self) -> Optional[str]:
        """
        Extract tax amount using spatial search.

        Returns:
            Tax amount as string (e.g., "2.65") or None
        """
        # 1. Find HST/GST/Tax label
        label = self.find_label(['HST', 'GST', 'Tax', 'Sales Tax', 'Harmonized'])
        if not label:
            return None

        # 2. Search right, then down for decimal number
        result = self.find_nearest_number(
            label,
            direction='right-then-down',
            max_distance_x=400,  # pixels
            max_distance_y=100,
            pattern=r'\d{1,3}(?:,\d{3})*\.\d{2}'
        )

        if result:
            matched_value, _ = result
            # Clean and return
            return matched_value.replace(',', '')

        return None

    def extract_amount(self) -> Optional[str]:
        """
        Extract total amount using spatial search.

        Returns:
            Total amount as string or None
        """
        # Search for "Total", "Amount", "Grand Total", "Paid", etc.
        label = self.find_label(['Total', 'Amount', 'Paid', 'Grand'])
        if not label:
            return None

        # Search right, then down for amount
        result = self.find_nearest_number(
            label,
            direction='right-then-down',
            max_distance_x=400,
            max_distance_y=100,
            pattern=r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
        )

        if result:
            matched_value, _ = result
            return matched_value.replace(',', '')

        return None

    def extract_all(self) -> Dict[str, Optional[str]]:
        """
        Extract all supported fields using bbox spatial search.

        Returns:
            Dictionary with extracted fields
        """
        return {
            'tax': self.extract_tax(),
            'amount': self.extract_amount(),
        }

    def visualize_words(self, max_words: int = 50) -> str:
        """
        Generate a text visualization of detected words and their positions.
        Useful for debugging.

        Args:
            max_words: Maximum number of words to display

        Returns:
            Multi-line string showing word positions
        """
        lines = []
        lines.append(f"Total words detected: {len(self.words)}")
        lines.append("-" * 80)

        for i, word in enumerate(self.words[:max_words]):
            lines.append(
                f"{i:3d}: '{word.text:20s}' @ ({word.x:4d}, {word.y:4d}) "
                f"[{word.width}x{word.height}] conf={word.confidence}"
            )

        if len(self.words) > max_words:
            lines.append(f"... and {len(self.words) - max_words} more words")

        return "\n".join(lines)
