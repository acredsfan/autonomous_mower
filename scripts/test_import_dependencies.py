#!/usr/bin/env python3
"""
Import dependency testing script for the autonomous mower project.

This script tests all imports in the codebase to ensure they work correctly
and identifies any circular dependencies or missing imports.
"""

import ast
import importlib
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


class ImportTester:
    """Tests imports and dependency relationships."""
    
    def __init__(self, source_dir: str = "src"):
        """Initialize the import tester.
        
        Args:
            source_dir: Source directory to test imports from.
        """
        self.source_dir = Path(source_dir)
        self.import_graph: Dict[str, Set[str]] = {}
        self.failed_imports: List[Tuple[str, str, str]] = []
        self.circular_deps: List[List[str]] = []
        
    def extract_imports_from_file(self, file_path: Path) -> List[str]:
        """Extract all imports from a Python file.
        
        Args:
            file_path: Path to the Python file.
            
        Returns:
            List of import statements found in the file.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                        for alias in node.names:
                            if alias.name != '*':
                                imports.append(f"{node.module}.{alias.name}")
            
            return imports
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return []
    
    def test_import(self, module_name: str, file_path: str) -> bool:
        """Test if a module can be imported successfully.
        
        Args:
            module_name: Name of the module to import.
            file_path: File path where the import is from (for error reporting).
            
        Returns:
            True if import succeeds, False otherwise.
        """
        try:
            # Add source directory to Python path temporarily
            if str(self.source_dir) not in sys.path:
                sys.path.insert(0, str(self.source_dir))
            
            importlib.import_module(module_name)
            return True
            
        except ImportError as e:
            self.failed_imports.append((file_path, module_name, str(e)))
            return False
        except Exception as e:
            self.failed_imports.append((file_path, module_name, f"Unexpected error: {e}"))
            return False
    
    def build_import_graph(self) -> None:
        """Build a graph of import dependencies."""
        print("Building import dependency graph...")
        
        for py_file in self.source_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
                
            module_path = str(py_file.relative_to(self.source_dir))
            module_name = module_path.replace('/', '.').replace('\\', '.').replace('.py', '')
            
            imports = self.extract_imports_from_file(py_file)
            
            # Filter for internal imports (within our project)
            internal_imports = set()
            for imp in imports:
                if imp.startswith('mower.') or imp == 'mower':
                    internal_imports.add(imp)
            
            self.import_graph[module_name] = internal_imports
    
    def find_circular_dependencies(self) -> None:
        """Find circular dependencies in the import graph."""
        print("Checking for circular dependencies...")
        
        def dfs(node: str, path: List[str], visited: Set[str]) -> None:
            if node in path:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                if cycle not in self.circular_deps:
                    self.circular_deps.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            for dependency in self.import_graph.get(node, set()):
                dfs(dependency, path.copy(), visited)
        
        visited = set()
        for module in self.import_graph:
            if module not in visited:
                dfs(module, [], visited)
    
    def test_all_imports(self) -> None:
        """Test all imports in the codebase."""
        print("Testing all imports...")
        
        total_imports = 0
        successful_imports = 0
        
        for py_file in self.source_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            
            imports = self.extract_imports_from_file(py_file)
            
            for import_name in imports:
                total_imports += 1
                if self.test_import(import_name, str(py_file)):
                    successful_imports += 1
        
        print(f"Import test results: {successful_imports}/{total_imports} successful")
    
    def run_comprehensive_test(self) -> None:
        """Run comprehensive import and dependency testing."""
        print("=" * 80)
        print("IMPORT DEPENDENCY TESTING")
        print("=" * 80)
        print(f"Testing imports in: {self.source_dir}")
        print()
        
        # Build import graph
        self.build_import_graph()
        
        # Find circular dependencies
        self.find_circular_dependencies()
        
        # Test all imports
        self.test_all_imports()
        
        # Print results
        self.print_results()
    
    def print_results(self) -> None:
        """Print comprehensive test results."""
        print("\n" + "=" * 80)
        print("IMPORT TESTING RESULTS")
        print("=" * 80)
        
        # Circular dependencies
        if self.circular_deps:
            print("❌ CIRCULAR DEPENDENCIES FOUND:")
            print("-" * 40)
            for i, cycle in enumerate(self.circular_deps, 1):
                print(f"{i}. {' -> '.join(cycle)}")
        else:
            print("✅ No circular dependencies found")
        
        print()
        
        # Failed imports
        if self.failed_imports:
            print("❌ FAILED IMPORTS:")
            print("-" * 40)
            for file_path, module, error in self.failed_imports:
                print(f"File: {file_path}")
                print(f"  Import: {module}")
                print(f"  Error: {error}")
                print()
        else:
            print("✅ All imports successful")
        
        # Summary
        print("-" * 80)
        total_modules = len(self.import_graph)
        total_failed = len(self.failed_imports)
        total_circular = len(self.circular_deps)
        
        print(f"Modules analyzed: {total_modules}")
        print(f"Failed imports: {total_failed}")
        print(f"Circular dependencies: {total_circular}")
        
        if total_failed > 0 or total_circular > 0:
            print("\n❌ Import testing failed. Please fix the issues above.")
            sys.exit(1)
        else:
            print("\n✅ All import tests passed!")


def main() -> None:
    """Main function to run import dependency testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test import dependencies")
    parser.add_argument(
        "--source-dir",
        default="src",
        help="Source directory to test (default: src)"
    )
    
    args = parser.parse_args()
    
    if not Path(args.source_dir).exists():
        print(f"Error: Source directory '{args.source_dir}' does not exist.")
        sys.exit(1)
    
    tester = ImportTester(args.source_dir)
    tester.run_comprehensive_test()


if __name__ == "__main__":
    main()