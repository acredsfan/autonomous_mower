#!/usr/bin/env python3
"""
Import Validation Script

This script validates that all imports in the codebase work correctly
and that there are no hidden import issues that could cause runtime errors.
"""

import sys
import importlib
import traceback
from pathlib import Path
from typing import List, Dict, Set, Tuple
import json


class ImportValidator:
    """Validates that all imports in the codebase work correctly."""
    
    def __init__(self, src_path: str = "src"):
        self.src_path = Path(src_path)
        self.validation_results = {
            "successful_imports": [],
            "failed_imports": [],
            "import_errors": {},
            "statistics": {},
            "recommendations": []
        }
    
    def get_all_modules(self) -> List[str]:
        """Get all Python modules in the source directory."""
        modules = []
        
        for root, dirs, files in self.src_path.rglob("*.py"):
            # Skip __pycache__ directories
            if "__pycache__" in str(root):
                continue
            
            # Convert file path to module name
            relative_path = root.relative_to(self.src_path)
            
            if root.name == "__init__.py":
                # Package module
                if relative_path.parent != Path("."):
                    module_name = str(relative_path.parent).replace("/", ".")
                    modules.append(module_name)
            else:
                # Regular module
                module_name = str(relative_path.with_suffix("")).replace("/", ".")
                modules.append(module_name)
        
        return sorted(set(modules))
    
    def validate_module_import(self, module_name: str) -> Tuple[bool, str]:
        """Validate that a single module can be imported successfully."""
        try:
            # Add src to Python path if not already there
            src_path_str = str(self.src_path.absolute())
            if src_path_str not in sys.path:
                sys.path.insert(0, src_path_str)
            
            # Try to import the module
            importlib.import_module(module_name)
            return True, "Success"
        
        except ImportError as e:
            return False, f"ImportError: {str(e)}"
        except SyntaxError as e:
            return False, f"SyntaxError: {str(e)}"
        except Exception as e:
            return False, f"Error: {type(e).__name__}: {str(e)}"
    
    def run_validation(self) -> Dict:
        """Run import validation on all modules."""
        print("🔍 Starting import validation...")
        
        # Get all modules
        modules = self.get_all_modules()
        print(f"📁 Found {len(modules)} modules to validate")
        
        successful_imports = []
        failed_imports = []
        import_errors = {}
        
        for i, module in enumerate(modules, 1):
            print(f"   Validating {i}/{len(modules)}: {module}", end="")
            
            success, error_msg = self.validate_module_import(module)
            
            if success:
                successful_imports.append(module)
                print(" ✅")
            else:
                failed_imports.append(module)
                import_errors[module] = error_msg
                print(f" ❌ - {error_msg}")
        
        # Generate statistics
        total_modules = len(modules)
        success_count = len(successful_imports)
        failure_count = len(failed_imports)
        success_rate = (success_count / total_modules * 100) if total_modules > 0 else 0
        
        statistics = {
            "total_modules": total_modules,
            "successful_imports": success_count,
            "failed_imports": failure_count,
            "success_rate": success_rate
        }
        
        # Generate recommendations
        recommendations = self.generate_recommendations(statistics, import_errors)
        
        # Store results
        self.validation_results = {
            "successful_imports": successful_imports,
            "failed_imports": failed_imports,
            "import_errors": import_errors,
            "statistics": statistics,
            "recommendations": recommendations
        }
        
        return self.validation_results
    
    def generate_recommendations(self, stats: Dict, errors: Dict[str, str]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        if stats["success_rate"] == 100:
            recommendations.append("✅ All modules import successfully!")
            recommendations.append("✅ No circular import issues detected during runtime validation")
            recommendations.append("✅ Import structure is healthy and functional")
        else:
            recommendations.append(f"⚠️  {stats['failed_imports']} modules failed to import ({100-stats['success_rate']:.1f}% failure rate)")
            
            # Analyze error patterns
            error_types = {}
            for error in errors.values():
                error_type = error.split(":")[0]
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            for error_type, count in error_types.items():
                recommendations.append(f"   • {error_type}: {count} modules")
            
            recommendations.append("")
            recommendations.append("🛠️  Recommended actions:")
            recommendations.append("   • Review failed imports and fix missing dependencies")
            recommendations.append("   • Check for typos in import statements")
            recommendations.append("   • Ensure all required packages are installed")
            recommendations.append("   • Verify module paths and structure")
        
        return recommendations
    
    def print_results(self) -> None:
        """Print validation results to console."""
        results = self.validation_results
        stats = results["statistics"]
        
        print("\n" + "="*80)
        print("🔍 IMPORT VALIDATION RESULTS")
        print("="*80)
        
        print(f"\n📊 STATISTICS:")
        print(f"   Total modules: {stats['total_modules']}")
        print(f"   Successful imports: {stats['successful_imports']}")
        print(f"   Failed imports: {stats['failed_imports']}")
        print(f"   Success rate: {stats['success_rate']:.1f}%")
        
        if results["failed_imports"]:
            print(f"\n❌ FAILED IMPORTS:")
            for module in results["failed_imports"]:
                error = results["import_errors"][module]
                print(f"   {module}: {error}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in results["recommendations"]:
            print(f"   {rec}")
        
        print("\n" + "="*80)
    
    def save_results(self, output_file: str = "import_validation_results.json") -> None:
        """Save validation results to a JSON file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.validation_results, f, indent=2, ensure_ascii=False)
        print(f"💾 Results saved to {output_file}")


def main():
    """Main function to run import validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate imports in Python codebase")
    parser.add_argument("--src", default="src", help="Source directory to validate (default: src)")
    parser.add_argument("--output", default="import_validation_results.json", 
                       help="Output file for results")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress console output")
    
    args = parser.parse_args()
    
    if not Path(args.src).exists():
        print(f"❌ Error: Source directory '{args.src}' does not exist")
        sys.exit(1)
    
    validator = ImportValidator(args.src)
    results = validator.run_validation()
    
    if not args.quiet:
        validator.print_results()
    
    validator.save_results(args.output)
    
    # Exit with error code if imports failed
    if results["statistics"]["success_rate"] < 100:
        print(f"\n❌ Validation failed: {results['statistics']['failed_imports']} modules could not be imported")
        sys.exit(1)
    else:
        print(f"\n✅ Validation successful: All modules import correctly")
        sys.exit(0)


if __name__ == "__main__":
    main()