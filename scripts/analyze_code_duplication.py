#!/usr/bin/env python3
"""
Code Duplication Analyzer

This script analyzes the codebase for:
1. Duplicate or near-duplicate functions and classes
2. Redundant configuration handling patterns
3. Repeated error handling or logging patterns

Usage:
    python scripts/analyze_code_duplication.py

Output:
    - Generates a JSON report of duplicated code
    - Provides a markdown summary of findings
"""

import os
import re
import json
import ast
import hashlib
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Any, Optional
import argparse
from pathlib import Path

# Configuration
SRC_DIR = "src/mower"
REPORT_FILE = "code_duplication_analysis.json"
SUMMARY_FILE = "code_duplication_summary.md"
MIN_DUPLICATE_LINES = 5  # Minimum number of lines to consider as duplication
SIMILARITY_THRESHOLD = 0.8  # Threshold for considering functions similar (0.0-1.0)

# Patterns to identify
CONFIG_PATTERNS = [
    r"(?:load|read|parse)_config",
    r"config\.[\"']?get",
    r"os\.environ\.get",
    r"json\.load.*config",
    r"config_manager",
    r"ConfigManager",
]

ERROR_PATTERNS = [
    r"try\s*:",
    r"except\s+\w+",
    r"except\s*:",
    r"raise\s+\w+",
    r"log(?:ger)?\.(?:error|exception|warning)",
    r"handle_(?:error|exception)",
]

LOGGING_PATTERNS = [
    r"log(?:ger)?\.(?:debug|info|warning|error|critical|exception)",
    r"logging\.\w+",
    r"self\.log",
]


class FunctionVisitor(ast.NodeVisitor):
    """AST visitor to extract functions and methods from Python files."""
    
    def __init__(self):
        self.functions = []
        self.current_class = None
        
    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node):
        # Get function source code
        source_lines = []
        for lineno in range(node.lineno, node.end_lineno + 1):
            source_lines.append(f"Line {lineno}")  # Placeholder, actual code will be extracted from file
            
        function_info = {
            "name": node.name,
            "class": self.current_class,
            "lineno": node.lineno,
            "end_lineno": node.end_lineno,
            "source_lines": source_lines,
            "args": [arg.arg for arg in node.args.args if arg.arg != "self"],
            "decorators": [d.id if isinstance(d, ast.Name) else "" for d in node.decorator_list],
        }
        self.functions.append(function_info)
        self.generic_visit(node)


def get_file_content(file_path: str) -> str:
    """Read file content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""


def get_file_lines(file_path: str) -> List[str]:
    """Read file lines."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.readlines()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []


def extract_functions(file_path: str) -> List[Dict[str, Any]]:
    """Extract functions and methods from a Python file using AST."""
    content = get_file_content(file_path)
    if not content:
        return []
    
    try:
        tree = ast.parse(content)
        visitor = FunctionVisitor()
        visitor.visit(tree)
        
        # Get actual source lines
        file_lines = get_file_lines(file_path)
        for func in visitor.functions:
            start = func["lineno"] - 1  # 0-indexed
            end = func["end_lineno"]
            func["source_lines"] = file_lines[start:end]
            func["source"] = "".join(func["source_lines"])
            # Create a normalized version for comparison (remove comments, whitespace)
            func["normalized_source"] = normalize_code(func["source"])
            # Create a hash for quick comparison
            func["hash"] = hashlib.md5(func["normalized_source"].encode()).hexdigest()
            func["file_path"] = file_path
            
        return visitor.functions
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return []
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []


def normalize_code(code: str) -> str:
    """Normalize code for comparison by removing comments, extra whitespace, etc."""
    # Remove comments
    code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
    # Remove docstrings (simple approach)
    code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
    code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
    # Normalize whitespace
    code = re.sub(r'\s+', ' ', code)
    # Remove variable names in some cases to focus on structure
    # This is a simplified approach - a more sophisticated one would use AST
    return code.strip()


def calculate_similarity(code1: str, code2: str) -> float:
    """Calculate similarity between two code snippets."""
    # Simple approach using Levenshtein distance
    # For production, consider more sophisticated algorithms
    if not code1 or not code2:
        return 0.0
    
    # Simple character-based similarity
    longer = max(len(code1), len(code2))
    if longer == 0:
        return 1.0
    
    # Count matching characters
    matches = sum(c1 == c2 for c1, c2 in zip(code1, code2))
    return matches / longer


def find_duplicate_functions(functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find duplicate or near-duplicate functions."""
    # Group by hash for exact matches
    hash_groups = defaultdict(list)
    for func in functions:
        hash_groups[func["hash"]].append(func)
    
    # Find exact duplicates
    exact_duplicates = [group for group in hash_groups.values() if len(group) > 1]
    
    # Find near-duplicates using similarity
    near_duplicates = []
    processed_hashes = set()
    
    for i, func1 in enumerate(functions):
        if func1["hash"] in processed_hashes:
            continue
            
        similar_funcs = [func1]
        
        for j, func2 in enumerate(functions[i+1:], i+1):
            if func2["hash"] in processed_hashes:
                continue
                
            if len(func1["source_lines"]) >= MIN_DUPLICATE_LINES and len(func2["source_lines"]) >= MIN_DUPLICATE_LINES:
                similarity = calculate_similarity(func1["normalized_source"], func2["normalized_source"])
                if similarity >= SIMILARITY_THRESHOLD and similarity < 1.0:  # Not exact match
                    similar_funcs.append(func2)
                    processed_hashes.add(func2["hash"])
        
        if len(similar_funcs) > 1:
            near_duplicates.append(similar_funcs)
            processed_hashes.add(func1["hash"])
    
    return {
        "exact_duplicates": exact_duplicates,
        "near_duplicates": near_duplicates
    }


def find_pattern_matches(file_path: str, patterns: List[str]) -> List[Dict[str, Any]]:
    """Find lines matching specific patterns in a file."""
    content = get_file_content(file_path)
    if not content:
        return []
    
    matches = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        line_num = i + 1
        for pattern in patterns:
            if re.search(pattern, line):
                matches.append({
                    "file_path": file_path,
                    "line_num": line_num,
                    "line": line.strip(),
                    "pattern": pattern
                })
    
    return matches


def find_all_python_files(directory: str) -> List[str]:
    """Find all Python files in a directory recursively."""
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files


def analyze_code_duplication():
    """Main function to analyze code duplication."""
    print("Analyzing code duplication...")
    
    # Find all Python files
    python_files = find_all_python_files(SRC_DIR)
    print(f"Found {len(python_files)} Python files")
    
    # Extract functions from all files
    all_functions = []
    for file_path in python_files:
        functions = extract_functions(file_path)
        all_functions.extend(functions)
    
    print(f"Extracted {len(all_functions)} functions/methods")
    
    # Find duplicate functions
    duplicate_results = find_duplicate_functions(all_functions)
    exact_duplicates = duplicate_results["exact_duplicates"]
    near_duplicates = duplicate_results["near_duplicates"]
    
    print(f"Found {sum(len(group) for group in exact_duplicates)} functions in {len(exact_duplicates)} exact duplicate groups")
    print(f"Found {sum(len(group) for group in near_duplicates)} functions in {len(near_duplicates)} near-duplicate groups")
    
    # Find configuration patterns
    config_matches = []
    for file_path in python_files:
        matches = find_pattern_matches(file_path, CONFIG_PATTERNS)
        config_matches.extend(matches)
    
    print(f"Found {len(config_matches)} configuration pattern matches")
    
    # Find error handling patterns
    error_matches = []
    for file_path in python_files:
        matches = find_pattern_matches(file_path, ERROR_PATTERNS)
        error_matches.extend(matches)
    
    print(f"Found {len(error_matches)} error handling pattern matches")
    
    # Find logging patterns
    logging_matches = []
    for file_path in python_files:
        matches = find_pattern_matches(file_path, LOGGING_PATTERNS)
        logging_matches.extend(matches)
    
    print(f"Found {len(logging_matches)} logging pattern matches")
    
    # Group pattern matches by file
    config_by_file = group_matches_by_file(config_matches)
    error_by_file = group_matches_by_file(error_matches)
    logging_by_file = group_matches_by_file(logging_matches)
    
    # Prepare results
    results = {
        "exact_duplicates": [
            {
                "group_id": i,
                "count": len(group),
                "functions": [
                    {
                        "name": f["name"],
                        "class": f["class"],
                        "file_path": f["file_path"],
                        "lineno": f["lineno"],
                        "end_lineno": f["end_lineno"],
                    }
                    for f in group
                ]
            }
            for i, group in enumerate(exact_duplicates)
        ],
        "near_duplicates": [
            {
                "group_id": i,
                "count": len(group),
                "similarity": "high",
                "functions": [
                    {
                        "name": f["name"],
                        "class": f["class"],
                        "file_path": f["file_path"],
                        "lineno": f["lineno"],
                        "end_lineno": f["end_lineno"],
                    }
                    for f in group
                ]
            }
            for i, group in enumerate(near_duplicates)
        ],
        "config_patterns": {
            "total_matches": len(config_matches),
            "files_with_matches": len(config_by_file),
            "top_files": get_top_files(config_by_file, 10)
        },
        "error_patterns": {
            "total_matches": len(error_matches),
            "files_with_matches": len(error_by_file),
            "top_files": get_top_files(error_by_file, 10)
        },
        "logging_patterns": {
            "total_matches": len(logging_matches),
            "files_with_matches": len(logging_by_file),
            "top_files": get_top_files(logging_by_file, 10)
        }
    }
    
    # Save results to JSON
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {REPORT_FILE}")
    
    # Generate summary markdown
    generate_summary(results)
    
    print(f"Summary saved to {SUMMARY_FILE}")
    
    return results


def group_matches_by_file(matches: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group pattern matches by file."""
    by_file = defaultdict(list)
    for match in matches:
        by_file[match["file_path"]].append(match)
    return by_file


def get_top_files(matches_by_file: Dict[str, List[Dict[str, Any]]], limit: int) -> List[Dict[str, Any]]:
    """Get top files with most matches."""
    top_files = sorted(
        [
            {"file_path": file_path, "match_count": len(matches)}
            for file_path, matches in matches_by_file.items()
        ],
        key=lambda x: x["match_count"],
        reverse=True
    )
    return top_files[:limit]


def generate_summary(results: Dict[str, Any]) -> None:
    """Generate a markdown summary of the results."""
    with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
        f.write("# Code Duplication Analysis Summary\n\n")
        
        # Exact duplicates
        f.write("## Exact Duplicate Functions\n\n")
        if results["exact_duplicates"]:
            f.write("| Group | Count | Functions |\n")
            f.write("|-------|-------|----------|\n")
            for group in results["exact_duplicates"]:
                functions_str = "<br>".join([
                    f"{func['file_path']}:{func['lineno']} - {func['class'] + '.' if func['class'] else ''}{func['name']}"
                    for func in group["functions"]
                ])
                f.write(f"| {group['group_id']} | {group['count']} | {functions_str} |\n")
        else:
            f.write("No exact duplicates found.\n")
        
        # Near duplicates
        f.write("\n## Near-Duplicate Functions\n\n")
        if results["near_duplicates"]:
            f.write("| Group | Count | Similarity | Functions |\n")
            f.write("|-------|-------|------------|----------|\n")
            for group in results["near_duplicates"]:
                functions_str = "<br>".join([
                    f"{func['file_path']}:{func['lineno']} - {func['class'] + '.' if func['class'] else ''}{func['name']}"
                    for func in group["functions"]
                ])
                f.write(f"| {group['group_id']} | {group['count']} | {group['similarity']} | {functions_str} |\n")
        else:
            f.write("No near-duplicates found.\n")
        
        # Configuration patterns
        f.write("\n## Configuration Handling Patterns\n\n")
        f.write(f"- Total matches: {results['config_patterns']['total_matches']}\n")
        f.write(f"- Files with matches: {results['config_patterns']['files_with_matches']}\n")
        f.write("\n### Top Files with Configuration Patterns\n\n")
        f.write("| File | Match Count |\n")
        f.write("|------|------------|\n")
        for file_info in results["config_patterns"]["top_files"]:
            f.write(f"| {file_info['file_path']} | {file_info['match_count']} |\n")
        
        # Error handling patterns
        f.write("\n## Error Handling Patterns\n\n")
        f.write(f"- Total matches: {results['error_patterns']['total_matches']}\n")
        f.write(f"- Files with matches: {results['error_patterns']['files_with_matches']}\n")
        f.write("\n### Top Files with Error Handling Patterns\n\n")
        f.write("| File | Match Count |\n")
        f.write("|------|------------|\n")
        for file_info in results["error_patterns"]["top_files"]:
            f.write(f"| {file_info['file_path']} | {file_info['match_count']} |\n")
        
        # Logging patterns
        f.write("\n## Logging Patterns\n\n")
        f.write(f"- Total matches: {results['logging_patterns']['total_matches']}\n")
        f.write(f"- Files with matches: {results['logging_patterns']['files_with_matches']}\n")
        f.write("\n### Top Files with Logging Patterns\n\n")
        f.write("| File | Match Count |\n")
        f.write("|------|------------|\n")
        for file_info in results["logging_patterns"]["top_files"]:
            f.write(f"| {file_info['file_path']} | {file_info['match_count']} |\n")
        
        # Recommendations
        f.write("\n## Recommendations\n\n")
        f.write("### Duplicate Code Consolidation\n\n")
        f.write("1. Create shared utility functions for the identified duplicate code\n")
        f.write("2. Refactor near-duplicate functions to use common base implementations\n")
        f.write("3. Consider using inheritance or composition for duplicate class methods\n\n")
        
        f.write("### Configuration Handling\n\n")
        f.write("1. Standardize configuration loading through a single module\n")
        f.write("2. Implement a centralized configuration manager with validation\n")
        f.write("3. Use dependency injection for configuration rather than direct imports\n\n")
        
        f.write("### Error Handling\n\n")
        f.write("1. Create standardized error handling utilities\n")
        f.write("2. Implement consistent exception hierarchies\n")
        f.write("3. Use decorators for common error handling patterns\n\n")
        
        f.write("### Logging\n\n")
        f.write("1. Standardize logging format and levels across all modules\n")
        f.write("2. Create a centralized logging configuration\n")
        f.write("3. Consider using a logging context manager for related log entries\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze code duplication in the codebase")
    parser.add_argument("--src-dir", default=SRC_DIR, help="Source directory to analyze")
    parser.add_argument("--report-file", default=REPORT_FILE, help="Output JSON report file")
    parser.add_argument("--summary-file", default=SUMMARY_FILE, help="Output markdown summary file")
    parser.add_argument("--min-lines", type=int, default=MIN_DUPLICATE_LINES, 
                        help="Minimum number of lines to consider as duplication")
    parser.add_argument("--similarity", type=float, default=SIMILARITY_THRESHOLD,
                        help="Similarity threshold (0.0-1.0)")
    
    args = parser.parse_args()
    
    SRC_DIR = args.src_dir
    REPORT_FILE = args.report_file
    SUMMARY_FILE = args.summary_file
    MIN_DUPLICATE_LINES = args.min_lines
    SIMILARITY_THRESHOLD = args.similarity
    
    analyze_code_duplication()