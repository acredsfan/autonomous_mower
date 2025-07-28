#!/usr/bin/env python3
"""
Type hint coverage checker for the autonomous mower project.

This script analyzes Python files to check for type hint coverage
and provides a report on which functions/methods need type hints.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class TypeHintChecker(ast.NodeVisitor):
    """AST visitor to check for type hints in Python code."""
    
    def __init__(self) -> None:
        self.functions: List[Dict[str, any]] = []
        self.classes: List[Dict[str, any]] = []
        self.current_class: str = ""
        
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions."""
        self.current_class = node.name
        self.classes.append({
            'name': node.name,
            'line': node.lineno,
            'has_docstring': ast.get_docstring(node) is not None
        })
        self.generic_visit(node)
        self.current_class = ""
        
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        # Check for type hints
        has_return_annotation = node.returns is not None
        has_arg_annotations = any(arg.annotation is not None for arg in node.args.args)
        
        # Skip special methods like __init__, __str__, etc. for some checks
        is_special_method = node.name.startswith('__') and node.name.endswith('__')
        
        self.functions.append({
            'name': node.name,
            'class': self.current_class,
            'line': node.lineno,
            'has_return_annotation': has_return_annotation,
            'has_arg_annotations': has_arg_annotations,
            'is_special_method': is_special_method,
            'has_docstring': ast.get_docstring(node) is not None,
            'arg_count': len(node.args.args)
        })
        
        self.generic_visit(node)
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        # Same logic as regular functions
        has_return_annotation = node.returns is not None
        has_arg_annotations = any(arg.annotation is not None for arg in node.args.args)
        is_special_method = node.name.startswith('__') and node.name.endswith('__')
        
        self.functions.append({
            'name': node.name,
            'class': self.current_class,
            'line': node.lineno,
            'has_return_annotation': has_return_annotation,
            'has_arg_annotations': has_arg_annotations,
            'is_special_method': is_special_method,
            'has_docstring': ast.get_docstring(node) is not None,
            'arg_count': len(node.args.args),
            'is_async': True
        })
        
        self.generic_visit(node)


def analyze_file(file_path: Path) -> Tuple[TypeHintChecker, bool]:
    """Analyze a Python file for type hints."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        checker = TypeHintChecker()
        checker.visit(tree)
        return checker, True
        
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return TypeHintChecker(), False


def get_python_files(directory: Path) -> List[Path]:
    """Get all Python files in a directory recursively."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.pytest_cache', '.mypy_cache', 'node_modules'}]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    return python_files


def generate_report(files_analysis: Dict[Path, TypeHintChecker]) -> None:
    """Generate a comprehensive type hint coverage report."""
    total_functions = 0
    functions_with_return_hints = 0
    functions_with_arg_hints = 0
    functions_with_docstrings = 0
    
    print("=" * 80)
    print("TYPE HINT COVERAGE REPORT")
    print("=" * 80)
    
    # Summary statistics
    for file_path, checker in files_analysis.items():
        for func in checker.functions:
            total_functions += 1
            if func['has_return_annotation']:
                functions_with_return_hints += 1
            if func['has_arg_annotations']:
                functions_with_arg_hints += 1
            if func['has_docstring']:
                functions_with_docstrings += 1
    
    if total_functions > 0:
        return_coverage = (functions_with_return_hints / total_functions) * 100
        arg_coverage = (functions_with_arg_hints / total_functions) * 100
        docstring_coverage = (functions_with_docstrings / total_functions) * 100
        
        print(f"Total functions analyzed: {total_functions}")
        print(f"Return type hint coverage: {return_coverage:.1f}%")
        print(f"Argument type hint coverage: {arg_coverage:.1f}%")
        print(f"Docstring coverage: {docstring_coverage:.1f}%")
        print()
    
    # Files needing attention
    print("FILES NEEDING TYPE HINTS:")
    print("-" * 40)
    
    for file_path, checker in files_analysis.items():
        functions_needing_hints = []
        
        for func in checker.functions:
            needs_attention = False
            issues = []
            
            if not func['has_return_annotation'] and not func['is_special_method']:
                needs_attention = True
                issues.append("missing return type")
            
            if not func['has_arg_annotations'] and func['arg_count'] > 1:  # Skip self parameter
                needs_attention = True
                issues.append("missing argument types")
                
            if not func['has_docstring']:
                needs_attention = True
                issues.append("missing docstring")
            
            if needs_attention:
                class_prefix = f"{func['class']}." if func['class'] else ""
                functions_needing_hints.append(
                    f"  Line {func['line']}: {class_prefix}{func['name']}() - {', '.join(issues)}"
                )
        
        if functions_needing_hints:
            print(f"\n{file_path}:")
            for issue in functions_needing_hints[:10]:  # Limit to first 10 issues per file
                print(issue)
            if len(functions_needing_hints) > 10:
                print(f"  ... and {len(functions_needing_hints) - 10} more issues")


def main() -> None:
    """Main function to run type hint analysis."""
    if len(sys.argv) > 1:
        target_dir = Path(sys.argv[1])
    else:
        target_dir = Path("src/mower")
    
    if not target_dir.exists():
        print(f"Directory {target_dir} does not exist")
        sys.exit(1)
    
    print(f"Analyzing Python files in {target_dir}...")
    
    python_files = get_python_files(target_dir)
    files_analysis = {}
    
    for file_path in python_files:
        checker, success = analyze_file(file_path)
        if success:
            files_analysis[file_path] = checker
    
    generate_report(files_analysis)


if __name__ == "__main__":
    main()