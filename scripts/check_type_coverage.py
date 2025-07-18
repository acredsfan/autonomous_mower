#!/usr/bin/env python3
"""Script to check type hint coverage in the codebase.

This script analyzes Python files to identify functions and methods that are
missing type hints and provides a coverage report.
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, NamedTuple, Set


class FunctionInfo(NamedTuple):
    """Information about a function or method."""
    name: str
    file_path: str
    line_number: int
    has_return_annotation: bool
    has_param_annotations: bool
    param_count: int
    annotated_param_count: int


class TypeHintChecker:
    """Analyzes Python files for type hint coverage."""
    
    def __init__(self, source_dir: str = "src/mower"):
        """Initialize the type hint checker.
        
        Args:
            source_dir: Directory to analyze for type hints.
        """
        self.source_dir = Path(source_dir)
        self.functions: List[FunctionInfo] = []
        
    def analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file for type hints.
        
        Args:
            file_path: Path to the Python file to analyze.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self._analyze_function(node, file_path)
                    
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    def _analyze_function(self, node: ast.FunctionDef, file_path: Path) -> None:
        """Analyze a function node for type annotations.
        
        Args:
            node: AST function definition node.
            file_path: Path to the file containing the function.
        """
        # Skip special methods and private methods for now
        if node.name.startswith('__') and node.name.endswith('__'):
            return
            
        has_return_annotation = node.returns is not None
        
        # Count parameters (excluding self/cls)
        params = node.args.args
        if params and params[0].arg in ('self', 'cls'):
            params = params[1:]
            
        param_count = len(params)
        annotated_param_count = sum(1 for arg in params if arg.annotation is not None)
        has_param_annotations = param_count == 0 or annotated_param_count == param_count
        
        function_info = FunctionInfo(
            name=node.name,
            file_path=str(file_path),
            line_number=node.lineno,
            has_return_annotation=has_return_annotation,
            has_param_annotations=has_param_annotations,
            param_count=param_count,
            annotated_param_count=annotated_param_count
        )
        
        self.functions.append(function_info)
    
    def analyze_directory(self) -> None:
        """Analyze all Python files in the source directory."""
        for py_file in self.source_dir.rglob("*.py"):
            if "__pycache__" not in str(py_file):
                self.analyze_file(py_file)
    
    def generate_report(self) -> None:
        """Generate and print a type hint coverage report."""
        if not self.functions:
            print("No functions found to analyze.")
            return
            
        total_functions = len(self.functions)
        fully_annotated = sum(1 for f in self.functions 
                             if f.has_return_annotation and f.has_param_annotations)
        
        return_annotated = sum(1 for f in self.functions if f.has_return_annotation)
        param_annotated = sum(1 for f in self.functions if f.has_param_annotations)
        
        print("=" * 60)
        print("TYPE HINT COVERAGE REPORT")
        print("=" * 60)
        print(f"Total functions analyzed: {total_functions}")
        print(f"Fully annotated functions: {fully_annotated} ({fully_annotated/total_functions*100:.1f}%)")
        print(f"Return type annotated: {return_annotated} ({return_annotated/total_functions*100:.1f}%)")
        print(f"Parameter annotated: {param_annotated} ({param_annotated/total_functions*100:.1f}%)")
        print()
        
        # Show functions missing annotations
        missing_annotations = [f for f in self.functions 
                             if not f.has_return_annotation or not f.has_param_annotations]
        
        if missing_annotations:
            print("FUNCTIONS MISSING TYPE HINTS:")
            print("-" * 40)
            for func in missing_annotations:
                issues = []
                if not func.has_return_annotation:
                    issues.append("return type")
                if not func.has_param_annotations:
                    issues.append(f"parameters ({func.annotated_param_count}/{func.param_count})")
                
                print(f"{func.file_path}:{func.line_number} - {func.name}() - Missing: {', '.join(issues)}")
        
        print("\n" + "=" * 60)


def main() -> None:
    """Main function to run type hint coverage analysis."""
    if len(sys.argv) > 1:
        source_dir = sys.argv[1]
    else:
        source_dir = "src/mower"
    
    if not Path(source_dir).exists():
        print(f"Error: Directory '{source_dir}' does not exist.")
        sys.exit(1)
    
    checker = TypeHintChecker(source_dir)
    checker.analyze_directory()
    checker.generate_report()


if __name__ == "__main__":
    main()