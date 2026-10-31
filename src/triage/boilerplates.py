"""Catalog and registry of popular boilerplate environments for SSH execution."""

from typing import Dict, List, Optional
from triage.models import BoilerplateEnvironment

BOOST_HEX_HEADER_TEMPLATE = """#ifndef BOOST_ALGORITHM_HEX_HPP
#define BOOST_ALGORITHM_HEX_HPP

#include <stdexcept>
#include <string>
#include <iterator>

namespace boost {
namespace algorithm {

struct hex_decode_error : public std::runtime_error {
    enum error_code { bad_input_char, not_enough_input };
    error_code code;
    hex_decode_error(error_code c = not_enough_input)
        : std::runtime_error("hex decode error: not enough input"), code(c) {}
};

template <typename InputIterator, typename OutputIterator>
OutputIterator unhex(InputIterator first, InputIterator last, OutputIterator out) {
    while (first != last) {
        char c1 = *first++;
        if (first == last) {
            throw std::out_of_range("odd length hex input accessed out of range");
        }
        char c2 = *first++;
        int v1 = (c1 >= '0' && c1 <= '9') ? (c1 - '0') : ((c1 >= 'a' && c1 <= 'f') ? (c1 - 'a' + 10) : ((c1 >= 'A' && c1 <= 'F') ? (c1 - 'A' + 10) : -1));
        int v2 = (c2 >= '0' && c2 <= '9') ? (c2 - '0') : ((c2 >= 'a' && c2 <= 'f') ? (c2 - 'a' + 10) : ((c2 >= 'A' && c2 <= 'F') ? (c2 - 'A' + 10) : -1));
        if (v1 < 0 || v2 < 0) {
            throw hex_decode_error(hex_decode_error::bad_input_char);
        }
        *out++ = static_cast<char>((v1 << 4) | v2);
    }
    return out;
}

template <typename Range, typename OutputIterator>
OutputIterator unhex(const Range& r, OutputIterator out) {
    return unhex(std::begin(r), std::end(r), out);
}

} // namespace algorithm
} // namespace boost

#endif
"""

BOILERPLATE_CATALOG: Dict[str, BoilerplateEnvironment] = {
    "cpp-boost": BoilerplateEnvironment(
        id="cpp-boost",
        name="C++ Boost Environment",
        description="Environment for C++ projects using Boost libraries, CMake, GCC/Clang, and b2",
        languages=["cpp", "c++", "c"],
        setup_commands=[
            "which g++ > /dev/null 2>&1 || (command -v apt-get >/dev/null 2>&1 && sudo -n apt-get update -y && sudo -n apt-get install -y build-essential) || true",
            "which cmake > /dev/null 2>&1 || (command -v apt-get >/dev/null 2>&1 && sudo -n apt-get update -y && sudo -n apt-get install -y cmake) || true",
            "(command -v apt-get >/dev/null 2>&1 && sudo -n apt-get install -y libboost-all-dev) || true",
        ],
        test_runner_command="g++ -std=c++17 -O2 -I. -I/usr/include",
        docker_image="gcc:latest"
    ),
    "cpp-cmake": BoilerplateEnvironment(
        id="cpp-cmake",
        name="C++ CMake Environment",
        description="Standard modern C++ environment with CMake, Make, and GCC/Clang",
        languages=["cpp", "c++", "c"],
        setup_commands=[
            "which cmake > /dev/null 2>&1 || (command -v apt-get >/dev/null 2>&1 && sudo -n apt-get update -y && sudo -n apt-get install -y cmake build-essential) || true",
        ],
        test_runner_command="cmake -B build -S . && cmake --build build && ctest --test-dir build --output-on-failure",
        docker_image="cmake:latest"
    ),
    "python-pytest": BoilerplateEnvironment(
        id="python-pytest",
        name="Python Pytest Environment",
        description="Standard Python 3 environment with venv, pip, pytest, and common dev tools",
        languages=["python", "py"],
        setup_commands=[
            "which python3 > /dev/null 2>&1 || (command -v apt-get >/dev/null 2>&1 && sudo -n apt-get update -y && sudo -n apt-get install -y python3 python3-pip python3-venv) || true",
            "python3 -m venv .triage_venv || true",
            ". .triage_venv/bin/activate && pip install --upgrade pip pytest setuptools wheel || true",
        ],
        test_runner_command=". .triage_venv/bin/activate && pytest",
        docker_image="python:3.11-slim"
    ),
    "node-npm": BoilerplateEnvironment(
        id="node-npm",
        name="Node.js NPM Environment",
        description="Modern Node.js runtime with npm, pnpm, and JavaScript/TypeScript test runners",
        languages=["javascript", "typescript", "node", "js", "ts"],
        setup_commands=[
            "which node > /dev/null 2>&1 || (command -v apt-get >/dev/null 2>&1 && curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -n -E bash - && sudo -n apt-get install -y nodejs) || true",
            "npm install --legacy-peer-deps || true",
        ],
        test_runner_command="npm test --if-present",
        docker_image="node:20-slim"
    ),
    "rust-cargo": BoilerplateEnvironment(
        id="rust-cargo",
        name="Rust Cargo Environment",
        description="Rust toolchain environment with cargo and rustc",
        languages=["rust", "rs"],
        setup_commands=[
            "which cargo > /dev/null 2>&1 || (curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y) || true",
        ],
        test_runner_command="cargo test",
        docker_image="rust:latest"
    ),
    "go-test": BoilerplateEnvironment(
        id="go-test",
        name="Go Toolchain Environment",
        description="Go development environment with standard toolchain",
        languages=["go", "golang"],
        setup_commands=[
            "which go > /dev/null 2>&1 || (command -v apt-get >/dev/null 2>&1 && sudo -n apt-get update -y && sudo -n apt-get install -y golang-go) || true",
            "go mod download || true",
        ],
        test_runner_command="go test -v ./...",
        docker_image="golang:latest"
    ),
}


def get_boilerplate(boilerplate_id: str) -> Optional[BoilerplateEnvironment]:
    """Retrieve boilerplate definition by ID."""
    return BOILERPLATE_CATALOG.get(boilerplate_id.lower().strip())


def list_boilerplates() -> List[BoilerplateEnvironment]:
    """List all available boilerplate environments."""
    return list(BOILERPLATE_CATALOG.values())


def register_boilerplate(boilerplate: BoilerplateEnvironment) -> None:
    """Register or overwrite a boilerplate environment."""
    BOILERPLATE_CATALOG[boilerplate.id] = boilerplate


def get_catalog_summary() -> str:
    """Format catalog of boilerplates for LLM prompts."""
    lines = []
    for bp in BOILERPLATE_CATALOG.values():
        langs = ", ".join(bp.languages)
        lines.append(f"- ID: `{bp.id}` | Name: {bp.name} | Languages: [{langs}] | Description: {bp.description}")
    return "\n".join(lines)


def detect_heuristic_boilerplate(repo_url: str, text: str) -> str:
    """Heuristic fallback to pick the most likely boilerplate if LLM is unavailable."""
    lower_repo = repo_url.lower()
    lower_text = text.lower()

    if "boost" in lower_repo or "boost" in lower_text:
        return "cpp-boost"
    if any(k in lower_text or k in lower_repo for k in ["c++", "cpp", "cmake", "make", "gcc", "clang"]):
        return "cpp-cmake"
    if any(k in lower_text or k in lower_repo for k in ["python", "pytest", "pip", "django", "flask", "requests"]):
        return "python-pytest"
    if any(k in lower_text or k in lower_repo for k in ["node", "npm", "javascript", "typescript", "react", "express"]):
        return "node-npm"
    if any(k in lower_text or k in lower_repo for k in ["rust", "cargo", "crates"]):
        return "rust-cargo"
    if any(k in lower_text or k in lower_repo for k in ["golang", "go test"]):
        return "go-test"

    return "custom"
