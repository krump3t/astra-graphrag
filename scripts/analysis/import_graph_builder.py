"""Import Graph Builder for Dead Code Analysis.

Builds a graph of imports starting from entry points to identify
code that is actually reachable vs dead code.

Task 015: Authenticity Validation Framework - Phase 1
"""

import ast
import json
from pathlib import Path
from typing import Dict, List, Set
import sys


class ImportGraphBuilder:
    """Build import graph from entry points."""

    def __init__(self, root_dir: Path):
        """Initialize builder.

        Args:
            root_dir: Root directory of codebase
        """
        self.root_dir = root_dir
        self.import_graph: Dict[str, Set[str]] = {}
        self.visited: Set[str] = set()
        self.entry_points: List[str] = []

    def analyze_imports(self, file_path: Path) -> Set[str]:
        """Extract imports from a Python file.

        Args:
            file_path: Path to Python file

        Returns:
            Set of imported module names
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(file_path))
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")
            return set()

        imports: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
                    # Also add specific imports
                    for alias in node.names:
                        full_name = f"{node.module}.{alias.name}"
                        imports.add(full_name)

        return imports

    def resolve_module_path(self, module_name: str) -> Path | None:
        """Resolve module name to file path.

        Args:
            module_name: Python module name (e.g., 'services.langgraph.workflow')

        Returns:
            Path to module file, or None if not found
        """
        # Convert module name to path
        parts = module_name.split(".")

        # Try as __init__.py in directory
        dir_path = self.root_dir / Path(*parts)
        init_path = dir_path / "__init__.py"
        if init_path.exists():
            return init_path

        # Try as .py file
        file_path = self.root_dir / Path(*parts[:-1]) / f"{parts[-1]}.py"
        if file_path.exists():
            return file_path

        # Try relative to root
        file_path = self.root_dir / f"{module_name.replace('.', '/')}.py"
        if file_path.exists():
            return file_path

        return None

    def build_graph(self, entry_points: List[Path]) -> Dict[str, Set[str]]:
        """Build import graph starting from entry points.

        Args:
            entry_points: List of entry point files

        Returns:
            Import graph as dict mapping file -> set of imported files
        """
        self.entry_points = [str(ep.relative_to(self.root_dir)) for ep in entry_points]
        queue = list(entry_points)

        while queue:
            file_path = queue.pop(0)
            file_key = str(file_path.relative_to(self.root_dir))

            if file_key in self.visited:
                continue

            self.visited.add(file_key)

            # Analyze imports
            imports = self.analyze_imports(file_path)
            self.import_graph[file_key] = set()

            # Resolve and queue imported modules
            for import_name in imports:
                # Skip standard library and external packages
                if not import_name.startswith(("services", "schemas", "scripts", "tests")):
                    continue

                # Resolve to file path
                resolved = self.resolve_module_path(import_name)
                if resolved and resolved.exists():
                    resolved_key = str(resolved.relative_to(self.root_dir))
                    self.import_graph[file_key].add(resolved_key)

                    if resolved_key not in self.visited:
                        queue.append(resolved)

        return self.import_graph

    def get_reachable_files(self) -> Set[str]:
        """Get all files reachable from entry points.

        Returns:
            Set of reachable file paths (relative to root)
        """
        return set(self.import_graph.keys())

    def get_unreachable_files(self, all_python_files: List[Path]) -> Set[str]:
        """Get files not reachable from entry points.

        Args:
            all_python_files: All Python files in codebase

        Returns:
            Set of unreachable file paths (relative to root)
        """
        all_files = {
            str(f.relative_to(self.root_dir))
            for f in all_python_files
            if not str(f).startswith(("tests", "venv", ".venv"))
        }
        reachable = self.get_reachable_files()
        return all_files - reachable

    def export_json(self, output_path: Path) -> None:
        """Export import graph to JSON.

        Args:
            output_path: Output JSON file path
        """
        # Convert sets to lists for JSON serialization
        graph_json = {
            "entry_points": self.entry_points,
            "reachable_count": len(self.get_reachable_files()),
            "import_graph": {
                k: list(v) for k, v in self.import_graph.items()
            },
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(graph_json, f, indent=2)

        print(f"Import graph exported to: {output_path}")
        print(f"Reachable files: {len(self.get_reachable_files())}")


def main():
    """Main entry point."""
    # Determine root directory
    script_path = Path(__file__).resolve()
    root_dir = script_path.parent.parent.parent  # Go up from scripts/analysis/

    # Define entry points
    entry_points = [
        root_dir / "mcp_server.py",
        root_dir / "mcp_http_server.py",
        root_dir / "services" / "langgraph" / "workflow.py",
    ]

    # Verify entry points exist
    missing = [ep for ep in entry_points if not ep.exists()]
    if missing:
        print(f"Error: Entry points not found: {missing}")
        sys.exit(1)

    # Build import graph
    builder = ImportGraphBuilder(root_dir)
    builder.build_graph(entry_points)

    # Export to JSON
    output_path = root_dir / "tasks" / "015-authenticity-validation-framework" / "qa" / "import_graph.json"
    builder.export_json(output_path)

    # Find unreachable files
    all_py_files = list(root_dir.glob("services/**/*.py")) + \
                   list(root_dir.glob("schemas/**/*.py")) + \
                   list(root_dir.glob("scripts/**/*.py"))

    unreachable = builder.get_unreachable_files(all_py_files)
    if unreachable:
        print(f"\nUnreachable files ({len(unreachable)}):")
        for f in sorted(unreachable)[:20]:  # Show first 20
            print(f"  - {f}")
        if len(unreachable) > 20:
            print(f"  ... and {len(unreachable) - 20} more")


if __name__ == "__main__":
    main()
