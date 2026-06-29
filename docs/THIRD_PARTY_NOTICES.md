# Third Party Notices

This file records third-party projects, ideas, and licenses that are relevant
to Ragent-Py.

## nageoffer/ragent

- Source: <https://github.com/nageoffer/ragent>
- Usage: architecture reference and engineering inspiration
- Scope: layered architecture, Agentic RAG design ideas, streaming RAG pipeline concepts, trace and reliability patterns
- Note: Ragent-Py is a Python implementation inspired by the architecture. It is not a line-by-line port of the Java codebase.

## xerrors/Yuxi

- Source: <https://github.com/xerrors/Yuxi>
- Version referenced: v0.7.0
- License: MIT
- Usage in Ragent-Py: selected frontend layout patterns, workspace structure ideas, UI interaction references, and adapted visual styles for a lightweight RAG-only console
- Explicit exclusions: MCP, Skills, SubAgents, Sandbox, LangGraph orchestration, multi-tenancy, auth, permission management, model routing, Rerank configuration, Knowledge Graph, Mind Map, and RAG evaluation features

## Yuxi MIT License

```text
MIT License

Copyright (c) [xerrors](https://github.com/xerrors)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Runtime Dependencies

Backend and frontend dependencies are listed in `pyproject.toml` and
`web/package.json`. Each dependency remains under its own upstream license.
