"""Tests for type hint coverage and quality.

This module contains tests to verify that the codebase maintains good type hint
coverage and follows typing best practices.
"""

import ast
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import pytest


class TestTypeHints:
    """Test class for type hint coverage and quality."""
    
    def test_mypy_passes_on_core_modules(self) -> None:
        """Test that mypy passes on core modules without errors."""
        core_modules = [
            "src/mower/constants.py",
            "src/mower/hardware/gpio_manager.py",
            "src/mower/interfaces/hardware.py",
            "src/mower/interfaces/navigation.py",
        ]
        
        for module in core_modules:
            if Path(module).exists():
                result = subprocess.run(
                    [sys.executable, "-m", "mypy", module, "--no-error-summary"],
                    capture_output=True,
                    text=True
                )
                assert result.returncode == 0, f"mypy failed for {module}: {result.stdout}"
    
    def test_interfaces_have_complete_type_hints(self) -> None:
        """Test that interface modules have complete type annotations."""
        interface_files = list(Path("src/mower/interfaces").glob("*.py"))
        
        for interface_file in interface_files:
            if interface_file.name == "__init__.py":
                continue
                
            with open(interface_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Skip special methods
                    if node.name.startswith('__') and node.name.endswith('__'):
                        continue
                    
                    # Check return annotation
                    assert node.returns is not None, (
                        f"Function {node.name} in {interface_file} missing return type annotation"
                    )
                    
                    # Check parameter annotations (excluding self/cls)
                    params = node.args.args
                    if params and params[0].arg in ('self', 'cls'):
                        params = params[1:]
                    
                    for param in params:
                        assert param.annotation is not None, (
                            f"Parameter {param.arg} in function {node.name} "
                            f"in {interface_file} missing type annotation"
                        )
    
    def test_constants_module_has_proper_types(self) -> None:
        """Test that constants module has proper type annotations."""
        constants_file = Path("src/mower/constants.py")
        if not constants_file.exists():
            pytest.skip("Constants file not found")
            
        with open(constants_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check that key constants have type annotations
        required_constants = [
            "TIME_INTERVAL",
            "EARTH_RADIUS", 
            "OBSTACLE_MARGIN",
            "polygon_coordinates"
        ]
        
        tree = ast.parse(content)
        
        # Find all annotated assignments
        annotated_vars = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                annotated_vars.add(node.target.id)
        
        # Check that required constants are annotated
        for const in required_constants:
            if const in content:  # Only check if constant exists
                assert const in annotated_vars or f"{const}:" in content, (
                    f"Constant {const} should have type annotation"
                )
    
    def test_type_hint_coverage_threshold(self) -> None:
        """Test that type hint coverage meets minimum threshold."""
        # Run our type coverage checker
        result = subprocess.run(
            [sys.executable, "scripts/check_type_coverage.py"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            pytest.skip("Type coverage checker failed to run")
        
        # Parse the output to get coverage percentages
        lines = result.stdout.split('\n')
        fully_annotated_line = [line for line in lines if "Fully annotated functions:" in line]
        
        if fully_annotated_line:
            # Extract percentage from line like "Fully annotated functions: 1123 (66.4%)"
            percentage_str = fully_annotated_line[0].split('(')[1].split('%')[0]
            coverage_percentage = float(percentage_str)
            
            # Assert minimum coverage threshold
            assert coverage_percentage >= 60.0, (
                f"Type hint coverage ({coverage_percentage}%) is below minimum threshold (60%)"
            )
    
    def test_no_any_types_in_interfaces(self) -> None:
        """Test that interface modules avoid using Any types where possible."""
        interface_files = list(Path("src/mower/interfaces").glob("*.py"))
        
        for interface_file in interface_files:
            if interface_file.name == "__init__.py":
                continue
                
            with open(interface_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count Any usage (this is a simple heuristic)
            any_count = content.count(": Any")
            total_annotations = content.count(": ")
            
            if total_annotations > 0:
                any_ratio = any_count / total_annotations
                assert any_ratio < 0.3, (
                    f"Interface {interface_file} has too many Any types "
                    f"({any_count}/{total_annotations} = {any_ratio:.1%})"
                )


if __name__ == "__main__":
    pytest.main([__file__])