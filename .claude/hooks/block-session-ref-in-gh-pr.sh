#!/usr/bin/env bash
# PreToolUse guard — block a `gh pr create` / `gh pr edit` whose title or body
# references the claude.ai/code session (CLAUDE.md: no Claude session link in PRs).
#
# Companion to block-session-ref-in-pr.sh: that one covers the GitHub MCP path; this
# covers the `gh` CLI path, which is reachable because the sandbox allow-lists
# api.github.com.
#
# Matched (in .claude/settings.json) on the Bash tool, so it sees every Bash call and
# must SELF-SCOPE: act only on gh PR-writing commands, leaving everything else alone.
# In particular a `git commit` carrying the link is handled by the commit-msg hook
# (strip), not blocked here, and routine commands that merely mention the URL are
# untouched.
#
# Deny, don't strip: exit 2 to block the call and feed the reason back to the agent.
payload="$(cat)"

if printf '%s' "$payload" | grep -qiE 'gh[[:space:]]+pr[[:space:]]+(create|edit)\b' \
   && printf '%s' "$payload" | grep -qiE 'https?://claude\.ai/code'; then
  echo "Blocked: this 'gh pr' command's title/body references the claude.ai/code session, which this repo forbids (CLAUDE.md — no Claude session link in commits or PRs). Re-run gh pr create/edit without the session reference." >&2
  exit 2
fi
exit 0
