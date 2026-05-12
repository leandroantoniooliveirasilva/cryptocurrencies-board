"""Shared CLI agent abstraction for qualitative/supply scoring.

Selects between Claude Code (``claude --print``) and Cursor Agent
(``cursor-agent --print``) via ``LLM_AGENT_CLI`` (default: ``claude``).

Env vars:
  LLM_AGENT_CLI         "claude" (default) | "cursor"
  CLAUDE_AGENT_BIN      override claude binary path (default: ``claude``)
  CLAUDE_AGENT_MODEL    claude model alias (default: ``sonnet``)
  CLAUDE_AGENT_TOOLS    comma-separated built-in tools to enable
                        (default: ``WebSearch,WebFetch`` — disables Write/Edit
                        so output must come on stdout)
  CURSOR_AGENT_BIN      override cursor-agent binary (default: ``cursor-agent``)
  CURSOR_AGENT_MODEL    cursor-agent model (default: ``auto``)
"""

from __future__ import annotations

import os


def _selected_cli() -> str:
    value = os.environ.get('LLM_AGENT_CLI', 'claude').strip().lower()
    return 'cursor' if value in ('cursor', 'cursor-agent') else 'claude'


def build_agent_command(prompt: str) -> list[str]:
    """Build the argv for invoking the selected agent CLI in non-interactive mode."""
    if _selected_cli() == 'cursor':
        binary = os.environ.get('CURSOR_AGENT_BIN', 'cursor-agent')
        model = os.environ.get('CURSOR_AGENT_MODEL', 'auto')
        return [binary, '--print', '--trust', '--force', '--model', model, prompt]

    binary = os.environ.get('CLAUDE_AGENT_BIN', 'claude')
    model = os.environ.get('CLAUDE_AGENT_MODEL', 'sonnet')
    tools = os.environ.get('CLAUDE_AGENT_TOOLS', 'WebSearch,WebFetch')
    return [
        binary,
        '--print',
        '--dangerously-skip-permissions',
        '--tools', tools,
        '--model', model,
        prompt,
    ]


def agent_label() -> str:
    """Human-readable label of the selected CLI (for logging)."""
    return 'Cursor Agent' if _selected_cli() == 'cursor' else 'Claude Code'


def agent_install_hint() -> str:
    """Install / auth hint for the selected CLI."""
    if _selected_cli() == 'cursor':
        return 'Install Cursor Agent CLI and run `cursor-agent login`.'
    return 'Install Claude Code CLI and run `claude login` (or set ANTHROPIC_API_KEY).'
