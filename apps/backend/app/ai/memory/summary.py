# apps/backend/app/ai/memory/summary.py
"""
Memory Summarization - Provider-independent memory summarization implementation.

This module implements memory summarization using the LLM interface:
- Generate summaries of individual memories
- Batch summarization of multiple memories
- Extract key insights from memory groups
- Provider-independent operation
"""

import logging
from typing import List, Optional

from app.ai.llm.interface import LLMConfig, LLMMessage, LLMProviderInterface
from app.ai.memory.interfaces import (
    IMemorySummarizer,
    MemoryRecord,
)

logger = logging.getLogger(__name__)


class MemorySummarizer(IMemorySummarizer):
    """
    Memory summarization implementation.

    Provides summarization capabilities using the LLM interface:
    - Single memory summarization
    - Batch memory summarization
    - Key insight extraction
    - Provider-independent operation
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProviderInterface] = None,
        max_summary_length: int = 500,
    ):
        """
        Initialize the memory summarizer.

        Args:
            llm_provider: Optional LLM provider (uses mock if None)
            max_summary_length: Maximum length of generated summaries
        """
        self.llm_provider = llm_provider
        self.max_summary_length = max_summary_length

        logger.info(f"Initialized MemorySummarizer with max_summary_length={max_summary_length}")

    async def summarize_memory(self, memory: MemoryRecord) -> str:
        """
        Generate a summary of a single memory.

        Creates a concise summary that captures the key information
        from the memory while reducing its size.
        """
        try:
            # If memory is already short, return as-is
            if len(memory.content) <= self.max_summary_length:
                return memory.content

            # If no LLM provider, use simple truncation
            if not self.llm_provider:
                return self._simple_truncate(memory.content)

            # Generate summary using LLM
            prompt = self._build_summary_prompt(memory.content, single=True)

            messages = [
                LLMMessage(
                    role="system",
                    content="You are a helpful assistant that summarizes text concisely.",
                ),
                LLMMessage(role="user", content=prompt),
            ]

            config = LLMConfig(
                temperature=0.3,  # Low temperature for consistent summaries
                max_tokens=self.max_summary_length,
            )

            response = await self.llm_provider.generate(messages, config)

            if response and response.content:
                summary = response.content.strip()
                logger.debug(f"Generated summary for memory {memory.id}: {len(summary)} chars")
                return summary
            else:
                # Fallback to simple truncation
                return self._simple_truncate(memory.content)

        except Exception as e:
            logger.error(f"Failed to summarize memory {memory.id}: {e}")
            return self._simple_truncate(memory.content)

    async def summarize_memories_batch(self, memories: List[MemoryRecord]) -> List[str]:
        """
        Generate summaries for multiple memories.

        Processes memories in batch for efficiency.
        """
        summaries = []

        for memory in memories:
            try:
                summary = await self.summarize_memory(memory)
                summaries.append(summary)
            except Exception as e:
                logger.error(f"Failed to summarize memory {memory.id} in batch: {e}")
                summaries.append(memory.content)  # Fallback to original

        logger.debug(f"Generated {len(summaries)} summaries in batch")
        return summaries

    async def extract_key_insights(self, memories: List[MemoryRecord]) -> List[str]:
        """
        Extract key insights from a set of memories.

        Analyzes multiple memories to extract:
        - Common themes
        - Important patterns
        - Notable events
        - Actionable insights
        """
        try:
            if not memories:
                return []

            # If no LLM provider, use simple extraction
            if not self.llm_provider:
                return self._simple_insight_extraction(memories)

            # Combine memory contents
            combined_content = "\n\n".join(
                [f"[{mem.memory_type.value}] {mem.content}" for mem in memories]
            )

            # Build insight extraction prompt
            prompt = self._build_insight_prompt(combined_content, len(memories))

            messages = [
                LLMMessage(
                    role="system",
                    content="You are a helpful assistant that extracts key insights from text.",
                ),
                LLMMessage(role="user", content=prompt),
            ]

            config = LLMConfig(
                temperature=0.4,
                max_tokens=800,
            )

            response = await self.llm_provider.generate(messages, config)

            if response and response.content:
                insights = self._parse_insights(response.content)
                logger.debug(f"Extracted {len(insights)} insights from {len(memories)} memories")
                return insights
            else:
                return self._simple_insight_extraction(memories)

        except Exception as e:
            logger.error(f"Failed to extract insights from memories: {e}")
            return self._simple_insight_extraction(memories)

    def _simple_truncate(self, content: str) -> str:
        """
        Simple truncation fallback when LLM is not available.

        Preserves sentence boundaries where possible.
        """
        if len(content) <= self.max_summary_length:
            return content

        # Find the last sentence boundary within limit
        truncated = content[: self.max_summary_length]

        # Try to end at a sentence boundary
        for separator in [". ", "! ", "? ", "\n"]:
            last_sep = truncated.rfind(separator)
            if last_sep > self.max_summary_length * 0.7:  # At least 70% of limit
                truncated = truncated[: last_sep + 1]
                break

        return truncated + "..."

    def _simple_insight_extraction(self, memories: List[MemoryRecord]) -> List[str]:
        """
        Simple insight extraction fallback when LLM is not available.

        Extracts basic insights based on memory metadata and content.
        """
        insights = []

        # Count memory types
        type_counts = {}
        for memory in memories:
            type_counts[memory.memory_type] = type_counts.get(memory.memory_type, 0) + 1

        # Add type distribution insight
        if type_counts:
            most_common = max(type_counts, key=type_counts.get)
            insights.append(
                f"Most common memory type: {most_common.value} "
                f"({type_counts[most_common]} memories)"
            )

        # Extract high-importance memories
        high_importance = [
            m for m in memories if m.metadata.importance.value in ["critical", "high"]
        ]
        if high_importance:
            insights.append(f"Found {len(high_importance)} high-importance memories")

        # Extract content themes (simple keyword-based)
        all_content = " ".join(m.content.lower() for m in memories)
        common_words = {}
        for word in all_content.split():
            if len(word) > 4:  # Ignore short words
                common_words[word] = common_words.get(word, 0) + 1

        if common_words:
            top_words = sorted(common_words, key=common_words.get, reverse=True)[:5]
            insights.append(f"Common themes: {', '.join(top_words)}")

        return insights

    def _build_summary_prompt(self, content: str, single: bool = True) -> str:
        """Build a prompt for memory summarization."""
        if single:
            return (
                "Please summarize the following text concisely. "
                "Capture the key information and main points. "
                "Keep the summary under 500 characters.\n\n"
                f"Text:\n{content}"
            )
        else:
            return (
                "Please summarize the following texts combined. "
                "Capture the key information and main points from all texts. "
                "Keep the summary under 500 characters.\n\n"
                f"Texts:\n{content}"
            )

    def _build_insight_prompt(self, combined_content: str, memory_count: int) -> str:
        """Build a prompt for insight extraction."""
        return (
            f"Please extract 3-5 key insights from the following {memory_count} memories. "
            "Focus on:\n"
            "- Common themes or patterns\n"
            "- Important events or information\n"
            "- Actionable insights\n"
            "- Notable changes over time\n\n"
            "Format each insight on a separate line.\n\n"
            f"Memories:\n{combined_content}"
        )

    def _parse_insights(self, response_content: str) -> List[str]:
        """Parse insights from LLM response."""
        # Split by common list markers
        lines = response_content.strip().split("\n")

        insights = []
        for line in lines:
            # Remove common list markers
            cleaned = line.strip()
            for prefix in ["-", "*", "•", "1.", "2.", "3.", "4.", "5."]:
                if cleaned.startswith(prefix):
                    cleaned = cleaned[len(prefix) :].strip()
                    break

            if cleaned and len(cleaned) > 10:  # Filter out very short lines
                insights.append(cleaned)

        return insights[:5]  # Limit to 5 insights

    async def generate_consolidated_summary(
        self, memories: List[MemoryRecord], max_length: int = 1000
    ) -> str:
        """
        Generate a consolidated summary from multiple memories.

        Creates a comprehensive summary that captures information from
        all memories while avoiding redundancy.
        """
        try:
            if not memories:
                return ""

            # If no LLM provider, concatenate individual summaries
            if not self.llm_provider:
                individual_summaries = await self.summarize_memories_batch(memories)
                return " ".join(individual_summaries)[:max_length]

            # Combine memory contents with metadata
            memory_descriptions = []
            for memory in memories:
                desc = f"[{memory.memory_type.value} - {memory.created_at.date()}]"
                desc += f" {memory.content}"
                memory_descriptions.append(desc)

            combined_content = "\n\n".join(memory_descriptions)

            # Build consolidated summary prompt
            prompt = (
                f"Please create a consolidated summary from the following {len(memories)} memories. "
                f"Capture the key information from all memories while avoiding redundancy. "
                f"Keep the summary under {max_length} characters.\n\n"
                f"Memories:\n{combined_content}"
            )

            messages = [
                LLMMessage(
                    role="system",
                    content="You are a helpful assistant that creates consolidated summaries.",
                ),
                LLMMessage(role="user", content=prompt),
            ]

            config = LLMConfig(
                temperature=0.3,
                max_tokens=max_length,
            )

            response = await self.llm_provider.generate(messages, config)

            if response and response.content:
                summary = response.content.strip()
                logger.debug(
                    f"Generated consolidated summary for {len(memories)} memories: "
                    f"{len(summary)} chars"
                )
                return summary
            else:
                # Fallback to concatenating individual summaries
                individual_summaries = await self.summarize_memories_batch(memories)
                return " ".join(individual_summaries)[:max_length]

        except Exception as e:
            logger.error(f"Failed to generate consolidated summary: {e}")
            # Fallback to concatenating individual summaries
            individual_summaries = await self.summarize_memories_batch(memories)
            return " ".join(individual_summaries)[:max_length]
