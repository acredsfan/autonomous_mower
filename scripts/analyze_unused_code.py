#!/usr/bin/env python3
"""
Comprehensive unused code analyzer for the autonomous mower system.

This script identifies:
- Unused files (not imported anywhere)
- Unused functions and classes
- Unused variables and imports
- Potential zombie code
"""

import ast
import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict
import importlib.util


class CodeAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze Python code for usage patterns."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.imports: Set[str] = set()
        self.from_imports: Dict[str, Set[str]] = defaultdict(set)
        self.function_defs: Set[str] = set()
        self.class_defs: Set[str] = set()
        self.variable_assignments: Set[str] = set()
        self.function_calls: Set[str] = set()
        self.attribute_accesses: Set[str] = set()
        self.name_references: Set[str] = set()
        
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            for alias in node.names:
                self.from_imports[node.module].add(alias.name)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_defs.add(node.name)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_defs.add(node.name)
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.class_defs.add(node.name)
        self.generic_visit(node)
    
    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.variable_assignments.add(target.id)
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            self.function_calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.attribute_accesses.add(node.func.attr)
        self.generic_visit(node)
    
    def visit_Attribute(self, node: ast.Attribute) -> None:
        self.attribute_accesses.add(node.attr)
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name) -> None:
        self.name_references.add(node.id)
        self.generic_visit(node)


class UnusedCodeDetector:
    """Main class for detecting unused code across the project."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.src_root = self.project_root / "src"
        self.test_root = self.project_root / "tests"
        self.scripts_root = self.project_root / "scripts"
        
        # Analysis results
        self.file_analysis: Dict[str, CodeAnalyzer] = {}
        self.all_python_files: Set[str] = set()
        self.import_graph: Dict[str, Set[str]] = defaultdict(set)
        self.usage_graph: Dict[str, Set[str]] = defaultdict(set)
        
        # Results
        self.unused_files: List[str] = []
        self.unused_functions: List[Tuple[str, str]] = []  # (file, function)
        self.unused_classes: List[Tuple[str, str]] = []   # (file, class)
        self.unused_imports: List[Tuple[str, str]] = []   # (file, import)
        self.zombie_files: List[str] = []  # Files that seem abandoned
        
    def find_python_files(self) -> List[str]:
        """Find all Python files in the project."""
        python_files = []
        
        # Search in src, tests, and scripts directories
        search_dirs = [self.src_root, self.test_root, self.scripts_root]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                for py_file in search_dir.rglob("*.py"):
                    # Skip __pycache__ directories
                    if "__pycache__" not in str(py_file):
                        python_files.append(str(py_file))
        
        # Also check root level Python files
        for py_file in self.project_root.glob("*.py"):
            python_files.append(str(py_file))
            
        return python_files
    
    def analyze_file(self, file_path: str) -> Optional[CodeAnalyzer]:
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the AST
            tree = ast.parse(content, filename=file_path)
            analyzer = CodeAnalyzer(file_path)
            analyzer.visit(tree)
            
            return analyzer
            
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError) as e:
            print(f"Warning: Could not analyze {file_path}: {e}")
            return None
    
    def build_import_graph(self) -> None:
        """Build a graph of which files import which other files."""
        for file_path, analyzer in self.file_analysis.items():
            rel_path = os.path.relpath(file_path, self.project_root)
            
            # Process direct imports
            for import_name in analyzer.imports:
                # Try to resolve to a file in our project
                resolved_file = self.resolve_import_to_file(import_name, file_path)
                if resolved_file:
                    self.import_graph[rel_path].add(resolved_file)
            
            # Process from imports
            for module, names in analyzer.from_imports.items():
                resolved_file = self.resolve_import_to_file(module, file_path)
                if resolved_file:
                    self.import_graph[rel_path].add(resolved_file)
    
    def resolve_import_to_file(self, import_name: str, importing_file: str) -> Optional[str]:
        """Try to resolve an import to a file path within the project."""
        # Handle relative imports
        if import_name.startswith('.'):
            # Relative import - resolve relative to importing file
            importing_dir = os.path.dirname(importing_file)
            # This is simplified - full relative import resolution is complex
            return None
        
        # Handle absolute imports within our project
        if import_name.startswith('mower') or import_name.startswith('src.mower'):
            # Convert module path to file path
            module_parts = import_name.replace('src.', '').split('.')
            if len(module_parts) > 1:
                module_path = '/'.join(module_parts[1:])
                potential_file = self.src_root / module_path / '__init__.py'
                if potential_file.exists():
                    return os.path.relpath(str(potential_file), self.project_root)
                
                potential_file = self.src_root / (module_path + '.py')
                if potential_file.exists():
                    return os.path.relpath(str(potential_file), self.project_root)
        
        return None
    
    def find_unused_files(self) -> None:
        """Find files that are never imported."""
        imported_files = set()
        
        # Collect all files that are imported
        for imports in self.import_graph.values():
            imported_files.update(imports)
        
        # Find files that are never imported
        for file_path in self.all_python_files:
            rel_path = os.path.relpath(file_path, self.project_root)
            
            # Skip certain files that are entry points
            if self.is_entry_point_file(file_path):
                continue
                
            if rel_path not in imported_files:
                self.unused_files.append(rel_path)
    
    def is_entry_point_file(self, file_path: str) -> bool:
        """Check if a file is an entry point (main, test, script)."""
        rel_path = os.path.relpath(file_path, self.project_root)
        
        # Entry point patterns
        entry_patterns = [
            'main.py',
            'main_controller.py',
            '__main__.py',
            'setup.py',
            'conftest.py',
        ]
        
        # Test files are entry points
        if rel_path.startswith('tests/') and rel_path.endswith('.py'):
            return True
            
        # Script files are entry points
        if rel_path.startswith('scripts/') and rel_path.endswith('.py'):
            return True
        
        # Check specific patterns
        filename = os.path.basename(file_path)
        if filename in entry_patterns:
            return True
            
        # Check if file has if __name__ == "__main__"
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'if __name__ == "__main__"' in content:
                    return True
        except:
            pass
            
        return False
    
    def find_unused_functions_and_classes(self) -> None:
        """Find functions and classes that are never called/referenced."""
        # Build usage maps
        all_function_calls = set()
        all_class_references = set()
        all_name_references = set()
        
        for analyzer in self.file_analysis.values():
            all_function_calls.update(analyzer.function_calls)
            all_name_references.update(analyzer.name_references)
            all_class_references.update(analyzer.name_references)  # Classes referenced as names
        
        # Find unused functions
        for file_path, analyzer in self.file_analysis.items():
            rel_path = os.path.relpath(file_path, self.project_root)
            
            for func_name in analyzer.function_defs:
                # Skip special methods
                if func_name.startswith('__') and func_name.endswith('__'):
                    continue
                    
                # Skip test methods
                if func_name.startswith('test_'):
                    continue
                
                # Check if function is called anywhere
                if func_name not in all_function_calls and func_name not in all_name_references:
                    self.unused_functions.append((rel_path, func_name))
            
            # Find unused classes
            for class_name in analyzer.class_defs:
                if class_name not in all_class_references:
                    self.unused_classes.append((rel_path, class_name))
    
    def find_unused_imports(self) -> None:
        """Find imports that are never used in the file."""
        for file_path, analyzer in self.file_analysis.items():
            rel_path = os.path.relpath(file_path, self.project_root)
            
            # Check direct imports
            for import_name in analyzer.imports:
                if import_name not in analyzer.name_references:
                    self.unused_imports.append((rel_path, f"import {import_name}"))
            
            # Check from imports
            for module, names in analyzer.from_imports.items():
                for name in names:
                    if name not in analyzer.name_references:
                        self.unused_imports.append((rel_path, f"from {module} import {name}"))
    
    def find_zombie_files(self) -> None:
        """Find files that might be zombie code (old, unused, or abandoned)."""
        for file_path in self.all_python_files:
            rel_path = os.path.relpath(file_path, self.project_root)
            
            # Skip if already identified as unused
            if rel_path in self.unused_files:
                continue
            
            analyzer = self.file_analysis.get(file_path)
            if not analyzer:
                continue
            
            # Heuristics for zombie files
            zombie_indicators = 0
            
            # Very few or no function/class definitions
            if len(analyzer.function_defs) + len(analyzer.class_defs) == 0:
                zombie_indicators += 1
            
            # Only has imports and simple assignments
            if (len(analyzer.function_defs) == 0 and 
                len(analyzer.class_defs) == 0 and 
                len(analyzer.variable_assignments) > 0):
                zombie_indicators += 1
            
            # Check file size and complexity
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    non_empty_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
                    
                    # Very small files with little content
                    if len(non_empty_lines) < 5:
                        zombie_indicators += 1
            except:
                pass
            
            # Files with suspicious names
            suspicious_names = ['temp', 'old', 'backup', 'test_temp', 'debug', 'tmp']
            filename = os.path.basename(file_path).lower()
            if any(name in filename for name in suspicious_names):
                zombie_indicators += 1
            
            if zombie_indicators >= 2:
                self.zombie_files.append(rel_path)
    
    def analyze(self) -> Dict[str, Any]:
        """Run the complete analysis."""
        print("Finding Python files...")
        python_files = self.find_python_files()
        self.all_python_files = set(python_files)
        print(f"Found {len(python_files)} Python files")
        
        print("Analyzing files...")
        for file_path in python_files:
            analyzer = self.analyze_file(file_path)
            if analyzer:
                self.file_analysis[file_path] = analyzer
        
        print("Building import graph...")
        self.build_import_graph()
        
        print("Finding unused files...")
        self.find_unused_files()
        
        print("Finding unused functions and classes...")
        self.find_unused_functions_and_classes()
        
        print("Finding unused imports...")
        self.find_unused_imports()
        
        print("Finding zombie files...")
        self.find_zombie_files()
        
        # Compile results
        results = {
            'summary': {
                'total_files_analyzed': len(self.file_analysis),
                'unused_files': len(self.unused_files),
                'unused_functions': len(self.unused_functions),
                'unused_classes': len(self.unused_classes),
                'unused_imports': len(self.unused_imports),
                'zombie_files': len(self.zombie_files)
            },
            'unused_files': self.unused_files,
            'unused_functions': self.unused_functions,
            'unused_classes': self.unused_classes,
            'unused_imports': self.unused_imports,
            'zombie_files': self.zombie_files,
            'import_graph': {k: list(v) for k, v in self.import_graph.items()}
        }
        
        return results
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a human-readable report."""
        report = []
        report.append("# Unused Code Analysis Report")
        report.append("=" * 50)
        report.append("")
        
        # Summary
        summary = results['summary']
        report.append("## Summary")
        report.append(f"- Total files analyzed: {summary['total_files_analyzed']}")
        report.append(f"- Unused files: {summary['unused_files']}")
        report.append(f"- Unused functions: {summary['unused_functions']}")
        report.append(f"- Unused classes: {summary['unused_classes']}")
        report.append(f"- Unused imports: {summary['unused_imports']}")
        report.append(f"- Potential zombie files: {summary['zombie_files']}")
        report.append("")
        
        # Unused files
        if results['unused_files']:
            report.append("## Unused Files")
            report.append("These files are never imported and may be safe to remove:")
            report.append("")
            for file_path in sorted(results['unused_files']):
                report.append(f"- {file_path}")
            report.append("")
        
        # Zombie files
        if results['zombie_files']:
            report.append("## Potential Zombie Files")
            report.append("These files show signs of being abandoned or temporary:")
            report.append("")
            for file_path in sorted(results['zombie_files']):
                report.append(f"- {file_path}")
            report.append("")
        
        # Unused functions
        if results['unused_functions']:
            report.append("## Unused Functions")
            report.append("These functions are defined but never called:")
            report.append("")
            by_file = defaultdict(list)
            for file_path, func_name in results['unused_functions']:
                by_file[file_path].append(func_name)
            
            for file_path in sorted(by_file.keys()):
                report.append(f"### {file_path}")
                for func_name in sorted(by_file[file_path]):
                    report.append(f"- {func_name}()")
                report.append("")
        
        # Unused classes
        if results['unused_classes']:
            report.append("## Unused Classes")
            report.append("These classes are defined but never referenced:")
            report.append("")
            by_file = defaultdict(list)
            for file_path, class_name in results['unused_classes']:
                by_file[file_path].append(class_name)
            
            for file_path in sorted(by_file.keys()):
                report.append(f"### {file_path}")
                for class_name in sorted(by_file[file_path]):
                    report.append(f"- {class_name}")
                report.append("")
        
        # Unused imports (top 20 to avoid overwhelming)
        if results['unused_imports']:
            report.append("## Unused Imports (Top 20)")
            report.append("These imports are never used in their respective files:")
            report.append("")
            by_file = defaultdict(list)
            for file_path, import_stmt in results['unused_imports'][:20]:
                by_file[file_path].append(import_stmt)
            
            for file_path in sorted(by_file.keys()):
                report.append(f"### {file_path}")
                for import_stmt in sorted(by_file[file_path]):
                    report.append(f"- {import_stmt}")
                report.append("")
        
        return "\n".join(report)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = "."
    
    detector = UnusedCodeDetector(project_root)
    results = detector.analyze()
    
    # Save detailed results as JSON
    output_file = "unused_code_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Detailed results saved to {output_file}")
    
    # Generate and save report
    report = detector.generate_report(results)
    report_file = "unused_code_report.md"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"Report saved to {report_file}")
    
    # Print summary
    print("\n" + "=" * 50)
    print("UNUSED CODE ANALYSIS SUMMARY")
    print("=" * 50)
    summary = results['summary']
    print(f"Total files analyzed: {summary['total_files_analyzed']}")
    print(f"Unused files: {summary['unused_files']}")
    print(f"Unused functions: {summary['unused_functions']}")
    print(f"Unused classes: {summary['unused_classes']}")
    print(f"Unused imports: {summary['unused_imports']}")
    print(f"Potential zombie files: {summary['zombie_files']}")
    
    if summary['unused_files'] > 0 or summary['zombie_files'] > 0:
        print(f"\n⚠️  Found {summary['unused_files'] + summary['zombie_files']} files that may be safe to remove")
    
    if summary['unused_functions'] > 0 or summary['unused_classes'] > 0:
        print(f"⚠️  Found {summary['unused_functions'] + summary['unused_classes']} unused functions/classes")
    
    if summary['unused_imports'] > 0:
        print(f"⚠️  Found {summary['unused_imports']} unused imports")


if __name__ == "__main__":
    main()