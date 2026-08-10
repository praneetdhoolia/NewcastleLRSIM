#!/usr/bin/env bash
# PreToolUse guard — block creating/updating a pull request whose title or body
# references the claude.ai/code session (CLAUDE.md: no Claude session/attribution in
# commits or PRs).
#
# WHY A HARNESS HOOK (not git): PRs are created through the GitHub MCP tools, which git
# hooks never see. This runs before the MCP tool executes. It is scoped (via the
# matcher in .claude/settings.json) to the PR create/update tools, so grepping the
# whole tool-call payload for the forbidden string is sufficient and safe.
#
# Deny, don't strip: a PreToolUse hook can't reliably rewrite MCP tool input, so it
# exits 2 to block the call and feeds the reason back to the agent, which then
# resubmits a clean title/body.
payload="$(cat)"

if printf '%s' "$payload" | grep -qiE 'https?://claude\.ai/code'; then
  echo "Blocked: this PR title/body references the claude.ai/code session, which this repo forbids (CLAUDE.md — no Claude session link or attribution in commits or PRs). Resubmit the PR without the session reference." >&2
  exit 2
fi
exit 0
