"""
Prompt management for AI operations.
Loads prompts from prompts.json and provides formatting utilities.
"""
import json
from pathlib import Path
from typing import Dict


class PromptManager:
    """Manages AI prompts from external JSON file."""

    def __init__(self, prompts_path: str = "prompts.json"):
        """
        Initialize prompt manager.

        Args:
            prompts_path: Path to prompts.json file (relative to backend directory)
        """
        # Resolve path relative to backend directory
        backend_dir = Path(__file__).parent.parent
        full_path = backend_dir / prompts_path

        if not full_path.exists():
            raise FileNotFoundError(f"Prompts file not found: {full_path}")

        with open(full_path, 'r') as f:
            self._prompts: Dict[str, str] = json.load(f)

    def get(self, prompt_key: str) -> str:
        """
        Get raw prompt by key.

        Args:
            prompt_key: Key from prompts.json

        Returns:
            Raw prompt string

        Raises:
            KeyError: If prompt_key not found
        """
        if prompt_key not in self._prompts:
            raise KeyError(f"Prompt key '{prompt_key}' not found in prompts.json")
        return self._prompts[prompt_key]

    def format(self, prompt_key: str, **kwargs) -> str:
        """
        Get prompt and format with variables.

        Args:
            prompt_key: Key from prompts.json
            **kwargs: Variables to substitute in prompt

        Returns:
            Formatted prompt string

        Raises:
            KeyError: If prompt_key not found
        """
        prompt = self.get(prompt_key)
        return prompt.format(**kwargs)

    def list_keys(self) -> list[str]:
        """Get list of all available prompt keys."""
        return list(self._prompts.keys())


# Global singleton instance
prompts = PromptManager()
