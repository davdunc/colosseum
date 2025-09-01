# Project Context

This project implements a multi-agent investment committee framework using Langchain, Fedora Bootable Containers, and KIND Kubernetes. It features:

- **MCP Client/Server Integration:**  
  Uses the official MCP client to connect to MCP servers defined in a config file. All agents share access to these clients for efficiency.

- **Plugin System:**  
  Plugins in `colosseum/plugins/` can register new tools or integrations with the supervisor agent.

- **Agent Architecture:**  
  The supervisor agent loads MCP servers and plugins, making them available to all agents for secure, efficient access to data and tools.

- **Configuration:**  
  Follows XDG and service file system conventions for config and state files.

This context is provided for GitHub Copilot and Amazon Q to assist with code completion and reasoning about the project structure.
