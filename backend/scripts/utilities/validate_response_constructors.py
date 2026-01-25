#!/usr/bin/env python3
"""
Validation script to check for duplicate keyword arguments in response constructors.
This prevents SyntaxError: keyword argument repeated errors.

Run this script before committing changes to catch duplicate arguments early.
"""

import ast
import sys
from pathlib import Path

def find_duplicate_kwargs(node):
    """Find duplicate keyword arguments in a function call."""
    if not isinstance(node, ast.Call):
        return []
    
    seen = set()
    duplicates = []
    
    for keyword in node.keywords:
        if keyword.arg in seen:
            duplicates.append(keyword.arg)
        seen.add(keyword.arg)
    
    return duplicates

def check_file(file_path):
    """Check a Python file for duplicate keyword arguments."""
    errors = []
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(file_path))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check if this is a PropertyResponse or PropertyDetailResponse constructor
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in ('PropertyResponse', 'PropertyDetailResponse'):
                        duplicates = find_duplicate_kwargs(node)
                        if duplicates:
                            errors.append({
                                'file': file_path,
                                'line': node.lineno,
                                'function': func_name,
                                'duplicates': duplicates
                            })
    
    except SyntaxError as e:
        # If the file has a syntax error, that's a problem too
        errors.append({
            'file': file_path,
            'line': e.lineno or 0,
            'function': 'SYNTAX_ERROR',
            'duplicates': [f'Syntax error: {e.msg}']
        })
    except Exception as e:
        print(f"Error checking {file_path}: {e}", file=sys.stderr)
    
    return errors

def main():
    """Main validation function."""
    backend_dir = Path(__file__).parent.parent
    api_routes_dir = backend_dir / 'api' / 'routes'
    
    if not api_routes_dir.exists():
        print(f"Error: {api_routes_dir} does not exist", file=sys.stderr)
        sys.exit(1)
    
    all_errors = []
    
    # Check all Python files in api/routes
    for py_file in api_routes_dir.glob('*.py'):
        errors = check_file(py_file)
        all_errors.extend(errors)
    
    if all_errors:
        print("❌ Found duplicate keyword arguments in response constructors:\n")
        for error in all_errors:
            print(f"  File: {error['file']}")
            print(f"  Line: {error['line']}")
            print(f"  Function: {error['function']}")
            print(f"  Duplicates: {', '.join(error['duplicates'])}")
            print()
        sys.exit(1)
    else:
        print("✅ No duplicate keyword arguments found!")
        sys.exit(0)

if __name__ == '__main__':
    main()
