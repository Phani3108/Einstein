#!/bin/bash
# Installation script for Einstein CLI shell completions and man page

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect shell
detect_shell() {
    if [ -n "$ZSH_VERSION" ]; then
        echo "zsh"
    elif [ -n "$BASH_VERSION" ]; then
        echo "bash"
    elif [ -n "$FISH_VERSION" ]; then
        echo "fish"
    else
        # Fallback to checking $SHELL
        case "$SHELL" in
            */zsh) echo "zsh" ;;
            */bash) echo "bash" ;;
            */fish) echo "fish" ;;
            *) echo "unknown" ;;
        esac
    fi
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPLETIONS_DIR="$PROJECT_DIR/completions"
DOCS_DIR="$PROJECT_DIR/docs"

print_status "Einstein CLI Installation Script"
print_status "================================"

# Check if completions directory exists
if [ ! -d "$COMPLETIONS_DIR" ]; then
    print_error "Completions directory not found: $COMPLETIONS_DIR"
    exit 1
fi

# Detect current shell
CURRENT_SHELL=$(detect_shell)
print_status "Detected shell: $CURRENT_SHELL"

# Install completions based on shell
install_bash_completion() {
    print_status "Installing Bash completion..."
    
    # Try system-wide installation first
    if [ -d "/etc/bash_completion.d" ] && [ -w "/etc/bash_completion.d" ]; then
        sudo cp "$COMPLETIONS_DIR/bash_completion.sh" "/etc/bash_completion.d/einstein"
        print_success "Installed system-wide Bash completion"
    elif [ -d "/usr/local/etc/bash_completion.d" ] && [ -w "/usr/local/etc/bash_completion.d" ]; then
        # macOS with Homebrew
        sudo cp "$COMPLETIONS_DIR/bash_completion.sh" "/usr/local/etc/bash_completion.d/einstein"
        print_success "Installed Homebrew Bash completion"
    else
        # User-specific installation
        mkdir -p "$HOME/.bash_completion.d"
        cp "$COMPLETIONS_DIR/bash_completion.sh" "$HOME/.bash_completion.d/einstein"
        
        # Add sourcing to .bashrc if not already present
        if ! grep -q "bash_completion.d/einstein" "$HOME/.bashrc" 2>/dev/null; then
            echo "" >> "$HOME/.bashrc"
            echo "# Einstein CLI completion" >> "$HOME/.bashrc"
            echo "source ~/.bash_completion.d/einstein" >> "$HOME/.bashrc"
            print_success "Added Einstein completion to ~/.bashrc"
        fi
        
        print_success "Installed user-specific Bash completion"
        print_warning "Restart your shell or run: source ~/.bashrc"
    fi
}

install_zsh_completion() {
    print_status "Installing Zsh completion..."
    
    # Find a suitable directory in fpath
    local zsh_completion_dir=""
    
    # Check common locations
    for dir in "/usr/local/share/zsh/site-functions" "/usr/share/zsh/site-functions" "$HOME/.zsh/completions"; do
        if [ -d "$dir" ] || mkdir -p "$dir" 2>/dev/null; then
            zsh_completion_dir="$dir"
            break
        fi
    done
    
    if [ -z "$zsh_completion_dir" ]; then
        # Create user-specific completion directory
        zsh_completion_dir="$HOME/.zsh/completions"
        mkdir -p "$zsh_completion_dir"
        
        # Add to fpath in .zshrc if not already present
        if ! grep -q "fpath.*zsh/completions" "$HOME/.zshrc" 2>/dev/null; then
            echo "" >> "$HOME/.zshrc"
            echo "# Einstein CLI completion" >> "$HOME/.zshrc"
            echo "fpath=(~/.zsh/completions \$fpath)" >> "$HOME/.zshrc"
            echo "autoload -U compinit && compinit" >> "$HOME/.zshrc"
            print_success "Added completion directory to ~/.zshrc"
        fi
    fi
    
    cp "$COMPLETIONS_DIR/zsh_completion.zsh" "$zsh_completion_dir/_einstein"
    print_success "Installed Zsh completion to $zsh_completion_dir"
    print_warning "Restart your shell or run: exec zsh"
}

install_fish_completion() {
    print_status "Installing Fish completion..."
    
    local fish_completion_dir="$HOME/.config/fish/completions"
    mkdir -p "$fish_completion_dir"
    
    cp "$COMPLETIONS_DIR/fish_completion.fish" "$fish_completion_dir/einstein.fish"
    print_success "Installed Fish completion to $fish_completion_dir"
    print_status "Fish completion is active immediately"
}

install_man_page() {
    print_status "Installing man page..."
    
    # Try system-wide installation first
    if [ -d "/usr/local/share/man/man1" ] && [ -w "/usr/local/share/man/man1" ]; then
        sudo cp "$DOCS_DIR/einstein.1" "/usr/local/share/man/man1/"
        sudo mandb >/dev/null 2>&1 || true
        print_success "Installed system-wide man page"
    elif [ -d "/usr/share/man/man1" ] && [ -w "/usr/share/man/man1" ]; then
        sudo cp "$DOCS_DIR/einstein.1" "/usr/share/man/man1/"
        sudo mandb >/dev/null 2>&1 || true
        print_success "Installed system-wide man page"
    else
        # User-specific installation
        local user_man_dir="$HOME/.local/share/man/man1"
        mkdir -p "$user_man_dir"
        cp "$DOCS_DIR/einstein.1" "$user_man_dir/"
        
        # Add to MANPATH if not already present
        if ! echo "$MANPATH" | grep -q "$HOME/.local/share/man"; then
            if ! grep -q "MANPATH.*local/share/man" "$HOME/.bashrc" 2>/dev/null; then
                echo "" >> "$HOME/.bashrc"
                echo "# Add local man pages to MANPATH" >> "$HOME/.bashrc"
                echo "export MANPATH=\"\$HOME/.local/share/man:\$MANPATH\"" >> "$HOME/.bashrc"
            fi
            
            if [ "$CURRENT_SHELL" = "zsh" ] && ! grep -q "MANPATH.*local/share/man" "$HOME/.zshrc" 2>/dev/null; then
                echo "" >> "$HOME/.zshrc"
                echo "# Add local man pages to MANPATH" >> "$HOME/.zshrc"
                echo "export MANPATH=\"\$HOME/.local/share/man:\$MANPATH\"" >> "$HOME/.zshrc"
            fi
        fi
        
        print_success "Installed user-specific man page"
        print_warning "Restart your shell to update MANPATH"
    fi
}

create_shell_aliases() {
    print_status "Creating suggested shell aliases..."
    
    local alias_file=""
    case "$CURRENT_SHELL" in
        bash) alias_file="$HOME/.bashrc" ;;
        zsh) alias_file="$HOME/.zshrc" ;;
        fish) alias_file="$HOME/.config/fish/config.fish" ;;
        *) 
            print_warning "Unknown shell, skipping alias creation"
            return
            ;;
    esac
    
    if [ -f "$alias_file" ]; then
        if ! grep -q "# Einstein CLI aliases" "$alias_file" 2>/dev/null; then
            echo "" >> "$alias_file"
            echo "# Einstein CLI aliases" >> "$alias_file"
            
            if [ "$CURRENT_SHELL" = "fish" ]; then
                echo "alias ft='einstein thoughts'" >> "$alias_file"
                echo "alias fs='einstein search'" >> "$alias_file"
                echo "alias fc='einstein config'" >> "$alias_file"
                echo "alias fa='einstein auth'" >> "$alias_file"
                echo "alias fi='einstein interactive'" >> "$alias_file"
            else
                echo "alias ft='einstein thoughts'" >> "$alias_file"
                echo "alias fs='einstein search'" >> "$alias_file"
                echo "alias fc='einstein config'" >> "$alias_file"
                echo "alias fa='einstein auth'" >> "$alias_file"
                echo "alias fi='einstein interactive'" >> "$alias_file"
            fi
            
            print_success "Added suggested aliases to $alias_file"
            print_warning "Restart your shell to use the new aliases"
        else
            print_status "Aliases already exist, skipping"
        fi
    fi
}

# Main installation logic
main() {
    print_status "Starting installation..."
    
    # Install completions based on detected shell
    case "$CURRENT_SHELL" in
        bash)
            install_bash_completion
            ;;
        zsh)
            install_zsh_completion
            ;;
        fish)
            install_fish_completion
            ;;
        *)
            print_warning "Unknown shell '$CURRENT_SHELL', installing all completions"
            install_bash_completion
            install_zsh_completion
            install_fish_completion
            ;;
    esac
    
    # Install man page
    if [ -f "$DOCS_DIR/einstein.1" ]; then
        install_man_page
    else
        print_warning "Man page not found, skipping"
    fi
    
    # Create shell aliases
    create_shell_aliases
    
    print_success "Installation completed!"
    print_status ""
    print_status "Next steps:"
    print_status "1. Restart your shell or source your shell config file"
    print_status "2. Try tab completion: einstein <TAB>"
    print_status "3. Read the man page: man einstein"
    print_status "4. Start with: einstein help tutorial"
    print_status ""
    print_status "Suggested aliases are now available:"
    print_status "  ft  = einstein thoughts"
    print_status "  fs  = einstein search"
    print_status "  fc  = einstein config"
    print_status "  fa  = einstein auth"
    print_status "  fi  = einstein interactive"
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Einstein CLI Installation Script"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --uninstall    Uninstall completions and man page"
        echo ""
        echo "This script installs:"
        echo "  • Shell completions for your current shell"
        echo "  • Man page for 'man einstein'"
        echo "  • Suggested shell aliases"
        echo ""
        exit 0
        ;;
    --uninstall)
        print_status "Uninstalling Einstein CLI completions and man page..."
        
        # Remove completions
        rm -f "/etc/bash_completion.d/einstein" 2>/dev/null || true
        rm -f "/usr/local/etc/bash_completion.d/einstein" 2>/dev/null || true
        rm -f "$HOME/.bash_completion.d/einstein" 2>/dev/null || true
        rm -f "/usr/local/share/zsh/site-functions/_einstein" 2>/dev/null || true
        rm -f "/usr/share/zsh/site-functions/_einstein" 2>/dev/null || true
        rm -f "$HOME/.zsh/completions/_einstein" 2>/dev/null || true
        rm -f "$HOME/.config/fish/completions/einstein.fish" 2>/dev/null || true
        
        # Remove man page
        sudo rm -f "/usr/local/share/man/man1/einstein.1" 2>/dev/null || true
        sudo rm -f "/usr/share/man/man1/einstein.1" 2>/dev/null || true
        rm -f "$HOME/.local/share/man/man1/einstein.1" 2>/dev/null || true
        
        print_success "Uninstallation completed"
        print_warning "You may want to manually remove aliases from your shell config files"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        print_error "Unknown option: $1"
        print_status "Use --help for usage information"
        exit 1
        ;;
esac