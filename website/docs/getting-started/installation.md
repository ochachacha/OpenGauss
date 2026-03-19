---
sidebar_position: 2
title: "Installation"
description: "Install Gauss on Linux, macOS, or WSL2."
---

# Installation

## Recommended

```bash
curl -fsSL https://raw.githubusercontent.com/math-inc/opengauss-dev/main/scripts/install.sh | bash
```

This installs Gauss into `~/.gauss/` by default, exposes `gauss` as the primary command, and installs the default managed-workflow runtime.

## Compatibility Behavior

- `gauss` is still installed as a compatibility alias
- if you already have `~/.gauss/` and no `~/.gauss/`, Gauss continues using the legacy directory

## After Install

```bash
gauss
```

Inside the CLI, start by selecting a project:

```text
/project init
```

## Windows

Native Windows is not a primary target. Use WSL2 when possible.
