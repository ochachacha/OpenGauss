---
sidebar_position: 4
title: "Migration to Gauss"
description: "How existing Gauss users should map the old product surface onto Gauss."
---

# Migration to Gauss

Gauss is a product narrowing, not just a rename.

## Renamed

- Primary command: `gauss`
- Default home directory for fresh installs: `~/.gauss/`
- Product identity: **Gauss** by **Math Inc.**

## Still Kept For Compatibility

- `gauss` command alias
- legacy `~/.gauss/` home when it already exists and no `~/.gauss/` has been created yet
- hidden legacy surfaces that still exist in the repository for migration or maintenance work

## Removed From The Default Surface

- bundled skills sync on install/start/update
- dynamic skill slash commands
- `/plan`
- public `/handoff` as a generic terminal-delegation workflow
- default user-managed MCP operations
- broad messaging/gateway/cron/skills-hub presentation in top-level docs and help

## New Primary Flow

1. `gauss`
2. pick the right managed workflow command: `/prove`, `/draft`, `/autoprove`, `/formalize`, or `/autoformalize`
3. work in the managed Lean session that command launches
4. return to the same Gauss session on exit
