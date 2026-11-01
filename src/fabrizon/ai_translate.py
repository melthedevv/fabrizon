"""Optional AI-assisted translation for stage 4 helper bodies.

Users can provide an NVIDIA API key (or OpenAI-compatible endpoint) to have an LLM
translate the `// TODO(stage 4):` comments into actual Rust code. The LLM receives:
- The target's Rust signature (from Candidate)
- The Java handler source (from BRIEF.md)
- The partially translated helper with TODO comments
- The surrounding context

The LLM output is validated by `rustc --emit=metadata` before being inserted.
"""

from __future__ import annotations

import os
import json
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass
from typing import Optional

try:
    from openai import OpenAI
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False
    OpenAI = None  # type: ignore


@dataclass
class AIConfig:
    api_key: str
    base_url: str = "https://integrate.api.nvidia.com/v1"
    model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    temperature: float = 0.2
    max_tokens: int = 8192

    @staticmethod
    def from_env() -> Optional["AIConfig"]:
        key = os.environ.get("FABRIZON_NVIDIA_API_KEY") or os.environ.get("NVIDIA_API_KEY")
        if not key:
            return None
        return AIConfig(
            api_key=key,
            base_url=os.environ.get("FABRIZON_NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            model=os.environ.get("FABRIZON_NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b"),
        )

    @staticmethod
    def from_file(path: str) -> Optional["AIConfig"]:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return AIConfig(
                api_key=data["api_key"],
                base_url=data.get("base_url", "https://integrate.api.nvidia.com/v1"),
                model=data.get("model", "nvidia/nemotron-3-ultra-550b-a55b"),
                temperature=data.get("temperature", 0.2),
                max_tokens=data.get("max_tokens", 8192),
            )
        except Exception:
            return None


_SYSTEM_PROMPT = """You are an expert Rust programmer helping port a Minecraft Fabric mod to Horizon (a Rust rewrite of Minecraft).

You will be given:
1. The target Horizon function signature (the hook point)
2. The original Java handler code (from the Fabric mod)
3. A partially translated Rust helper with `// TODO(stage 4):` comments marking what the mechanical translator couldn't handle

Your task: Replace the TODO comments with correct, idiomatic Rust that compiles against the Horizon codebase.

Rules:
- The helper must be a private, synchronous, safe `fn` with no attributes, no generics, no `self` receiver
- Parameter names and types must match the helper signature exactly
- Use only the Horizon APIs implied by the target signature and the Java code
- Do NOT invent new types, traits, or modules — use what Horizon provides
- Return the COMPLETE helper function (not just the changed lines)
- No markdown, no explanation — only the Rust code
"""


def _build_prompt(target_sig: str, java_code: str, partial_helper: str) -> str:
    return f"""Target Horizon signature:
{target_sig}

Original Java handler:
```java
{java_code}
```

Partially translated helper (replace TODO comments):
```rust
{partial_helper}
```"""


def _validate_rust(code: str) -> bool:
    """Quick compile check using rustc --emit=metadata."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rs", delete=False, encoding="utf-8") as f:
        f.write(code)
        path = f.name
    try:
        result = subprocess.run(
            ["rustc", "--edition", "2021", "--crate-type", "lib", "--emit=metadata", "-o", "/dev/null", path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


def translate_with_ai(config: AIConfig, target_sig: str, java_code: str, partial_helper: str) -> Optional[str]:
    """Call the LLM to fill in TODO comments. Returns complete helper or None on failure."""
    if not _HAS_OPENAI:
        return None

    client = OpenAI(base_url=config.base_url, api_key=config.api_key)

    try:
        completion = client.chat.completions.create(
            model=config.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_prompt(target_sig, java_code, partial_helper)},
            ],
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            stream=False,
        )
        content = completion.choices[0].message.content
        if not content:
            return None

        # Extract code block if present
        if "```rust" in content:
            content = content.split("```rust")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        content = content.strip()

        # Validate
        if _validate_rust(content):
            return content
        return None

    except Exception:
        return None