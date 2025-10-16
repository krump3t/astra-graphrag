"""Dead Code Analyzer with Tri-Factor Classification.

Combines Vulture, coverage.py, and import graph analysis to classify
dead code into tiers for safe removal.

Task 015: Authenticity Validation Framework - Phase 1
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set
from dataclasses import dataclass, asdict


@dataclass
class DeadCodeCandidate:
    """Dead code candidate with classification."""

    file: str
    line: int
    name: str
    type: str  # function, class, variable, import
    confidence: int
    tier: int  # 1=safe, 2=review, 3=risky
    reasons: List[str]
    import_reachable: bool
    coverage: float | None = None


class DeadCodeAnalyzer:
    """Analyze dead code using multiple signals."""

    def __init__(self, root_dir: Path):
        """Initialize analyzer.

        Args:
            root_dir: Root directory of codebase
        """
        self.root_dir = root_dir
        self.vulture_candidates: List[Dict[str, Any]] = []
        self.import_graph: Dict[str, Any] = {}
        self.reachable_files: Set[str] = set()
        self.coverage_data: Dict[str, Any] = {}

    def load_vulture_output(self, vulture_file: Path) -> None:
        """Parse Vulture output file.

        Args:
            vulture_file: Path to Vulture output text file
        """
        # Regex pattern for Vulture output:
        # services\graph_index\astra_api.py:75: unused variable 'upper_bound' (100% confidence, 1 line)
        pattern = r"^(.+?):(\d+): unused (variable|function|class|import|attribute|property|method) '([^']+)' \((\d+)% confidence"

        with open(vulture_file, "r", encoding="utf-8") as f:
            for line in f:
                match = re.match(pattern, line.strip())
                if match:
                    file_path, line_num, item_type, name, confidence = match.groups()
                    self.vulture_candidates.append({
                        "file": file_path.replace("\\", "/"),
                        "line": int(line_num),
                        "name": name,
                        "type": item_type,
                        "confidence": int(confidence),
                    })

        print(f"Loaded {len(self.vulture_candidates)} Vulture candidates")

    def load_import_graph(self, import_graph_file: Path) -> None:
        """Load import graph JSON.

        Args:
            import_graph_file: Path to import graph JSON
        """
        with open(import_graph_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.import_graph = data.get("import_graph", {})
            self.reachable_files = set(self.import_graph.keys())

        print(f"Loaded import graph: {len(self.reachable_files)} reachable files")

    def load_coverage_data(self, coverage_file: Path) -> None:
        """Load coverage data (optional).

        Args:
            coverage_file: Path to coverage.xml (optional)
        """
        if not coverage_file.exists():
            print("Warning: Coverage file not found, skipping coverage data")
            return

        # Parse coverage.xml - simplified for now
        # In production, use xml.etree.ElementTree to parse properly
        print("Coverage data loading not yet implemented (optional)")

    def is_file_reachable(self, file_path: str) -> bool:
        """Check if file is reachable from entry points.

        Args:
            file_path: File path (relative to root)

        Returns:
            True if reachable
        """
        # Normalize path
        normalized = file_path.replace("\\", "/")
        return any(normalized in reachable for reachable in self.reachable_files)

    def classify_candidate(self, candidate: Dict[str, Any]) -> DeadCodeCandidate:
        """Classify a dead code candidate into tiers.

        Tier 1 (Safe to remove):
        - Confidence ≥90%
        - File NOT reachable from entry points
        - Type: unused variable, unused import

        Tier 2 (Review recommended):
        - Confidence ≥80%
        - File reachable but item unused
        - Type: unused function, unused class

        Tier 3 (Risky, defer):
        - Confidence <80%
        - Critical path files
        - Type: unused method, unused property

        Args:
            candidate: Vulture candidate dict

        Returns:
            Classified dead code candidate
        """
        file_path = candidate["file"]
        confidence = candidate["confidence"]
        item_type = candidate["type"]
        reachable = self.is_file_reachable(file_path)

        reasons = []
        tier = 3  # Default to risky

        # Tier 1: Safe to remove
        if confidence >= 90 and not reachable and item_type in ("variable", "import"):
            tier = 1
            reasons.append("High confidence (≥90%)")
            reasons.append("File unreachable from entry points")
            reasons.append(f"Safe type ({item_type})")

        # Tier 2: Review recommended
        elif confidence >= 80 and item_type in ("function", "class", "variable", "import"):
            tier = 2
            reasons.append("Medium-high confidence (≥80%)")
            if reachable:
                reasons.append("File reachable but item unused")
            else:
                reasons.append("File unreachable from entry points")

        # Tier 3: Risky (default)
        else:
            tier = 3
            reasons.append(f"Lower confidence ({confidence}%)")
            if item_type in ("method", "property", "attribute"):
                reasons.append(f"Complex type ({item_type})")
            if reachable:
                reasons.append("File reachable from entry points")

        return DeadCodeCandidate(
            file=file_path,
            line=candidate["line"],
            name=candidate["name"],
            type=item_type,
            confidence=confidence,
            tier=tier,
            reasons=reasons,
            import_reachable=reachable,
            coverage=None,  # Not yet implemented
        )

    def analyze(self) -> List[DeadCodeCandidate]:
        """Analyze all candidates and classify into tiers.

        Returns:
            List of classified dead code candidates
        """
        return [self.classify_candidate(c) for c in self.vulture_candidates]

    def export_registry(self, output_path: Path, candidates: List[DeadCodeCandidate]) -> None:
        """Export dead code registry to JSON.

        Args:
            output_path: Output JSON file path
            candidates: List of classified candidates
        """
        # Group by tier
        by_tier: Dict[int, List[Dict[str, Any]]] = {1: [], 2: [], 3: []}
        for c in candidates:
            by_tier[c.tier].append(asdict(c))

        registry = {
            "summary": {
                "total_candidates": len(candidates),
                "tier_1_safe": len(by_tier[1]),
                "tier_2_review": len(by_tier[2]),
                "tier_3_risky": len(by_tier[3]),
            },
            "classification_criteria": {
                "tier_1": "Safe to remove (confidence ≥90%, unreachable, safe type)",
                "tier_2": "Review recommended (confidence ≥80%, unused)",
                "tier_3": "Risky/deferred (lower confidence, complex type, or critical path)",
            },
            "candidates_by_tier": by_tier,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)

        print(f"\nDead Code Registry exported to: {output_path}")
        print(f"  Tier 1 (Safe):   {len(by_tier[1])} candidates")
        print(f"  Tier 2 (Review): {len(by_tier[2])} candidates")
        print(f"  Tier 3 (Risky):  {len(by_tier[3])} candidates")

        # Show top Tier 1 candidates
        if by_tier[1]:
            print("\nTop Tier 1 (Safe to remove) candidates:")
            candidate_dict: Dict[str, Any]
            for candidate_dict in by_tier[1][:10]:
                print(f"  - {candidate_dict['file']}:{candidate_dict['line']} {candidate_dict['type']} '{candidate_dict['name']}'")
            if len(by_tier[1]) > 10:
                print(f"  ... and {len(by_tier[1]) - 10} more")


def main() -> None:
    """Main entry point."""
    # Determine root directory
    script_path = Path(__file__).resolve()
    root_dir = script_path.parent.parent.parent  # Go up from scripts/analysis/

    # Define input paths
    task_dir = root_dir / "tasks" / "015-authenticity-validation-framework"
    vulture_file = task_dir / "qa" / "vulture_dead_code.txt"
    import_graph_file = task_dir / "qa" / "import_graph.json"
    coverage_file = task_dir / "qa" / "coverage_baseline.xml"
    output_file = task_dir / "qa" / "dead_code_registry.json"

    # Verify inputs
    if not vulture_file.exists():
        print(f"Error: Vulture output not found: {vulture_file}")
        return

    if not import_graph_file.exists():
        print(f"Error: Import graph not found: {import_graph_file}")
        return

    # Initialize analyzer
    analyzer = DeadCodeAnalyzer(root_dir)
    analyzer.load_vulture_output(vulture_file)
    analyzer.load_import_graph(import_graph_file)
    analyzer.load_coverage_data(coverage_file)  # Optional

    # Classify candidates
    candidates = analyzer.analyze()

    # Export registry
    analyzer.export_registry(output_file, candidates)


if __name__ == "__main__":
    main()
