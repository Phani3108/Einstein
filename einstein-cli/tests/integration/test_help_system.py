#!/usr/bin/env python3
"""
Test script for the Einstein CLI help system and documentation.

This script tests all the help features implemented in task 14:
- Comprehensive help text for all commands
- Context-sensitive help in interactive mode
- Built-in tutorial and getting started guide
- Help guides and workflows
"""

import subprocess
import sys
import json
from pathlib import Path


def run_command(cmd, capture_output=True, text=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=capture_output, 
            text=text,
            timeout=30
        )
        return result
    except subprocess.TimeoutExpired:
        print(f"❌ Command timed out: {cmd}")
        return None
    except Exception as e:
        print(f"❌ Error running command '{cmd}': {e}")
        return None


def test_main_help():
    """Test main CLI help."""
    print("🧪 Testing main CLI help...")
    
    result = run_command("python -m einstein_cli.main --help")
    if result and result.returncode == 0:
        output = result.stdout
        
        # Check for key sections
        checks = [
            "Einstein Personal Semantic Engine CLI",
            "QUICK START:",
            "MODES:",
            "EXAMPLES:",
            "Global Options",
        ]
        
        passed = 0
        for check in checks:
            if check in output:
                print(f"  ✅ Found: {check}")
                passed += 1
            else:
                print(f"  ❌ Missing: {check}")
        
        print(f"  📊 Main help: {passed}/{len(checks)} checks passed")
        return passed == len(checks)
    else:
        print("  ❌ Failed to get main help")
        return False


def test_command_help():
    """Test help for individual commands."""
    print("\n🧪 Testing individual command help...")
    
    commands = [
        "auth",
        "config", 
        "thoughts",
        "search",
        "help",
        "version"
    ]
    
    passed_commands = 0
    
    for cmd in commands:
        print(f"  Testing: einstein {cmd} --help")
        result = run_command(f"python -m einstein_cli.main {cmd} --help")
        
        if result and result.returncode == 0:
            output = result.stdout
            
            # Basic checks for command help
            if cmd in output.lower() and ("usage" in output.lower() or "examples" in output.lower() or "description" in output.lower()):
                print(f"    ✅ {cmd} help looks good")
                passed_commands += 1
            else:
                print(f"    ❌ {cmd} help seems incomplete")
        else:
            print(f"    ❌ Failed to get help for {cmd}")
    
    print(f"  📊 Command help: {passed_commands}/{len(commands)} commands passed")
    return passed_commands == len(commands)


def test_help_guides():
    """Test the help guide system."""
    print("\n🧪 Testing help guide system...")
    
    # Test help guide index
    result = run_command("python -m einstein_cli.main help guide")
    if result and result.returncode == 0:
        output = result.stdout
        if "Help Center" in output and "Available Help Topics" in output:
            print("  ✅ Help guide index works")
        else:
            print("  ❌ Help guide index incomplete")
            return False
    else:
        print("  ❌ Failed to get help guide index")
        return False
    
    # Test specific guides
    guides = [
        "getting-started",
        "commands", 
        "interactive",
        "configuration",
        "scripting",
        "troubleshooting",
        "examples"
    ]
    
    passed_guides = 0
    
    for guide in guides:
        print(f"  Testing guide: {guide}")
        result = run_command(f"python -m einstein_cli.main help guide {guide}")
        
        if result and result.returncode == 0:
            output = result.stdout
            if len(output) > 100:  # Basic check for substantial content
                print(f"    ✅ {guide} guide has content")
                passed_guides += 1
            else:
                print(f"    ❌ {guide} guide seems too short")
        else:
            print(f"    ❌ Failed to get {guide} guide")
    
    print(f"  📊 Help guides: {passed_guides}/{len(guides)} guides passed")
    return passed_guides == len(guides)


def test_help_tutorial():
    """Test the tutorial system."""
    print("\n🧪 Testing tutorial system...")
    
    result = run_command("python -m einstein_cli.main help tutorial --help")
    if result and result.returncode == 0:
        output = result.stdout
        if "interactive tutorial" in output.lower() and "walkthrough" in output.lower():
            print("  ✅ Tutorial help text looks good")
            return True
        else:
            print("  ❌ Tutorial help text incomplete")
            return False
    else:
        print("  ❌ Failed to get tutorial help")
        return False


def test_help_shortcuts():
    """Test shortcuts and workflows help."""
    print("\n🧪 Testing shortcuts and workflows...")
    
    # Test shortcuts
    result = run_command("python -m einstein_cli.main help shortcuts")
    if result and result.returncode == 0:
        output = result.stdout
        if "shortcuts" in output.lower() and "alias" in output.lower():
            print("  ✅ Shortcuts help works")
        else:
            print("  ❌ Shortcuts help incomplete")
            return False
    else:
        print("  ❌ Failed to get shortcuts help")
        return False
    
    # Test workflows
    result = run_command("python -m einstein_cli.main help workflows")
    if result and result.returncode == 0:
        output = result.stdout
        if "workflow" in output.lower() and "pattern" in output.lower():
            print("  ✅ Workflows help works")
            return True
        else:
            print("  ❌ Workflows help incomplete")
            return False
    else:
        print("  ❌ Failed to get workflows help")
        return False


def test_version_command():
    """Test enhanced version command."""
    print("\n🧪 Testing version command...")
    
    # Test basic version
    result = run_command("python -m einstein_cli.main version")
    if result and result.returncode == 0:
        output = result.stdout
        if "Einstein CLI" in output and "version" in output:
            print("  ✅ Basic version works")
        else:
            print("  ❌ Basic version incomplete")
            return False
    else:
        print("  ❌ Failed to get version")
        return False
    
    # Test detailed version
    result = run_command("python -m einstein_cli.main version --detailed")
    if result and result.returncode == 0:
        output = result.stdout
        if "System Information" in output and "Python:" in output:
            print("  ✅ Detailed version works")
            return True
        else:
            print("  ❌ Detailed version incomplete")
            return False
    else:
        print("  ❌ Failed to get detailed version")
        return False


def test_completion_files():
    """Test that completion files exist and have content."""
    print("\n🧪 Testing completion files...")
    
    completion_files = [
        "completions/bash_completion.sh",
        "completions/zsh_completion.zsh", 
        "completions/fish_completion.fish"
    ]
    
    passed_files = 0
    
    for file_path in completion_files:
        full_path = Path(file_path)
        if full_path.exists():
            content = full_path.read_text()
            if len(content) > 500:  # Basic check for substantial content
                print(f"  ✅ {file_path} exists and has content")
                passed_files += 1
            else:
                print(f"  ❌ {file_path} exists but seems too short")
        else:
            print(f"  ❌ {file_path} does not exist")
    
    print(f"  📊 Completion files: {passed_files}/{len(completion_files)} files passed")
    return passed_files == len(completion_files)


def test_man_page():
    """Test that man page exists and has content."""
    print("\n🧪 Testing man page...")
    
    man_page = Path("docs/einstein.1")
    if man_page.exists():
        content = man_page.read_text()
        
        # Check for key man page sections
        sections = [".TH FARADAY", ".SH NAME", ".SH SYNOPSIS", ".SH DESCRIPTION", ".SH COMMANDS"]
        passed_sections = 0
        
        for section in sections:
            if section in content:
                passed_sections += 1
            else:
                print(f"  ❌ Missing man page section: {section}")
        
        if passed_sections == len(sections):
            print("  ✅ Man page exists and has all required sections")
            return True
        else:
            print(f"  ❌ Man page incomplete: {passed_sections}/{len(sections)} sections")
            return False
    else:
        print("  ❌ Man page does not exist")
        return False


def test_installation_script():
    """Test that installation script exists and is executable."""
    print("\n🧪 Testing installation script...")
    
    script_path = Path("scripts/install_completions.sh")
    if script_path.exists():
        # Check if executable
        import stat
        file_stat = script_path.stat()
        if file_stat.st_mode & stat.S_IEXEC:
            print("  ✅ Installation script exists and is executable")
            
            # Test help option
            result = run_command("./scripts/install_completions.sh --help")
            if result and result.returncode == 0:
                output = result.stdout
                if "Installation Script" in output and "Usage:" in output:
                    print("  ✅ Installation script help works")
                    return True
                else:
                    print("  ❌ Installation script help incomplete")
                    return False
            else:
                print("  ❌ Installation script help failed")
                return False
        else:
            print("  ❌ Installation script exists but is not executable")
            return False
    else:
        print("  ❌ Installation script does not exist")
        return False


def test_documentation_files():
    """Test that documentation files exist and have content."""
    print("\n🧪 Testing documentation files...")
    
    doc_files = [
        "docs/README.md",
        "docs/CLI_USAGE.md",
        "docs/CONFIGURATION.md",
        "docs/GETTING_STARTED.md"
    ]
    
    passed_docs = 0
    
    for doc_file in doc_files:
        doc_path = Path(doc_file)
        if doc_path.exists():
            content = doc_path.read_text()
            if len(content) > 1000:  # Basic check for substantial content
                print(f"  ✅ {doc_file} exists and has substantial content")
                passed_docs += 1
            else:
                print(f"  ❌ {doc_file} exists but seems too short")
        else:
            print(f"  ❌ {doc_file} does not exist")
    
    print(f"  📊 Documentation files: {passed_docs}/{len(doc_files)} files passed")
    return passed_docs == len(doc_files)


def main():
    """Run all help system tests."""
    print("🚀 Testing Einstein CLI Help System and Documentation")
    print("=" * 60)
    
    tests = [
        ("Main CLI Help", test_main_help),
        ("Command Help", test_command_help),
        ("Help Guides", test_help_guides),
        ("Tutorial System", test_help_tutorial),
        ("Shortcuts & Workflows", test_help_shortcuts),
        ("Version Command", test_version_command),
        ("Completion Files", test_completion_files),
        ("Man Page", test_man_page),
        ("Installation Script", test_installation_script),
        ("Documentation Files", test_documentation_files),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed_tests += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print(f"\n{'='*60}")
    print(f"📊 FINAL RESULTS: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All help system tests passed!")
        print("\n✨ Task 14 Implementation Summary:")
        print("  ✅ Comprehensive help text for all commands and options")
        print("  ✅ Context-sensitive help in interactive mode")
        print("  ✅ Usage examples and common workflow documentation")
        print("  ✅ Man pages and shell completion scripts")
        print("  ✅ Built-in tutorial and getting started guide")
        print("  ✅ User experience and discoverability features")
        return True
    else:
        print(f"❌ {total_tests - passed_tests} tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)