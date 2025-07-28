#!/usr/bin/env python3
"""
Enhanced Import Analysis Script

This script provides comprehensive analysis of import patterns including:
- Circular import detection
- Unused import detection
- Complex dependency chain analysis
- Import pattern recommendations
- Dependency graph visualization
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict, deque
import json
import re


class EnhancedImportAnalyzer(ast.NodeVisitor):
    """Enhanced AST visitor to extract detailed import information."""
    
    def __init__(self, module_path: str):
        self.module_path = module_path
        self.imports: List[Dict[str, Any]] = []
        self.from_imports: List[Dict[str, Any]] = []
        self.used_names: Set[str] = set()
        self.defined_names: Set[str] = set()
        
    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statements like 'import module'."""
        for alias in node.names:
            import_info = {
                'module': alias.name,
                'alias': alias.asname,
                'line': node.lineno,
                'type': 'import'
            }
            self.imports.append(import_info)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from-import statements like 'from module import item'."""
        if node.module:
            imported_items = []
            for alias in node.names:
                imported_items.append({
                    'name': alias.name,
                    'alias': alias.asname,
                })
            
            import_info = {
                'module': node.module,
                'items': imported_items,
                'line': node.lineno,
                'level': node.level,
                'type': 'from_import'
            }
            self.from_imports.append(import_info)
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name) -> None:
        """Track name usage in the module."""
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        elif isinstance(node.ctx, ast.Store):
            self.defined_names.add(node.id)
        self.generic_visit(node)
    
    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Track attribute access."""
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track function definitions."""
        self.defined_names.add(node.name)
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class definitions."""
        self.defined_names.add(node.name)
        self.generic_visit(node)


class EnhancedCircularImportDetector:
    """Enhanced circular import detector with additional analysis capabilities."""
    
    def __init__(self, src_path: str = "src"):
        self.src_path = Path(src_path)
        self.module_graph: Dict[str, Set[str]] = defaultdict(set)
        self.detailed_imports: Dict[str, List[Dict[str, Any]]] = {}
        self.file_to_module: Dict[str, str] = {}
        self.module_to_file: Dict[str, str] = {}
        self.unused_imports: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.complex_chains: List[List[str]] = []
        self.analysis_results = {}
    
    def get_module_name(self, file_path: Path) -> str:
        """Convert file path to Python module name."""
        relative_path = file_path.relative_to(self.src_path)
        
        if relative_path.suffix == '.py':
            relative_path = relative_path.with_suffix('')
        
        module_parts = list(relative_path.parts)
        
        if module_parts and module_parts[-1] == '__init__':
            module_parts = module_parts[:-1]
        
        return '.'.join(module_parts) if module_parts else ''
    
    def resolve_import_to_module(self, import_name: str, current_module: str) -> Optional[str]:
        """Resolve an import statement to a module name within our codebase."""
        if import_name.startswith('.'):
            current_parts = current_module.split('.')
            level = 0
            for char in import_name:
                if char == '.':
                    level += 1
                else:
                    break
            
            import_name = import_name[level:]
            
            if level > len(current_parts):
                return None
            
            parent_parts = current_parts[:-level] if level > 0 else current_parts
            
            if import_name:
                resolved = '.'.join(parent_parts + [import_name])
            else:
                resolved = '.'.join(parent_parts)
        else:
            resolved = import_name
        
        if resolved in self.module_to_file:
            return resolved
        
        for module in self.module_to_file:
            if resolved.startswith(module + '.'):
                return module
        
        return None
    
    def analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file for imports and usage."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            analyzer = EnhancedImportAnalyzer(str(file_path))
            analyzer.visit(tree)
            
            current_module = self.get_module_name(file_path)
            if not current_module:
                return
            
            self.file_to_module[str(file_path)] = current_module
            self.module_to_file[current_module] = str(file_path)
            
            # Store detailed import information
            all_imports = analyzer.imports + analyzer.from_imports
            self.detailed_imports[current_module] = all_imports
            
            # Analyze import usage
            self.analyze_import_usage(current_module, analyzer)
            
            # Build dependency graph
            for import_info in all_imports:
                if import_info['type'] == 'import':
                    resolved = self.resolve_import_to_module(import_info['module'], current_module)
                    if resolved and resolved != current_module:
                        self.module_graph[current_module].add(resolved)
                elif import_info['type'] == 'from_import':
                    resolved = self.resolve_import_to_module(import_info['module'], current_module)
                    if resolved and resolved != current_module:
                        self.module_graph[current_module].add(resolved)
        
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
    
    def analyze_import_usage(self, module: str, analyzer: EnhancedImportAnalyzer) -> None:
        """Analyze which imports are actually used in the module."""
        used_names = analyzer.used_names
        
        for import_info in analyzer.imports:
            import_name = import_info['alias'] or import_info['module'].split('.')[-1]
            if import_name not in used_names:
                self.unused_imports[module].append({
                    'type': 'unused_import',
                    'import': import_info['module'],
                    'line': import_info['line'],
                    'reason': f"Import '{import_info['module']}' is not used"
                })
        
        for import_info in analyzer.from_imports:
            for item in import_info['items']:
                item_name = item['alias'] or item['name']
                if item_name not in used_names and item['name'] != '*':
                    self.unused_imports[module].append({
                        'type': 'unused_from_import',
                        'import': f"from {import_info['module']} import {item['name']}",
                        'line': import_info['line'],
                        'reason': f"Import '{item['name']}' from '{import_info['module']}' is not used"
                    })
    
    def find_complex_dependency_chains(self, max_depth: int = 5) -> List[List[str]]:
        """Find complex dependency chains that might indicate architectural issues."""
        complex_chains = []
        
        def dfs_chains(start: str, current: str, path: List[str], visited: Set[str]) -> None:
            if len(path) > max_depth:
                return
            
            if current in visited:
                return
            
            visited.add(current)
            path.append(current)
            
            if len(path) > 3:  # Consider chains longer than 3 as complex
                complex_chains.append(path.copy())
            
            for neighbor in self.module_graph.get(current, []):
                if neighbor not in path:  # Avoid immediate cycles
                    dfs_chains(start, neighbor, path, visited.copy())
            
            path.pop()
        
        for module in self.module_graph:
            dfs_chains(module, module, [], set())
        
        # Remove duplicates and sort by length
        unique_chains = []
        seen = set()
        for chain in complex_chains:
            chain_tuple = tuple(chain)
            if chain_tuple not in seen:
                seen.add(chain_tuple)
                unique_chains.append(chain)
        
        return sorted(unique_chains, key=len, reverse=True)
    
    def detect_cycles_dfs(self) -> List[List[str]]:
        """Detect cycles using depth-first search."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> bool:
            if node in rec_stack:
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
                dfs(neighbor)
            
            rec_stack.remove(node)
            path.pop()
            return False
        
        for node in self.module_graph:
            if node not in visited:
                dfs(node)
        
        return cycles
    
    def analyze_import_patterns(self) -> Dict[str, Any]:
        """Analyze import patterns and generate detailed statistics."""
        stats = {
            "total_modules": len(self.module_to_file),
            "total_dependencies": sum(len(deps) for deps in self.module_graph.values()),
            "modules_with_dependencies": len([m for m in self.module_graph if self.module_graph[m]]),
            "average_dependencies": 0,
            "max_dependencies": 0,
            "most_dependent_module": "",
            "dependency_distribution": defaultdict(int),
            "unused_imports_count": sum(len(unused) for unused in self.unused_imports.values()),
            "modules_with_unused_imports": len([m for m in self.unused_imports if self.unused_imports[m]]),
            "complex_chains_count": len(self.complex_chains),
            "external_dependencies": set(),
            "internal_dependencies": set()
        }
        
        if stats["modules_with_dependencies"] > 0:
            stats["average_dependencies"] = stats["total_dependencies"] / stats["modules_with_dependencies"]
        
        # Analyze dependency patterns
        for module, deps in self.module_graph.items():
            dep_count = len(deps)
            stats["dependency_distribution"][dep_count] += 1
            
            if dep_count > stats["max_dependencies"]:
                stats["max_dependencies"] = dep_count
                stats["most_dependent_module"] = module
            
            for dep in deps:
                if dep in self.module_to_file:
                    stats["internal_dependencies"].add(dep)
                else:
                    stats["external_dependencies"].add(dep)
        
        # Convert sets to lists for JSON serialization
        stats["external_dependencies"] = list(stats["external_dependencies"])
        stats["internal_dependencies"] = list(stats["internal_dependencies"])
        
        return stats
    
    def generate_recommendations(self, cycles: List[List[str]], stats: Dict[str, Any]) -> List[str]:
        """Generate comprehensive recommendations for improving import structure."""
        recommendations = []
        
        # Circular import recommendations
        if cycles:
            recommendations.append(f"🚨 CIRCULAR IMPORTS: Found {len(cycles)} circular import cycle(s)")
            for i, cycle in enumerate(cycles, 1):
                recommendations.append(f"   Cycle {i}: {' → '.join(cycle)}")
        else:
            recommendations.append("✅ No circular imports detected")
        
        # Unused import recommendations
        if stats["unused_imports_count"] > 0:
            recommendations.append(f"🧹 UNUSED IMPORTS: Found {stats['unused_imports_count']} unused imports in {stats['modules_with_unused_imports']} modules")
            recommendations.append("   • Run 'autoflake --remove-all-unused-imports --in-place src/**/*.py' to clean up")
            recommendations.append("   • Consider using 'isort' and 'black' for import organization")
        else:
            recommendations.append("✅ No unused imports detected")
        
        # Complex dependency chain recommendations
        if stats["complex_chains_count"] > 0:
            recommendations.append(f"🔗 COMPLEX CHAINS: Found {stats['complex_chains_count']} complex dependency chains")
            recommendations.append("   • Consider breaking long dependency chains")
            recommendations.append("   • Use dependency injection to reduce coupling")
        else:
            recommendations.append("✅ No overly complex dependency chains")
        
        # Architecture recommendations
        if stats["max_dependencies"] > 10:
            recommendations.append(f"⚠️  HIGH COUPLING: Module '{stats['most_dependent_module']}' has {stats['max_dependencies']} dependencies")
            recommendations.append("   • Consider breaking this module into smaller components")
            recommendations.append("   • Use interfaces to reduce direct dependencies")
        
        # General recommendations
        recommendations.extend([
            "",
            "🛠️  GENERAL RECOMMENDATIONS:",
            "   • Follow the dependency inversion principle",
            "   • Use abstract base classes in the interfaces module",
            "   • Keep modules focused on single responsibilities",
            "   • Consider using dependency injection containers",
            "   • Regularly review and refactor import structures"
        ])
        
        return recommendations
    
    def find_python_files(self) -> List[Path]:
        """Find all Python files in the source directory."""
        python_files = []
        
        for root, dirs, files in os.walk(self.src_path):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return python_files
    
    def run_analysis(self) -> Dict[str, Any]:
        """Run the complete enhanced import analysis."""
        print("🔍 Starting enhanced import analysis...")
        
        # Find and analyze all Python files
        python_files = self.find_python_files()
        print(f"📁 Found {len(python_files)} Python files to analyze")
        
        for file_path in python_files:
            self.analyze_file(file_path)
        
        print(f"📊 Analyzed {len(self.module_to_file)} modules")
        
        # Detect circular imports
        print("🔄 Detecting circular dependencies...")
        cycles = self.detect_cycles_dfs()
        
        # Find complex dependency chains
        print("🔗 Analyzing dependency chains...")
        self.complex_chains = self.find_complex_dependency_chains()
        
        # Generate statistics
        print("📈 Generating statistics...")
        stats = self.analyze_import_patterns()
        
        # Generate recommendations
        recommendations = self.generate_recommendations(cycles, stats)
        
        # Compile results
        self.analysis_results = {
            "circular_dependencies": cycles,
            "complex_dependency_chains": self.complex_chains[:10],  # Top 10 most complex
            "unused_imports": dict(self.unused_imports),
            "import_graph": {k: list(v) for k, v in self.module_graph.items()},
            "detailed_imports": self.detailed_imports,
            "module_to_file": self.module_to_file,
            "file_to_module": self.file_to_module,
            "statistics": stats,
            "recommendations": recommendations
        }
        
        return self.analysis_results
    
    def print_results(self) -> None:
        """Print comprehensive analysis results to console."""
        results = self.analysis_results
        
        print("\n" + "="*80)
        print("🔍 ENHANCED IMPORT ANALYSIS RESULTS")
        print("="*80)
        
        # Print statistics
        stats = results["statistics"]
        print(f"\n📊 STATISTICS:")
        print(f"   Total modules analyzed: {stats['total_modules']}")
        print(f"   Total dependencies: {stats['total_dependencies']}")
        print(f"   Modules with dependencies: {stats['modules_with_dependencies']}")
        print(f"   Average dependencies per module: {stats['average_dependencies']:.2f}")
        print(f"   Module with most dependencies: {stats['most_dependent_module']} ({stats['max_dependencies']} deps)")
        print(f"   Unused imports found: {stats['unused_imports_count']}")
        print(f"   Modules with unused imports: {stats['modules_with_unused_imports']}")
        print(f"   Complex dependency chains: {stats['complex_chains_count']}")
        
        # Print circular dependencies
        cycles = results["circular_dependencies"]
        if cycles:
            print(f"\n🚨 CIRCULAR DEPENDENCIES: {len(cycles)} found")
            for i, cycle in enumerate(cycles, 1):
                print(f"   Cycle {i}: {' → '.join(cycle)}")
        else:
            print(f"\n✅ NO CIRCULAR DEPENDENCIES")
        
        # Print unused imports summary
        unused = results["unused_imports"]
        if any(unused.values()):
            print(f"\n🧹 UNUSED IMPORTS SUMMARY:")
            for module, unused_list in unused.items():
                if unused_list:
                    print(f"   {module}: {len(unused_list)} unused imports")
        
        # Print complex chains summary
        complex_chains = results["complex_dependency_chains"]
        if complex_chains:
            print(f"\n🔗 COMPLEX DEPENDENCY CHAINS (Top 5):")
            for i, chain in enumerate(complex_chains[:5], 1):
                print(f"   Chain {i} ({len(chain)} modules): {' → '.join(chain[:3])}{'...' if len(chain) > 3 else ''}")
        
        # Print recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in results["recommendations"]:
            print(f"   {rec}")
        
        print("\n" + "="*80)
    
    def save_results(self, output_file: str = "enhanced_import_analysis.json") -> None:
        """Save analysis results to a JSON file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, indent=2, ensure_ascii=False)
        print(f"💾 Results saved to {output_file}")


def main():
    """Main function to run the enhanced import analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced import analysis for Python codebase")
    parser.add_argument("--src", default="src", help="Source directory to analyze (default: src)")
    parser.add_argument("--output", default="enhanced_import_analysis.json", 
                       help="Output file for results")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress console output")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.src):
        print(f"❌ Error: Source directory '{args.src}' does not exist")
        sys.exit(1)
    
    detector = EnhancedCircularImportDetector(args.src)
    results = detector.run_analysis()
    
    if not args.quiet:
        detector.print_results()
    
    detector.save_results(args.output)
    
    # Exit with error code if issues found
    issues_found = (
        len(results["circular_dependencies"]) > 0 or
        results["statistics"]["unused_imports_count"] > 0 or
        results["statistics"]["complex_chains_count"] > 10
    )
    
    if issues_found:
        print(f"\n⚠️  Analysis complete: Issues found that may need attention")
        sys.exit(1)
    else:
        print(f"\n✅ Analysis complete: Import structure looks good")
        sys.exit(0)


if __name__ == "__main__":
    main()