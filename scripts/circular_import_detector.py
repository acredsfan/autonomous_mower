#!/usr/bin/env python3
"""
Circular Import Detection Script

This script analyzes Python files in the src directory to detect circular import dependencies.
It builds a dependency graph and identifies cycles that could cause import errors.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque
import json


class ImportAnalyzer(ast.NodeVisitor):
    """AST visitor to extract import statements from Python files."""
    
    def __init__(self, module_path: str):
        self.module_path = module_path
        self.imports: List[str] = []
        self.from_imports: List[Tuple[str, List[str]]] = []
    
    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statements like 'import module'."""
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from-import statements like 'from module import item'."""
        if node.module:
            imported_items = [alias.name for alias in node.names]
            self.from_imports.append((node.module, imported_items))
        self.generic_visit(node)


class CircularImportDetector:
    """Main class for detecting circular imports in Python codebase."""
    
    def __init__(self, src_path: str = "src"):
        self.src_path = Path(src_path)
        self.module_graph: Dict[str, Set[str]] = defaultdict(set)
        self.file_to_module: Dict[str, str] = {}
        self.module_to_file: Dict[str, str] = {}
        self.analysis_results = {
            "circular_dependencies": [],
            "import_graph": {},
            "problematic_modules": [],
            "statistics": {},
            "recommendations": []
        }
    
    def get_module_name(self, file_path: Path) -> str:
        """Convert file path to Python module name."""
        relative_path = file_path.relative_to(self.src_path)
        
        # Remove .py extension
        if relative_path.suffix == '.py':
            relative_path = relative_path.with_suffix('')
        
        # Convert path separators to dots
        module_parts = list(relative_path.parts)
        
        # Remove __init__ from module name
        if module_parts and module_parts[-1] == '__init__':
            module_parts = module_parts[:-1]
        
        return '.'.join(module_parts) if module_parts else ''
    
    def resolve_import_to_module(self, import_name: str, current_module: str) -> Optional[str]:
        """Resolve an import statement to a module name within our codebase."""
        # Handle relative imports
        if import_name.startswith('.'):
            current_parts = current_module.split('.')
            
            # Count leading dots for relative level
            level = 0
            for char in import_name:
                if char == '.':
                    level += 1
                else:
                    break
            
            # Remove leading dots from import name
            import_name = import_name[level:]
            
            # Calculate parent module
            if level > len(current_parts):
                return None
            
            parent_parts = current_parts[:-level] if level > 0 else current_parts
            
            if import_name:
                resolved = '.'.join(parent_parts + [import_name])
            else:
                resolved = '.'.join(parent_parts)
        else:
            # Absolute import
            resolved = import_name
        
        # Check if this module exists in our codebase
        if resolved in self.module_to_file:
            return resolved
        
        # Check if it's a submodule of an existing module
        for module in self.module_to_file:
            if resolved.startswith(module + '.'):
                return module
        
        return None
    
    def analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file for imports."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            analyzer = ImportAnalyzer(str(file_path))
            analyzer.visit(tree)
            
            current_module = self.get_module_name(file_path)
            if not current_module:
                return
            
            self.file_to_module[str(file_path)] = current_module
            self.module_to_file[current_module] = str(file_path)
            
            # Process direct imports
            for import_name in analyzer.imports:
                resolved = self.resolve_import_to_module(import_name, current_module)
                if resolved and resolved != current_module:
                    self.module_graph[current_module].add(resolved)
            
            # Process from imports
            for module_name, items in analyzer.from_imports:
                resolved = self.resolve_import_to_module(module_name, current_module)
                if resolved and resolved != current_module:
                    self.module_graph[current_module].add(resolved)
        
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    def find_python_files(self) -> List[Path]:
        """Find all Python files in the source directory."""
        python_files = []
        
        for root, dirs, files in os.walk(self.src_path):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return python_files
    
    def detect_cycles_dfs(self) -> List[List[str]]:
        """Detect cycles using depth-first search."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> bool:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return True
            
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.module_graph.get(node, []):
                if dfs(neighbor):
                    # Continue to find all cycles, don't return immediately
                    pass
            
            rec_stack.remove(node)
            path.pop()
            return False
        
        for node in self.module_graph:
            if node not in visited:
                dfs(node)
        
        return cycles
    
    def detect_cycles_tarjan(self) -> List[List[str]]:
        """Detect strongly connected components using Tarjan's algorithm."""
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        on_stack = {}
        sccs = []
        
        def strongconnect(node: str) -> None:
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack[node] = True
            
            for neighbor in self.module_graph.get(node, []):
                if neighbor not in index:
                    strongconnect(neighbor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
                elif on_stack.get(neighbor, False):
                    lowlinks[node] = min(lowlinks[node], index[neighbor])
            
            if lowlinks[node] == index[node]:
                component = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    component.append(w)
                    if w == node:
                        break
                if len(component) > 1:  # Only cycles with more than one node
                    sccs.append(component)
        
        for node in self.module_graph:
            if node not in index:
                strongconnect(node)
        
        return sccs
    
    def analyze_import_patterns(self) -> Dict[str, any]:
        """Analyze import patterns and generate statistics."""
        stats = {
            "total_modules": len(self.module_to_file),
            "total_dependencies": sum(len(deps) for deps in self.module_graph.values()),
            "modules_with_dependencies": len([m for m in self.module_graph if self.module_graph[m]]),
            "average_dependencies": 0,
            "max_dependencies": 0,
            "most_dependent_module": "",
            "dependency_distribution": defaultdict(int)
        }
        
        if stats["modules_with_dependencies"] > 0:
            stats["average_dependencies"] = stats["total_dependencies"] / stats["modules_with_dependencies"]
        
        for module, deps in self.module_graph.items():
            dep_count = len(deps)
            stats["dependency_distribution"][dep_count] += 1
            
            if dep_count > stats["max_dependencies"]:
                stats["max_dependencies"] = dep_count
                stats["most_dependent_module"] = module
        
        return stats
    
    def generate_recommendations(self, cycles: List[List[str]]) -> List[str]:
        """Generate recommendations for fixing circular imports."""
        recommendations = []
        
        if not cycles:
            recommendations.append("✅ No circular imports detected! Your codebase has a clean import structure.")
            return recommendations
        
        recommendations.append(f"🔍 Found {len(cycles)} circular import cycle(s) that need attention:")
        
        for i, cycle in enumerate(cycles, 1):
            recommendations.append(f"\n📋 Cycle {i}: {' → '.join(cycle)}")
            
            # Analyze the cycle for recommendations
            if len(cycle) == 2:
                recommendations.append("   💡 This is a simple two-module cycle. Consider:")
                recommendations.append("      • Moving shared code to a separate module")
                recommendations.append("      • Using dependency injection instead of direct imports")
                recommendations.append("      • Restructuring one module to not depend on the other")
            else:
                recommendations.append("   💡 This is a complex multi-module cycle. Consider:")
                recommendations.append("      • Breaking the cycle by extracting shared interfaces")
                recommendations.append("      • Using the dependency inversion principle")
                recommendations.append("      • Restructuring the module hierarchy")
        
        recommendations.extend([
            "\n🛠️  General strategies to fix circular imports:",
            "   • Extract shared code into a separate module",
            "   • Use dependency injection patterns",
            "   • Move imports inside functions (lazy loading)",
            "   • Restructure code to follow a layered architecture",
            "   • Use abstract base classes in a separate interfaces module"
        ])
        
        return recommendations
    
    def run_analysis(self) -> Dict[str, any]:
        """Run the complete circular import analysis."""
        print("🔍 Starting circular import analysis...")
        
        # Find and analyze all Python files
        python_files = self.find_python_files()
        print(f"📁 Found {len(python_files)} Python files to analyze")
        
        for file_path in python_files:
            self.analyze_file(file_path)
        
        print(f"📊 Analyzed {len(self.module_to_file)} modules")
        
        # Detect circular imports
        print("🔄 Detecting circular dependencies...")
        cycles = self.detect_cycles_dfs()
        
        # Also try Tarjan's algorithm for comparison
        tarjan_cycles = self.detect_cycles_tarjan()
        
        # Generate statistics
        stats = self.analyze_import_patterns()
        
        # Generate recommendations
        recommendations = self.generate_recommendations(cycles)
        
        # Compile results
        self.analysis_results = {
            "circular_dependencies": cycles,
            "tarjan_cycles": tarjan_cycles,
            "import_graph": {k: list(v) for k, v in self.module_graph.items()},
            "module_to_file": self.module_to_file,
            "file_to_module": self.file_to_module,
            "statistics": stats,
            "recommendations": recommendations
        }
        
        return self.analysis_results
    
    def print_results(self) -> None:
        """Print analysis results to console."""
        results = self.analysis_results
        
        print("\n" + "="*80)
        print("🔍 CIRCULAR IMPORT ANALYSIS RESULTS")
        print("="*80)
        
        # Print statistics
        stats = results["statistics"]
        print(f"\n📊 STATISTICS:")
        print(f"   Total modules analyzed: {stats['total_modules']}")
        print(f"   Total dependencies: {stats['total_dependencies']}")
        print(f"   Modules with dependencies: {stats['modules_with_dependencies']}")
        print(f"   Average dependencies per module: {stats['average_dependencies']:.2f}")
        print(f"   Module with most dependencies: {stats['most_dependent_module']} ({stats['max_dependencies']} deps)")
        
        # Print circular dependencies
        cycles = results["circular_dependencies"]
        if cycles:
            print(f"\n🚨 CIRCULAR DEPENDENCIES FOUND: {len(cycles)}")
            for i, cycle in enumerate(cycles, 1):
                print(f"\n   Cycle {i}:")
                for j, module in enumerate(cycle):
                    if j < len(cycle) - 1:
                        print(f"      {module} →")
                    else:
                        print(f"      {module}")
                        if cycle[0] != cycle[-1]:
                            print(f"      ↑_______________|")
        else:
            print(f"\n✅ NO CIRCULAR DEPENDENCIES FOUND!")
        
        # Print recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in results["recommendations"]:
            print(f"   {rec}")
        
        print("\n" + "="*80)
    
    def save_results(self, output_file: str = "circular_import_analysis.json") -> None:
        """Save analysis results to a JSON file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, indent=2, ensure_ascii=False)
        print(f"💾 Results saved to {output_file}")


def main():
    """Main function to run the circular import analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Detect circular imports in Python codebase")
    parser.add_argument("--src", default="src", help="Source directory to analyze (default: src)")
    parser.add_argument("--output", default="circular_import_analysis.json", 
                       help="Output file for results (default: circular_import_analysis.json)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress console output")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.src):
        print(f"❌ Error: Source directory '{args.src}' does not exist")
        sys.exit(1)
    
    detector = CircularImportDetector(args.src)
    results = detector.run_analysis()
    
    if not args.quiet:
        detector.print_results()
    
    detector.save_results(args.output)
    
    # Exit with error code if circular imports found
    if results["circular_dependencies"]:
        print(f"\n❌ Analysis complete: {len(results['circular_dependencies'])} circular import(s) found")
        sys.exit(1)
    else:
        print(f"\n✅ Analysis complete: No circular imports found")
        sys.exit(0)


if __name__ == "__main__":
    main()