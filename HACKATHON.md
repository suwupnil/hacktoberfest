# HACKATHON.md

## Team name
Zig2

## Team members
- Swapnil Pradhan
- Akshat Kumar

## Problem statement
Problem 2: Triage that tests the claims

## Models we use and why
- **Qwen 2.5 Coder (7B / 1.5B Instruct)**: Local open-weights model running on Metal GPU via Ollama with KV-cache compression (`q8_0`) and flash attention. Synthesizes minimal Python reproduction scripts for bug reports, analyzes AST execution call paths, and executes in an isolated air-gapped sandbox without cloud dependencies.
- **Moondream (1.8B Local Vision)**: Fast local multimodal model for reading UI error screenshots and inspecting video keyframes.
- **Apple Silicon Native Vision Framework**: Low-latency, sub-20ms OCR on Apple Neural Engine to verify error text claims against repository code symbols and string literals (with cross-platform Tesseract fallback for Linux/Windows).
- **Multi-language AST Parser**: In-memory abstract syntax tree indexer across Python, TypeScript/JavaScript, Go, Rust, Java, and C/C++ to verify claims in microseconds.
