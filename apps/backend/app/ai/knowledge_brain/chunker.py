import PyPDF2
from typing import List

class DocumentChunker:
    """Handles text chunking and PDF text extraction."""

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Splits long text into manageable overlapping chunks.

        Uses word-based splitting to ensure words aren't cut in half,
        keeping overlap to preserve context between chunks.

        Args:
            text: The input text to chunk
            chunk_size: Target size for each chunk in characters
            overlap: Number of characters to overlap between chunks

        Returns:
            List of text chunks
        """
        if not text:
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            # Calculate end position for this chunk
            end = min(start + chunk_size, text_length)

            # If we're not at the end of the text, try to find a word boundary
            if end < text_length:
                # Look backwards from end to find a space
                while end > start and text[end] != ' ':
                    end -= 1

                # If no space found, force split at chunk_size
                if end == start:
                    end = min(start + chunk_size, text_length)

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Keep track of where start was so we can guarantee progress
            previous_start = start

            # Move start position with overlap
            start = end - overlap

            # GUARANTEE WE MAKE PROGRESS
            # If our new start is somehow the same or less than our old start,
            # we force it forward by forcing it to just be `end`.
            # This prevents infinite loops.
            if start <= previous_start:
                start = end

        return chunks

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """
        Extracts text from a PDF file using PyPDF2.

        Args:
            file_path: Path to the PDF file

        Returns:
            Full text content of the PDF
        """
        text = ""

        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)

            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"

        return text
