# Configuration Examples

This directory contains example configuration files for the Colosseum framework.

## Files

### mcp.json
Example MCP (Model Context Protocol) server configuration. This file defines the various MCP servers that agents can connect to for data and tools.

**Location options:**
- `~/.config/colosseum/mcp.json` (recommended for user-specific config)
- `/etc/colosseum/mcp.json` (for system-wide config)

**Usage:**
```bash
# Copy to your config directory
mkdir -p ~/.config/colosseum
cp examples/mcp.json ~/.config/colosseum/mcp.json
# Edit with your actual credentials
nano ~/.config/colosseum/mcp.json
```

### config.yaml
Main application configuration file for Colosseum settings, agent parameters, and plugin configuration.

**Location options:**
- `~/.config/colosseum/config.yaml` (XDG standard, user-specific)
- `/etc/colosseum/config.yaml` (system-wide, requires root)
- `/var/lib/colosseum/config.yaml` (service-specific)

**Usage:**
```bash
# Copy to your config directory
mkdir -p ~/.config/colosseum
cp examples/config.yaml ~/.config/colosseum/config.yaml
# Edit as needed
nano ~/.config/colosseum/config.yaml
```

## Environment Variables

You can also configure Colosseum using environment variables:

- `OPENAI_API_KEY` - Your OpenAI API key
- `MCP_CONFIG_PATH` - Override the default MCP config location
- `XDG_CONFIG_HOME` - Override the default XDG config directory

## Security Notes

- **Never commit actual credentials** to version control
- Store sensitive information (API keys, passwords) in environment variables when possible
- Use file permissions to protect configuration files: `chmod 600 ~/.config/colosseum/*.json`
- Consider using secret management tools (Vault, AWS Secrets Manager) for production deployments
