#!/bin/bash
# Bash completion script for Einstein CLI
# Install by sourcing this file or copying to /etc/bash_completion.d/

_einstein_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    # Global options
    local global_opts="--config --api-url --json --verbose --no-interactive --help"
    
    # Main commands
    local commands="auth config thoughts search sync help interactive version"
    
    # Auth subcommands
    local auth_commands="login logout status"
    
    # Config subcommands
    local config_commands="get set show reset path"
    
    # Thoughts subcommands
    local thoughts_commands="add list show delete"
    
    # Sync subcommands
    local sync_commands="sync status"
    
    # Help subcommands
    local help_commands="guide tutorial shortcuts workflows"
    
    # Help guide topics
    local help_topics="getting-started commands interactive configuration scripting troubleshooting examples"
    
    case "${COMP_CWORD}" in
        1)
            # Complete main commands
            COMPREPLY=($(compgen -W "${commands} ${global_opts}" -- ${cur}))
            ;;
        2)
            # Complete subcommands based on main command
            case "${prev}" in
                auth)
                    COMPREPLY=($(compgen -W "${auth_commands}" -- ${cur}))
                    ;;
                config)
                    COMPREPLY=($(compgen -W "${config_commands}" -- ${cur}))
                    ;;
                thoughts)
                    COMPREPLY=($(compgen -W "${thoughts_commands}" -- ${cur}))
                    ;;
                sync)
                    COMPREPLY=($(compgen -W "${sync_commands}" -- ${cur}))
                    ;;
                help)
                    COMPREPLY=($(compgen -W "${help_commands}" -- ${cur}))
                    ;;
                search)
                    # No subcommands for search, just complete with common search terms
                    COMPREPLY=()
                    ;;
                *)
                    COMPREPLY=($(compgen -W "${global_opts}" -- ${cur}))
                    ;;
            esac
            ;;
        3)
            # Complete third-level commands
            case "${COMP_WORDS[1]}" in
                help)
                    case "${prev}" in
                        guide)
                            COMPREPLY=($(compgen -W "${help_topics}" -- ${cur}))
                            ;;
                    esac
                    ;;
                config)
                    case "${prev}" in
                        get|set)
                            # Complete configuration keys
                            local config_keys="api.url api.timeout auth.auto_login auth.remember_token output.colors output.pager output.max_results cache.enabled cache.max_size_mb cache.sync_interval ui.auto_interactive"
                            COMPREPLY=($(compgen -W "${config_keys}" -- ${cur}))
                            ;;
                    esac
                    ;;
            esac
            ;;
        *)
            # For longer commands, just complete global options
            COMPREPLY=($(compgen -W "${global_opts}" -- ${cur}))
            ;;
    esac
    
    return 0
}

# Register the completion function
complete -F _einstein_completion einstein

# Also provide completion for common aliases
complete -F _einstein_completion f
complete -F _einstein_completion far