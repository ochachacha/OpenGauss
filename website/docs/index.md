---
sidebar_position: 1
title: "Gauss Documentation"
description: "Gauss is a focused Lean workflow workspace built around managed CLI-agent sessions."
---

# Gauss

Gauss is a narrow product on purpose. It is not trying to be a general agent platform anymore. The default experience is:

1. start `gauss`
2. pick `/prove`, `/draft`, `/autoprove`, `/formalize`, or `/autoformalize`
3. enter the managed Lean session for that workflow
4. return to the same Gauss session when that child exits

## Core Ideas

- **Lean workflow menu**: guided proving, drafting, autonomous proving, interactive formalization, and autonomous formalization
- **Managed Lean runtime**: Gauss stages the Lean 4 plugin and Lean LSP MCP config for you
- **Minimal public surface**: bundled skills and user-managed MCP are off by default
- **Recoverable session model**: the selected backend takes over the current terminal, then Gauss redraws the same session on return

## Start Here

- [Quickstart](/docs/getting-started/quickstart)
- [Installation](/docs/getting-started/installation)
- [Migration to Gauss](/docs/getting-started/migration-to-gauss)
- [Slash Commands](/docs/reference/slash-commands)
