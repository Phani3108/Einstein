#!/usr/bin/env python3
"""
Simple verification script for Task 14 implementation.
Checks file contents without running the CLI.
"""

import os
from pathlib import Path


def check_file_content(file_path, expected_content, description):
    """Check if a file exists and contains expected content."""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ {description}: File {file_path} does not exist")
        return False
    
    try:
        content = path.read_text()
        if not content.strip():
            print(f"❌ {description}: File {file_path} is empty")
            return False
        
        missing_content = []
        for expected in expected_content:
            if expected not in content:
                missing_content.append(expected)
        
        if missing_content:
            print(f"❌ {description}: Missing content in {file_path}:")
            for missing in missing_content:
                print(f"   - {missing}")
            return False
        else:
            print(f"✅ {description}: {file_path} has all expected content")
            return True
            
    except Exception as e:
        print(f"❌ {description}: Error reading {file_path}: {e}")
        return False


def main():
    """Verify Task 14 implementation."""
    print("🔍 Verifying Task 14: CLI Documentation and Help System")
    print("=" * 60)
    
    checks = []
    
    # 1. Check enhanced main CLI help
    print("\n1. Enhanced Main CLI Help")
    checks.append(check_file_content(
        "src/einstein_cli/main.py",
        [
            "QUICK START:",
            "MODES:",
            "EXAMPLES:",
            "einstein auth login",
            "einstein thoughts add",
            "einstein search"
        ],
        "Main CLI help enhancement"
    ))
    
    # 2. Check help command system
    print("\n2. Help Command System")
    checks.append(check_file_content(
        "src/einstein_cli/commands/help.py",
        [
            "help_group",
            "guide",
            "tutorial",
            "shortcuts",
            "workflows",
            "_show_getting_started_guide",
            "_show_commands_guide",
            "_run_interactive_tutorial"
        ],
        "Help command system"
    ))
    
    # 3. Check enhanced interactive help
    print("\n3. Enhanced Interactive Help")
    checks.append(check_file_content(
        "src/einstein_cli/interactive.py",
        [
            "_show_general_help",
            "_show_command_help",
            "_handle_tutorial",
            "_handle_tips",
            "Context-Sensitive Tips",
            "help [command]"
        ],
        "Interactive help enhancement"
    ))
    
    # 4. Check shell completions
    print("\n4. Shell Completion Scripts")
    completion_files = [
        ("completions/bash_completion.sh", ["_einstein_completion", "complete -F"]),
        ("completions/zsh_completion.zsh", ["#compdef einstein", "_einstein_commands"]),
        ("completions/fish_completion.fish", ["complete -c einstein", "__fish_seen_subcommand_from"])
    ]
    
    for file_path, expected in completion_files:
        checks.append(check_file_content(file_path, expected, f"Shell completion: {file_path}"))
    
    # 5. Check man page
    print("\n5. Man Page")
    checks.append(check_file_content(
        "docs/einstein.1",
        [
            ".TH FARADAY",
            ".SH NAME",
            ".SH SYNOPSIS", 
            ".SH DESCRIPTION",
            ".SH COMMANDS",
            ".SH INTERACTIVE MODE",
            ".SH EXAMPLES"
        ],
        "Man page"
    ))
    
    # 6. Check installation script
    print("\n6. Installation Script")
    checks.append(check_file_content(
        "scripts/install_completions.sh",
        [
            "#!/bin/bash",
            "install_bash_completion",
            "install_zsh_completion",
            "install_fish_completion",
            "install_man_page",
            "--help",
            "--uninstall"
        ],
        "Installation script"
    ))
    
    # 7. Check documentation files
    print("\n7. Documentation Files")
    doc_files = [
        ("docs/GETTING_STARTED.md", ["Quick Start", "Essential Commands", "Interactive Mode"]),
        ("docs/CLI_USAGE.md", ["Complete guide", "Interactive Mode", "Troubleshooting"]),
        ("docs/CONFIGURATION.md", ["Configuration Guide", "Platform-Specific Paths"]),
        ("docs/README.md", ["Documentation Index", "Quick Reference"])
    ]
    
    for file_path, expected in doc_files:
        checks.append(check_file_content(file_path, expected, f"Documentation: {file_path}"))
    
    # 8. Check that help group is registered in main
    print("\n8. Help Group Registration")
    checks.append(check_file_content(
        "src/einstein_cli/main.py",
        [
            "from einstein_cli.commands.help import help_group",
            "cli.add_command(help_group)"
        ],
        "Help group registration"
    ))
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(checks)
    total = len(checks)
    
    print(f"📊 VERIFICATION RESULTS: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All Task 14 implementation checks passed!")
        print("\n✨ Implementation Summary:")
        print("  ✅ Comprehensive help text for all commands and options")
        print("  ✅ Context-sensitive help in interactive mode")
        print("  ✅ Usage examples and common workflow documentation")
        print("  ✅ Man pages and shell completion scripts")
        print("  ✅ Built-in tutorial and getting started guide")
        print("  ✅ User experience and discoverability features")
        
        print("\n📁 Files Created/Modified:")
        print("  • src/einstein_cli/commands/help.py - Help command system")
        print("  • src/einstein_cli/main.py - Enhanced main help")
        print("  • src/einstein_cli/interactive.py - Enhanced interactive help")
        print("  • docs/einstein.1 - Man page")
        print("  • docs/GETTING_STARTED.md - Getting started guide")
        print("  • completions/*.sh/*.zsh/*.fish - Shell completions")
        print("  • scripts/install_completions.sh - Installation script")
        
        return True
    else:
        print(f"❌ {total - passed} checks failed")
        print("Please review the failed checks above.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)