"""Multi-language AST and Symbol Scanner.

Indexes symbols (functions, classes, methods, variables, exports) across
Python, JavaScript/TypeScript, and configuration files to catch AI hallucinations
and fabricated security CVE claims.
"""

import ast
import re
import os
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
import difflib


class SymbolLocation:
    def __init__(self, name: str, kind: str, file_path: str, line_number: int, signature: str = ""):
        self.name = name
        self.kind = kind  # function, async_function, class, method, variable, export
        self.file_path = file_path
        self.line_number = line_number
        self.signature = signature

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "signature": self.signature
        }


class CodebaseSymbolIndex:
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir).resolve()
        self.symbols: Dict[str, List[SymbolLocation]] = {}
        self.scanned_files: List[str] = []
        self._index_codebase()

    def _index_codebase(self):
        """Walks the codebase and indexes symbols."""
        ignored_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build", ".pytest_cache"}

        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]

            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), self.root_dir)
                full_path = Path(root) / file

                if file.endswith(".py"):
                    self._index_python_file(full_path, rel_path)
                    self.scanned_files.append(rel_path)
                elif file.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
                    self._index_js_ts_file(full_path, rel_path)
                    self.scanned_files.append(rel_path)
                elif file.endswith(".go"):
                    self._index_go_file(full_path, rel_path)
                    self.scanned_files.append(rel_path)
                elif file.endswith(".rs"):
                    self._index_rust_file(full_path, rel_path)
                    self.scanned_files.append(rel_path)
                elif file.endswith(".swift"):
                    self._index_swift_file(full_path, rel_path)
                    self.scanned_files.append(rel_path)
                elif file.endswith((".java", ".kt")):
                    self._index_jvm_file(full_path, rel_path)
                    self.scanned_files.append(rel_path)
                elif file.endswith((".c", ".cpp", ".cc", ".cxx", ".h", ".hpp")):
                    self._index_c_cpp_file(full_path, rel_path)
                    self.scanned_files.append(rel_path)

    def _index_python_file(self, full_path: Path, rel_path: str):
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(full_path))
        except Exception:
            return

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                kind = "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
                args = [a.arg for a in node.args.args]
                sig = f"{node.name}({', '.join(args)})"
                self._add_symbol(node.name, kind, rel_path, node.lineno, sig)

            elif isinstance(node, ast.ClassDef):
                sig = f"class {node.name}"
                self._add_symbol(node.name, "class", rel_path, node.lineno, sig)
                # Also index methods inside this class
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_kind = "method"
                        method_args = [a.arg for a in item.args.args]
                        method_sig = f"{node.name}.{item.name}({', '.join(method_args)})"
                        self._add_symbol(item.name, method_kind, rel_path, item.lineno, method_sig)
                        self._add_symbol(f"{node.name}.{item.name}", method_kind, rel_path, item.lineno, method_sig)

    def _index_js_ts_file(self, full_path: Path, rel_path: str):
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        # 1. Matches function foo(...) or async function foo(...)
        func_matches = re.finditer(r"(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\((.*?)\)", content)
        for m in func_matches:
            name = m.group(1)
            line = content[:m.start()].count("\n") + 1
            sig = f"{name}({m.group(2).strip()})"
            self._add_symbol(name, "function", rel_path, line, sig)

        # 2. Matches React components, arrow functions, forwardRef, memo:
        # const Foo = (...) => or const Foo = forwardRef(...) or export const Foo = ...
        var_matches = re.finditer(
            r"(?:export\s+)?(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:forwardRef|memo|styled|React\.forwardRef|React\.memo)?(?:\s*<[^>]+>)?\s*(?:\((.*?)\)|[A-Za-z0-9_$]+)?",
            content
        )
        for m in var_matches:
            name = m.group(1)
            line = content[:m.start()].count("\n") + 1
            kind = "component" if name[0].isupper() else "function"
            self._add_symbol(name, kind, rel_path, line, f"{name}(...)")

        # 3. Matches class Foo
        class_matches = re.finditer(r"(?:export\s+)?class\s+([A-Za-z0-9_$]+)", content)
        for m in class_matches:
            name = m.group(1)
            line = content[:m.start()].count("\n") + 1
            self._add_symbol(name, "class", rel_path, line, f"class {name}")

        # 4. Matches interfaces and types (e.g. interface ComboboxProps, type ModalVariant)
        type_matches = re.finditer(r"(?:export\s+)?(?:interface|type)\s+([A-Za-z0-9_$]+)", content)
        for m in type_matches:
            name = m.group(1)
            line = content[:m.start()].count("\n") + 1
            self._add_symbol(name, "type", rel_path, line, f"type {name}")

        # 5. File basename component indexing (e.g. Accordion.tsx -> Accordion)
        file_stem = full_path.stem.split(".")[0]
        if file_stem and file_stem[0].isupper() and file_stem != "Index":
            self._add_symbol(file_stem, "component_file", rel_path, 1, f"component {file_stem}")

    def _index_go_file(self, full_path: Path, rel_path: str):
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        # Matches func FuncName(...) or func (r *Receiver) MethodName(...)
        for m in re.finditer(r"func\s+(?:\([^\)]+\)\s+)?([A-Za-z0-9_]+)\s*\(", content):
            name = m.group(1)
            line = content[:m.start()].count("\n") + 1
            self._add_symbol(name, "function", rel_path, line, f"func {name}(...)")

        # Matches type StructName struct / interface
        for m in re.finditer(r"type\s+([A-Za-z0-9_]+)\s+(?:struct|interface)", content):
            name = m.group(1)
            line = content[:m.start()].count("\n") + 1
            self._add_symbol(name, "type", rel_path, line, f"type {name}")

    def _index_rust_file(self, full_path: Path, rel_path: str):
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        # Matches fn func_name(...) or pub fn func_name(...)
        for m in re.finditer(r"(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z0-9_]+)\s*(?:<[^>]+>)?\s*\(", content):
            name = m.group(1)
            line = content[:m.start()].count("\n") + 1
            self._add_symbol(name, "function", rel_path, line, f"fn {name}(...)")

        # Matches struct/enum/trait Name
        for m in re.finditer(r"(?:pub\s+)?(?:struct|enum|trait)\s+([A-Za-z0-9_]+)", content):
            name = m.group(1)
            line = content[:m.start()].count("\n") + 1
            self._add_symbol(name, "type", rel_path, line, f"type {name}")

    def _index_swift_file(self, full_path: Path, rel_path: str):
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        # Matches class/struct/enum/protocol/extension Name
        for m in re.finditer(r"(?:public\s+|private\s+|fileprivate\s+|internal\s+|open\s+)?(?:class|struct|enum|protocol|extension)\s+([A-Za-z0-9_]+)", content):
            name = m.group(1)
            line = content[:m.start()].count("\n") + 1
            self._add_symbol(name, "type", rel_path, line, f"type {name}")

        # Matches func func_name(...)
        for m in re.finditer(r"(?:public\s+|private\s+|fileprivate\s+|internal\s+|open\s+|override\s+|mutating\s+)?func\s+([A-Za-z0-9_]+)\s*(?:<[^>]+>)?\s*\((.*?)\)", content):
            name = m.group(1)
            line = content[:m.start()].count("\n") + 1
            sig = f"func {name}({m.group(2).strip()})"
            self._add_symbol(name, "function", rel_path, line, sig)

    def _index_jvm_file(self, full_path: Path, rel_path: str):
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        # Matches class/interface Name
        for m in re.finditer(r"(?:class|interface|object|record)\s+([A-Za-z0-9_]+)", content):
            name = m.group(1)
            line = content[:m.start()].count("\n") + 1
            self._add_symbol(name, "class", rel_path, line, f"class {name}")

        # Matches Kotlin fun name(...)
        for m in re.finditer(r"fun\s+([A-Za-z0-9_]+)\s*\(", content):
            name = m.group(1)
            line = content[:m.start()].count("\n") + 1
            self._add_symbol(name, "function", rel_path, line, f"fun {name}(...)")

    def _index_c_cpp_file(self, full_path: Path, rel_path: str):
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        # Matches class/struct Name
        for m in re.finditer(r"(?:class|struct)\s+([A-Za-z0-9_]+)\s*[{:]", content):
            name = m.group(1)
            line = content[:m.start()].count("\n") + 1
            self._add_symbol(name, "class", rel_path, line, f"class {name}")

        # Matches function signatures: ReturnType FuncName(...) {
        for m in re.finditer(r"\b([A-Za-z0-9_]+)\s*\([^)]*\)\s*\{", content):
            name = m.group(1)
            if name not in {"if", "for", "while", "switch", "catch"}:
                line = content[:m.start()].count("\n") + 1
                self._add_symbol(name, "function", rel_path, line, f"{name}(...)")

    def _add_symbol(self, name: str, kind: str, rel_path: str, line: int, signature: str):
        if name not in self.symbols:
            self.symbols[name] = []
        self.symbols[name].append(SymbolLocation(name, kind, rel_path, line, signature))

    def lookup(self, symbol_name: str) -> Dict[str, Any]:
        """Checks if a symbol exists. Returns locations, similar candidates, and scan statistics."""
        # Clean symbol name (remove trailing parens like foo() -> foo)
        clean_name = re.sub(r"\(.*\)$", "", symbol_name.strip())

        exists = clean_name in self.symbols
        locations = [loc.to_dict() for loc in self.symbols.get(clean_name, [])]

        # Find closest matches if missing or for fuzzy audit
        all_symbol_names = list(self.symbols.keys())
        similar = difflib.get_close_matches(clean_name, all_symbol_names, n=3, cutoff=0.55)

        return {
            "query_symbol": symbol_name,
            "clean_symbol": clean_name,
            "exists": exists,
            "locations": locations,
            "similar_candidates": similar,
            "total_files_scanned": len(self.scanned_files),
            "total_symbols_indexed": len(self.symbols),
            "scanned_files": self.scanned_files[:10]  # first 10 for display
        }
