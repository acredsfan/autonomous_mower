#!/usr/bin/env python3
"""
Analyze import dependencies and detect circular imports in the autonomous mower codebase.

This script scans Python files for imports and builds a dependency graph to identify
circular dependencies and other import issues.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import networkx as nx


class ImportAnalyzer:
    """Analyzes Python imports and detects circular dependencies."""
    
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.src_path = root_path / "src"
        self.dependency_graph = nx.DiGraph()
        self.module_files = {}  # module_name -> file_path
        self.file_imports = {}  # file_path -> list of imported modules
        
    def scan_python_files(self) -> List[Path]:
        """Find all Python files in the src directory."""
        python_files = []
        for root, dirs, files in os.walk(self.src_path):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return python_files
    
    def parse_imports(self, file_path: Path) -> List[str]:
        """Parse imports from a Python file."""
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
                        # Also track specific imports from the module
                        for alias in node.names:
                            if alias.name != '*':
                                full_import = f"{node.module}.{alias.name}"
                                imports.append(full_import)
            
            return imports
            
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError) as e:
            print(f"Error parsing {file_path}: {e}")
            return []
    
    def get_module_name(self, file_path: Path) -> str:
        """Convert file path to module name."""
        # Get relative path from src directory
        try:
            rel_path = file_path.relative_to(self.src_path)
        except ValueError:
            # File is not in src directory
            return str(file_path)
        
        # Convert path to module name
        parts = list(rel_path.parts)
        if parts[-1] == '__init__.py':
            parts = parts[:-1]
        elif parts[-1].endswith('.py'):
            parts[-1] = parts[-1][:-3]
        
        return '.'.join(parts)
    
    def build_dependency_graph(self):
        """Build a dependency graph of all modules."""
        python_files = self.scan_python_files()
        
        # First pass: map modules to files
        for file_path in python_files:
            module_name = self.get_module_name(file_path)
            self.module_files[module_name] = file_path
            self.dependency_graph.add_node(module_name)
        
        # Second pass: analyze imports and build edges
        for file_path in python_files:
            module_name = self.get_module_name(file_path)
            imports = self.parse_imports(file_path)
            self.file_imports[file_path] = imports
            
            for imported_module in imports:
                # Normalize imported module name
                imported_module = self.normalize_import(imported_module)
                
                # Only track internal module dependencies
                if self.is_internal_module(imported_module):
                    self.dependency_graph.add_edge(module_name, imported_module)
    
    def normalize_import(self, import_name: str) -> str:
        """Normalize import names to module names."""
        # Remove leading dots for relative imports
        if import_name.startswith('.'):
            import_name = import_name.lstrip('.')
        
        # For mower.* imports, normalize to internal module names
        if import_name.startswith('mower.'):
            return import_name[6:]  # Remove 'mower.' prefix
        
        return import_name
    
    def is_internal_module(self, module_name: str) -> bool:
        """Check if a module is internal to the project."""
        # Check if it's one of our known modules
        if module_name in self.module_files:
            return True
        
        # Check if it's a submodule of one of our modules
        for known_module in self.module_files:
            if module_name.startswith(known_module + '.'):
                return True
            if known_module.startswith(module_name + '.'):
                return True
        
        return False
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """Find all circular dependencies in the module graph."""
        try:
            cycles = list(nx.simple_cycles(self.dependency_graph))
            return cycles
        except nx.NetworkXError:
            return []
    
    def find_missing_modules(self) -> List[Tuple[str, str]]:
        """Find imported modules that don't exist."""
        missing = []
        
        for file_path, imports in self.file_imports.items():
            module_name = self.get_module_name(file_path)
            
            for imported_module in imports:
                normalized = self.normalize_import(imported_module)
                
                # Skip external libraries
                if not (normalized.startswith('mower') or 
                        '.' in normalized or
                        normalized in self.module_files):
                    continue
                
                # Check if this internal module exists
                if self.is_internal_module(normalized) and normalized not in self.module_files:
                    missing.append((str(file_path), imported_module))
        
        return missing
    
    def generate_report(self) -> str:
        """Generate a comprehensive import analysis report."""
        self.build_dependency_graph()
        
        report = []
        report.append("=== Autonomous Mower Import Analysis Report ===\n")
        
        # Basic statistics
        report.append(f"Total Python files analyzed: {len(self.scan_python_files())}")
        report.append(f"Total modules found: {len(self.module_files)}")
        report.append(f"Total dependency edges: {self.dependency_graph.number_of_edges()}\n")
        
        # Circular dependencies
        cycles = self.find_circular_dependencies()
        report.append(f"=== Circular Dependencies ({len(cycles)} found) ===")
        if cycles:
            for i, cycle in enumerate(cycles, 1):
                cycle_str = ' -> '.join(cycle + [cycle[0]])
                report.append(f"{i}. {cycle_str}")
        else:
            report.append("No circular dependencies found!")
        report.append("")
        
        # Missing modules
        missing = self.find_missing_modules()
        report.append(f"=== Missing Modules ({len(missing)} found) ===")
        if missing:
            for file_path, missing_module in missing:
                rel_path = Path(file_path).relative_to(self.root_path)
                report.append(f"  {rel_path} imports missing: {missing_module}")
        else:
            report.append("No missing modules found!")
        report.append("")
        
        # Module with most dependencies
        if self.dependency_graph.nodes():
            out_degrees = dict(self.dependency_graph.out_degree())
            max_deps_module = max(out_degrees, key=out_degrees.get)
            max_deps_count = out_degrees[max_deps_module]
            report.append(f"=== Module with Most Dependencies ===")
            report.append(f"{max_deps_module}: {max_deps_count} dependencies")
            
            # List the dependencies
            dependencies = list(self.dependency_graph.successors(max_deps_module))
            if dependencies:
                report.append("Dependencies:")
                for dep in sorted(dependencies):
                    report.append(f"  - {dep}")
            report.append("")
        
        # Modules with no dependencies (potential unused)
        no_deps = [module for module in self.dependency_graph.nodes() 
                   if self.dependency_graph.out_degree(module) == 0]
        report.append(f"=== Modules with No Dependencies ({len(no_deps)} found) ===")
        if no_deps:
            for module in sorted(no_deps):
                report.append(f"  - {module}")
        report.append("")
        
        # Modules not imported by anyone (potential unused)
        no_incoming = [module for module in self.dependency_graph.nodes() 
                       if self.dependency_graph.in_degree(module) == 0]
        report.append(f"=== Modules Not Imported ({len(no_incoming)} found) ===")
        if no_incoming:
            for module in sorted(no_incoming):
                report.append(f"  - {module}")
        
        return '\n'.join(report)


def main():
    """Main function to run import analysis."""
    root_path = Path(__file__).parent.parent
    analyzer = ImportAnalyzer(root_path)
    
    print("Analyzing imports in autonomous mower codebase...")
    report = analyzer.generate_report()
    
    # Write report to file
    report_file = root_path / "import_analysis_report.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"Analysis complete! Report saved to: {report_file}")
    print("\n" + "="*60)
    print(report)


if __name__ == "__main__":
    main()
