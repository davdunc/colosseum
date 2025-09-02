# Colosseum Multi-Agent Investment Committee Framework

## Overview

Colosseum is a multi-agent investment committee framework leveraging Langchain, Fedora Bootable Containers, and a KIND single-node Kubernetes cluster. It supports integration with MCP (Model Context Protocol) servers and clients for secure, programmatic access to data, tools, and AI agent management.

## MCP Client/Server Integration

- **MCP servers** are defined in a configuration file (e.g., `mcp.json`) and instantiated at runtime.
- The official [MCP client](https://modelcontextprotocol.io/quickstart/client) is used to connect to these servers.
- MCP servers provide access to news, tickers, brokers, and custom data sources.
- All agents can access the shared MCP client(s) for efficient compute and parallelism.

## Plugin Architecture

- Plugins can be placed in the `colosseum/plugins/` directory.
- Each plugin can register tools or integrations with the supervisor agent.
- Example: A plugin that fetches and converts a website to markdown for agent consumption.

## Agent Access

- The `SupervisorAgent` class loads MCP servers and plugins, making them available to all agents.
- Agents can directly use the MCP client(s) for secure, efficient access to resources.

## For GitHub Copilot and Amazon Q Users

- The codebase is modular and extensible, following best practices for dependency management and plugin loading.
- MCP client usage follows the official specification and is available to all agents.
- Configuration files are loaded according to XDG and service conventions for compatibility.

## Quickstart

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Configure MCP servers in `~/.config/colosseum/mcp.json` or `/etc/colosseum/mcp.json`.
3. Run the application. Agents will have access to all configured MCP servers and plugins.

## References

- [Model Context Protocol (MCP) Client Quickstart](https://modelcontextprotocol.io/quickstart/client)
- [Langchain Documentation](https://python.langchain.com/)
