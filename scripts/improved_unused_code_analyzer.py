#!/usr/bin/env python3
"""
Improved unused code analyzer for the autonomous mower system.

This version is much more conservative and accurate, avoiding false positives
by better understanding the codebase structure and usage patterns.
"""

import ast
import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict


class ImprovedCodeAnalyzer(ast.NodeVisitor):
    """Enhanced AST visitor that better understands code usage patterns."""
    
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
        self.string_literals: Set[str] = set()
        self.decorators: Set[str] = set()
        self.method_calls: Set[str] = set()  # Track method calls like self.method()
        
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
        # Track decorators
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                self.decorators.add(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                self.decorators.add(decorator.attr)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_defs.add(node.name)
        # Track decorators
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                self.decorators.add(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                self.decorators.add(decorator.attr)
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
            # Track method calls like self.method()
            if isinstance(node.func.value, ast.Name) and node.func.value.id == 'self':
                self.method_calls.add(node.func.attr)
        self.generic_visit(node)
    
    def visit_Attribute(self, node: ast.Attribute) -> None:
        self.attribute_accesses.add(node.attr)
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name) -> None:
        self.name_references.add(node.id)
        self.generic_visit(node)
    
    def visit_Str(self, node: ast.Str) -> None:
        # Track string literals that might reference functions/classes
        self.string_literals.add(node.s)
        self.generic_visit(node)
    
    def visit_Constant(self, node: ast.Constant) -> None:
        # Python 3.8+ uses Constant instead of Str
        if isinstance(node.value, str):
            self.string_literals.add(node.value)
        self.generic_visit(node)


class ImprovedUnusedCodeDetector:
    """Enhanced unused code detector with better accuracy."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.src_root = self.project_root / "src"
        self.test_root = self.project_root / "tests"
        self.scripts_root = self.project_root / "scripts"
        
        # Analysis results
        self.file_analysis: Dict[str, ImprovedCodeAnalyzer] = {}
        self.all_python_files: Set[str] = set()
        self.import_graph: Dict[str, Set[str]] = defaultdict(set)
        
        # Results (more conservative)
        self.likely_unused_files: List[str] = []
        self.likely_unused_functions: List[Tuple[str, str]] = []
        self.likely_unused_classes: List[Tuple[str, str]] = []
        self.unused_imports: List[Tuple[str, str]] = []
        self.suspicious_files: List[str] = []  # Files that might be unused but need review
        
        # Special file patterns that should never be considered unused
        self.special_files = {
            'src/mower/robohat_files/code.py',  # RP2040 microcontroller code
            'setup.py',  # Package setup
            'conftest.py',  # Pytest configuration
            '__init__.py',  # Package initialization
        }
        
        # Framework patterns that indicate usage
        self.framework_patterns = {
            'flask': ['@app.route', '@bp.route', 'app.route', 'blueprint'],
            'pytest': ['test_', 'fixture', '@pytest.', 'conftest'],
            'fastapi': ['@app.get', '@app.post', '@router.'],
            'django': ['urlpatterns', 'admin.register'],
        }
        
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
    
    def analyze_file(self, file_path: str) -> Optional[ImprovedCodeAnalyzer]:
        """Analyze a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the AST
            tree = ast.parse(content, filename=file_path)
            analyzer = ImprovedCodeAnalyzer(file_path)
            analyzer.visit(tree)
            
            return analyzer
            
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError) as e:
            print(f"Warning: Could not analyze {file_path}: {e}")
            return None
    
    def is_special_file(self, file_path: str) -> bool:
        """Check if a file has special purposes and should not be considered unused."""
        rel_path = os.path.relpath(file_path, self.project_root)
        
        # Check exact matches
        if rel_path in self.special_files:
            return True
        
        # Check patterns
        filename = os.path.basename(file_path)
        
        # Special filenames
        special_patterns = [
            '__init__.py',
            '__main__.py',
            'setup.py',
            'conftest.py',
            'main.py',
            'app.py',
            'wsgi.py',
            'manage.py',
        ]
        
        if filename in special_patterns:
            return True
        
        # Files in special directories
        if any(part in rel_path for part in ['templates', 'static', 'migrations', 'fixtures']):
            return True
        
        # Configuration files
        if filename.endswith(('_config.py', 'config.py', 'settings.py')):
            return True
        
        return False
    
    def is_entry_point_file(self, file_path: str) -> bool:
        """Enhanced entry point detection."""
        rel_path = os.path.relpath(file_path, self.project_root)
        
        # Special files are always entry points
        if self.is_special_file(file_path):
            return True
        
        # Test files are entry points
        if rel_path.startswith('tests/') and rel_path.endswith('.py'):
            return True
            
        # Script files are entry points
        if rel_path.startswith('scripts/') and rel_path.endswith('.py'):
            return True
        
        # Check file content for entry point indicators
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Has main guard
                if 'if __name__ == "__main__"' in content:
                    return True
                
                # Flask app patterns
                if any(pattern in content for pattern in ['@app.route', 'Flask(__name__)', 'app.run(']):
                    return True
                
                # Test patterns
                if any(pattern in content for pattern in ['def test_', '@pytest.', 'class Test']):
                    return True
                
                # CLI patterns
                if any(pattern in content for pattern in ['argparse', 'click.command', 'sys.argv']):
                    return True
                    
        except:
            pass
            
        return False
    
    def resolve_import_to_file(self, import_name: str, importing_file: str) -> Optional[str]:
        """Improved import resolution."""
        # Handle relative imports
        if import_name.startswith('.'):
            importing_dir = os.path.dirname(importing_file)
            # This is complex - for now, skip relative imports
            return None
        
        # Handle absolute imports within our project
        if import_name.startswith(('mower', 'src.mower')):
            # Convert module path to file path
            module_parts = import_name.replace('src.', '').split('.')
            
            if len(module_parts) >= 1:
                # Try different path combinations
                if module_parts[0] == 'mower':
                    module_parts = module_parts[1:]  # Remove 'mower' prefix
                
                if module_parts:
                    module_path = '/'.join(module_parts)
                    
                    # Try as package (__init__.py)
                    potential_file = self.src_root / 'mower' / module_path / '__init__.py'
                    if potential_file.exists():
                        return os.path.relpath(str(potential_file), self.project_root)
                    
                    # Try as module (.py file)
                    potential_file = self.src_root / 'mower' / (module_path + '.py')
                    if potential_file.exists():
                        return os.path.relpath(str(potential_file), self.project_root)
        
        return None
    
    def build_import_graph(self) -> None:
        """Build a more accurate import graph."""
        for file_path, analyzer in self.file_analysis.items():
            rel_path = os.path.relpath(file_path, self.project_root)
            
            # Process all imports
            all_imports = set(analyzer.imports)
            for module, names in analyzer.from_imports.items():
                all_imports.add(module)
            
            for import_name in all_imports:
                resolved_file = self.resolve_import_to_file(import_name, file_path)
                if resolved_file:
                    self.import_graph[rel_path].add(resolved_file)
    
    def find_likely_unused_files(self) -> None:
        """Find files that are likely unused (conservative approach)."""
        imported_files = set()
        
        # Collect all files that are imported
        for imports in self.import_graph.values():
            imported_files.update(imports)
        
        # Find files that might be unused
        for file_path in self.all_python_files:
            rel_path = os.path.relpath(file_path, self.project_root)
            
            # Skip entry points and special files
            if self.is_entry_point_file(file_path):
                continue
            
            # If not imported, might be unused
            if rel_path not in imported_files:
                # Be more conservative - add to suspicious list first
                self.suspicious_files.append(rel_path)
                
                # Only add to likely unused if we're very confident
                analyzer = self.file_analysis.get(file_path)
                if analyzer:
                    # Very small files with no significant content
                    if (len(analyzer.function_defs) == 0 and 
                        len(analyzer.class_defs) == 0 and 
                        len(analyzer.variable_assignments) <= 2):
                        self.likely_unused_files.append(rel_path)
    
    def find_likely_unused_functions(self) -> None:
        """Find functions that are likely unused (very conservative)."""
        # Build comprehensive usage maps
        all_function_calls = set()
        all_method_calls = set()
        all_name_references = set()
        all_string_references = set()
        all_decorators = set()
        
        for analyzer in self.file_analysis.values():
            all_function_calls.update(analyzer.function_calls)
            all_method_calls.update(analyzer.method_calls)
            all_name_references.update(analyzer.name_references)
            all_string_references.update(analyzer.string_literals)
            all_decorators.update(analyzer.decorators)
        
        # Find potentially unused functions
        for file_path, analyzer in self.file_analysis.items():
            rel_path = os.path.relpath(file_path, self.project_root)
            
            for func_name in analyzer.function_defs:
                # Skip special methods and common patterns
                if self._should_skip_function(func_name, rel_path):
                    continue
                
                # Check if function is referenced anywhere
                is_used = (
                    func_name in all_function_calls or
                    func_name in all_method_calls or
                    func_name in all_name_references or
                    func_name in all_string_references or
                    func_name in all_decorators or
                    self._is_framework_function(func_name, analyzer)
                )
                
                if not is_used:
                    self.likely_unused_functions.append((rel_path, func_name))
    
    def _should_skip_function(self, func_name: str, file_path: str) -> bool:
        """Check if a function should be skipped from unused analysis."""
        # Skip special methods
        if func_name.startswith('__') and func_name.endswith('__'):
            return True
        
        # Skip test methods
        if func_name.startswith('test_'):
            return True
        
        # Skip common patterns
        skip_patterns = [
            'setUp', 'tearDown', 'setUpClass', 'tearDownClass',
            'main', 'run', 'start', 'stop', 'init', 'cleanup',
            'get_', 'set_', 'is_', 'has_', 'can_', 'should_',
        ]
        
        if any(func_name.startswith(pattern) for pattern in skip_patterns):
            return True
        
        # Skip in test files
        if 'test' in file_path:
            return True
        
        # Skip in special files
        if any(special in file_path for special in ['conftest', 'setup', '__init__']):
            return True
        
        return False
    
    def _is_framework_function(self, func_name: str, analyzer: ImprovedCodeAnalyzer) -> bool:
        """Check if function is used by a framework."""
        # Check for Flask route decorators
        if any('@app.route' in s or '@bp.route' in s for s in analyzer.string_literals):
            return True
        
        # Check for pytest fixtures
        if 'fixture' in analyzer.decorators:
            return True
        
        # Check for other framework patterns
        framework_indicators = ['route', 'endpoint', 'handler', 'callback', 'listener']
        if any(indicator in func_name.lower() for indicator in framework_indicators):
            return True
        
        return False
    
    def find_unused_imports(self) -> None:
        """Find imports that are clearly unused."""
        for file_path, analyzer in self.file_analysis.items():
            rel_path = os.path.relpath(file_path, self.project_root)
            
            # Check direct imports
            for import_name in analyzer.imports:
                # Skip common imports that might be used indirectly
                if import_name in ['os', 'sys', 'time', 'json', 'logging']:
                    continue
                
                if import_name not in analyzer.name_references:
                    self.unused_imports.append((rel_path, f"import {import_name}"))
            
            # Check from imports
            for module, names in analyzer.from_imports.items():
                for name in names:
                    # Skip common patterns
                    if name in ['*', 'TYPE_CHECKING']:
                        continue
                    
                    if name not in analyzer.name_references:
                        self.unused_imports.append((rel_path, f"from {module} import {name}"))
    
    def analyze(self) -> Dict[str, Any]:
        """Run the improved analysis."""
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
        
        print("Finding likely unused files...")
        self.find_likely_unused_files()
        
        print("Finding likely unused functions...")
        self.find_likely_unused_functions()
        
        print("Finding unused imports...")
        self.find_unused_imports()
        
        # Compile results (ensure JSON serializable)
        results = {
            'summary': {
                'total_files_analyzed': len(self.file_analysis),
                'likely_unused_files': len(self.likely_unused_files),
                'suspicious_files': len(self.suspicious_files),
                'likely_unused_functions': len(self.likely_unused_functions),
                'unused_imports': len(self.unused_imports),
            },
            'likely_unused_files': self.likely_unused_files,
            'suspicious_files': self.suspicious_files,
            'likely_unused_functions': self.likely_unused_functions,
            'unused_imports': self.unused_imports,
            'import_graph_sample': {k: list(v) for k, v in list(self.import_graph.items())[:5]},  # Convert sets to lists
        }
        
        return results
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a conservative, accurate report."""
        report = []
        report.append("# Improved Unused Code Analysis Report")
        report.append("=" * 50)
        report.append("")
        report.append("This analysis is conservative and focuses on high-confidence findings.")
        report.append("Files marked as 'suspicious' need manual review.")
        report.append("")
        
        # Summary
        summary = results['summary']
        report.append("## Summary")
        report.append(f"- Total files analyzed: {summary['total_files_analyzed']}")
        report.append(f"- Likely unused files: {summary['likely_unused_files']}")
        report.append(f"- Suspicious files (need review): {summary['suspicious_files']}")
        report.append(f"- Likely unused functions: {summary['likely_unused_functions']}")
        report.append(f"- Unused imports: {summary['unused_imports']}")
        report.append("")
        
        # Likely unused files
        if results['likely_unused_files']:
            report.append("## Likely Unused Files (High Confidence)")
            report.append("These files appear to be unused with high confidence:")
            report.append("")
            for file_path in sorted(results['likely_unused_files']):
                report.append(f"- {file_path}")
            report.append("")
        
        # Suspicious files
        if results['suspicious_files']:
            report.append("## Suspicious Files (Need Manual Review)")
            report.append("These files might be unused but require manual verification:")
            report.append("")
            for file_path in sorted(results['suspicious_files']):
                report.append(f"- {file_path}")
            report.append("")
        
        # Likely unused functions (limited to top 20)
        if results['likely_unused_functions']:
            report.append("## Likely Unused Functions (Top 20)")
            report.append("These functions appear to be unused:")
            report.append("")
            by_file = defaultdict(list)
            for file_path, func_name in results['likely_unused_functions'][:20]:
                by_file[file_path].append(func_name)
            
            for file_path in sorted(by_file.keys()):
                report.append(f"### {file_path}")
                for func_name in sorted(by_file[file_path]):
                    report.append(f"- {func_name}()")
                report.append("")
        
        # Unused imports (limited to top 20)
        if results['unused_imports']:
            report.append("## Unused Imports (Top 20)")
            report.append("These imports appear to be unused:")
            report.append("")
            by_file = defaultdict(list)
            for file_path, import_stmt in results['unused_imports'][:20]:
                by_file[file_path].append(import_stmt)
            
            for file_path in sorted(by_file.keys()):
                report.append(f"### {file_path}")
                for import_stmt in sorted(by_file[file_path]):
                    report.append(f"- {import_stmt}")
                report.append("")
        
        report.append("## Notes")
        report.append("- This analysis is conservative to avoid false positives")
        report.append("- 'Suspicious' files need manual review before removal")
        report.append("- Framework-specific usage patterns are considered")
        report.append("- Special files (like code.py for RP2040) are protected")
        report.append("")
        
        return "\n".join(report)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = "."
    
    detector = ImprovedUnusedCodeDetector(project_root)
    results = detector.analyze()
    
    # Save detailed results as JSON
    output_file = "improved_unused_code_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Detailed results saved to {output_file}")
    
    # Generate and save report
    report = detector.generate_report(results)
    report_file = "improved_unused_code_report.md"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"Report saved to {report_file}")
    
    # Print summary
    print("\n" + "=" * 50)
    print("IMPROVED UNUSED CODE ANALYSIS SUMMARY")
    print("=" * 50)
    summary = results['summary']
    print(f"Total files analyzed: {summary['total_files_analyzed']}")
    print(f"Likely unused files: {summary['likely_unused_files']}")
    print(f"Suspicious files (need review): {summary['suspicious_files']}")
    print(f"Likely unused functions: {summary['likely_unused_functions']}")
    print(f"Unused imports: {summary['unused_imports']}")
    
    if summary['likely_unused_files'] > 0:
        print(f"\n✅ Found {summary['likely_unused_files']} files that are likely safe to remove")
    
    if summary['suspicious_files'] > 0:
        print(f"⚠️  Found {summary['suspicious_files']} files that need manual review")
    
    if summary['likely_unused_functions'] > 0:
        print(f"⚠️  Found {summary['likely_unused_functions']} functions that might be unused")


if __name__ == "__main__":
    main()