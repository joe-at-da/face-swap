#!/usr/bin/env python3
"""
Find potentially unused code in the project.
This script analyzes imports and function calls to identify files and functions 
that might not be used anywhere in the codebase.

Usage:
    python find_unused_code.py [--directory DIR] [--verbose]
"""

import os
import re
import sys
import argparse
import subprocess
from pathlib import Path
from collections import defaultdict, Counter

def find_python_files(directory):
    """Find all Python files in the directory."""
    result = subprocess.run(
        ["find", directory, "-name", "*.py", "-type", "f"],
        capture_output=True, text=True
    )
    return [line.strip() for line in result.stdout.splitlines()]

def extract_imports(file_path):
    """Extract all imports from a Python file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find import statements
    import_patterns = [
        r'import\s+([\w\.]+)',  # import module
        r'from\s+([\w\.]+)\s+import',  # from module import ...
    ]
    
    imports = []
    for pattern in import_patterns:
        imports.extend(re.findall(pattern, content))
    
    return imports

def extract_functions(file_path):
    """Extract all function definitions from a Python file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find function definitions
    function_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
    functions = re.findall(function_pattern, content)
    
    # Extract class names
    class_pattern = r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[:\(]'
    classes = re.findall(class_pattern, content)
    
    return functions, classes

def find_function_calls(file_path, function_name):
    """Find calls to a specific function in a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to find function calls (basic, not perfect)
    pattern = r'[^a-zA-Z0-9_]' + re.escape(function_name) + r'\s*\('
    return len(re.findall(pattern, content))

def find_class_usage(file_path, class_name):
    """Find usage of a specific class in a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to find class instantiation or inheritance
    patterns = [
        r'[^a-zA-Z0-9_]' + re.escape(class_name) + r'\s*\(',  # Instantiation
        r'class\s+[a-zA-Z0-9_]*\s*\(\s*' + re.escape(class_name) + r'[,\)]'  # Inheritance
    ]
    
    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, content))
    
    return count

def find_file_references(directory, file_path):
    """Find references to a file in other files."""
    # Get the module path
    rel_path = os.path.relpath(file_path, directory)
    module_path = os.path.splitext(rel_path)[0].replace('/', '.')
    
    # Count references
    count = 0
    for py_file in find_python_files(directory):
        if py_file == file_path:
            continue
        
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for imports of this module
        patterns = [
            r'import\s+' + re.escape(module_path),
            r'from\s+' + re.escape(module_path) + r'\s+import',
            r'import\s+.*\s+as\s+' + os.path.basename(module_path)
        ]
        
        for pattern in patterns:
            if re.search(pattern, content):
                count += 1
                break
    
    return count

def analyze_codebase(directory, verbose=False):
    """Analyze the codebase for unused code."""
    python_files = find_python_files(directory)
    
    # Track all defined functions and their usage
    all_functions = {}  # {file_path: [function_names]}
    all_classes = {}    # {file_path: [class_names]}
    
    # First pass: collect all functions and classes
    for file_path in python_files:
        functions, classes = extract_functions(file_path)
        all_functions[file_path] = functions
        all_classes[file_path] = classes
    
    # Second pass: check for usage
    unused_functions = []
    unused_classes = []
    
    for file_path, functions in all_functions.items():
        for func in functions:
            # Skip special methods
            if func.startswith('__') and func.endswith('__'):
                continue
                
            # Count calls to this function
            call_count = 0
            for check_file in python_files:
                if check_file != file_path:  # Don't count self-references
                    call_count += find_function_calls(check_file, func)
            
            if call_count == 0:
                unused_functions.append((file_path, func))
    
    for file_path, classes in all_classes.items():
        for cls in classes:
            # Count usage of this class
            usage_count = 0
            for check_file in python_files:
                if check_file != file_path:  # Don't count self-references
                    usage_count += find_class_usage(check_file, cls)
            
            if usage_count == 0:
                unused_classes.append((file_path, cls))
    
    # Check for unused files
    unused_files = []
    for file_path in python_files:
        # Skip __init__.py files
        if os.path.basename(file_path) == '__init__.py':
            continue
            
        ref_count = find_file_references(directory, file_path)
        if ref_count == 0:
            unused_files.append(file_path)
    
    # Print results
    print(f"Found {len(python_files)} Python files")
    print(f"Potentially unused files: {len(unused_files)}")
    print(f"Potentially unused functions: {len(unused_functions)}")
    print(f"Potentially unused classes: {len(unused_classes)}")
    
    if verbose:
        print("\nPotentially unused files:")
        for file_path in unused_files:
            print(f"  {file_path}")
        
        print("\nPotentially unused functions:")
        for file_path, func in unused_functions:
            print(f"  {func} in {file_path}")
        
        print("\nPotentially unused classes:")
        for file_path, cls in unused_classes:
            print(f"  {cls} in {file_path}")
    
    return {
        'unused_files': unused_files,
        'unused_functions': unused_functions,
        'unused_classes': unused_classes
    }

def main():
    parser = argparse.ArgumentParser(description='Find potentially unused code in a Python project')
    parser.add_argument('--directory', '-d', default='.', help='Directory to analyze')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed results')
    args = parser.parse_args()
    
    print(f"Analyzing code in {args.directory}...")
    analyze_codebase(args.directory, args.verbose)

if __name__ == '__main__':
    main()
