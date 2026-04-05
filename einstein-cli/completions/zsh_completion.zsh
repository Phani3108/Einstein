#compdef einstein

# Zsh completion script for Einstein CLI
# Install by copying to a directory in your $fpath

_einstein() {
    local context state state_descr line
    typeset -A opt_args
    
    _arguments -C \
        '(--config)--config[Path to custom configuration file]:config file:_files' \
        '(--api-url)--api-url[Override API server URL]:api url:' \
        '(--json)--json[Output results in JSON format]' \
        '(--verbose -v)'{--verbose,-v}'[Enable verbose output for debugging]' \
        '(--no-interactive)--no-interactive[Disable automatic interactive mode]' \
        '(--help -h)'{--help,-h}'[Show help message]' \
        '1: :_einstein_commands' \
        '*:: :->args' \
        && return 0
    
    case $state in
        args)
            case $words[1] in
                auth)
                    _einstein_auth_commands
                    ;;
                config)
                    _einstein_config_commands
                    ;;
                thoughts)
                    _einstein_thoughts_commands
                    ;;
                search)
                    _einstein_search_commands
                    ;;
                sync)
                    _einstein_sync_commands
                    ;;
                help)
                    _einstein_help_commands
                    ;;
            esac
            ;;
    esac
}

_einstein_commands() {
    local commands
    commands=(
        'auth:Authentication commands'
        'config:Configuration management commands'
        'thoughts:Thought management commands'
        'search:Search thoughts using natural language queries'
        'sync:Cache synchronization commands'
        'help:Help and tutorial commands'
        'interactive:Start interactive mode'
        'version:Show version information'
    )
    _describe 'commands' commands
}

_einstein_auth_commands() {
    local auth_commands
    auth_commands=(
        'login:Login to Einstein server'
        'logout:Logout from Einstein server'
        'status:Show authentication status'
    )
    _describe 'auth commands' auth_commands
}

_einstein_config_commands() {
    local config_commands
    config_commands=(
        'get:Get a configuration value'
        'set:Set a configuration value'
        'show:Show all configuration values'
        'reset:Reset configuration to defaults'
        'path:Show the path to the configuration file'
    )
    
    case $words[2] in
        get|set)
            _einstein_config_keys
            ;;
        *)
            _describe 'config commands' config_commands
            ;;
    esac
}

_einstein_config_keys() {
    local config_keys
    config_keys=(
        'api.url:Einstein server URL'
        'api.timeout:Request timeout in seconds'
        'auth.auto_login:Automatically login when needed'
        'auth.remember_token:Remember authentication tokens'
        'output.colors:Enable colored output'
        'output.pager:Pager for long output'
        'output.max_results:Maximum results to show in lists'
        'cache.enabled:Enable local caching'
        'cache.max_size_mb:Maximum cache size in MB'
        'cache.sync_interval:Cache sync interval in seconds'
        'ui.auto_interactive:Enable automatic interactive mode'
    )
    _describe 'config keys' config_keys
}

_einstein_thoughts_commands() {
    local thoughts_commands
    thoughts_commands=(
        'add:Add a new thought'
        'list:List recent thoughts'
        'show:Show detailed information about a specific thought'
        'delete:Delete a thought by ID'
    )
    _describe 'thoughts commands' thoughts_commands
}

_einstein_search_commands() {
    # Search doesn't have subcommands, just complete with common options
    _arguments \
        '(--limit)--limit[Maximum number of results to return]:limit:' \
        '(--mood)--mood[Filter results by mood]:mood:' \
        '(--tags)--tags[Filter results by tags]:tags:' \
        '(--since)--since[Filter results since date]:since date:' \
        '(--until)--until[Filter results until date]:until date:' \
        '(--min-score)--min-score[Minimum relevance score]:min score:' \
        '(--sort)--sort[Sort results]:sort:(relevance date date-desc)' \
        '*:search query:'
}

_einstein_sync_commands() {
    local sync_commands
    sync_commands=(
        'sync:Synchronize with server'
        'status:Show sync status'
    )
    _describe 'sync commands' sync_commands
}

_einstein_help_commands() {
    local help_commands
    help_commands=(
        'guide:Show detailed help guides for specific topics'
        'tutorial:Start an interactive tutorial for new users'
        'shortcuts:Show keyboard shortcuts and quick commands'
        'workflows:Show common workflows and usage patterns'
    )
    
    case $words[2] in
        guide)
            _einstein_help_topics
            ;;
        *)
            _describe 'help commands' help_commands
            ;;
    esac
}

_einstein_help_topics() {
    local help_topics
    help_topics=(
        'getting-started:First-time setup and basic usage'
        'commands:Complete command reference'
        'interactive:Interactive mode guide'
        'configuration:Configuration management'
        'scripting:Automation and scripting'
        'troubleshooting:Common issues and solutions'
        'examples:Real-world usage examples'
    )
    _describe 'help topics' help_topics
}

# Enable completion for common aliases
compdef _einstein f
compdef _einstein far

_einstein "$@"