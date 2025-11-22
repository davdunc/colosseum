# Colosseum Agent Examples

This directory contains example agents demonstrating various features of the Colosseum framework.

## Examples

### 1. Simple Agent (`simple_agent.py`)

Demonstrates basic agent functionality with database persistence:
- Creating an agent with tools
- Running queries with conversation history
- Saving and loading agent state
- Resuming previous sessions

**Run:**
```bash
python examples/agents/simple_agent.py
```

**Features shown:**
- Tool registration (calculator, portfolio checker)
- Automatic conversation persistence
- State management
- Session resumption

### 2. Multi-Agent Workflow (`multi_agent.py`)

Shows multiple agents working together through shared database state:
- Specialized agents (researcher, analyst, decision-maker)
- Agent coordination via shared state
- Multi-step workflows
- Persistent audit trail

**Run:**
```bash
python examples/agents/multi_agent.py
```

**Features shown:**
- Multiple agent coordination
- Shared state management
- Workflow orchestration
- Complete investment analysis pipeline

## Database Requirements

Before running examples, ensure the database is initialized:

```bash
# Initialize database (uses SQLite by default in development)
python -m colosseum.cli init-db

# Or deploy with PostgreSQL using Quadlets
python -m colosseum.quadlet_deploy deploy
```

## Viewing Results

After running examples, you can inspect the database:

```bash
# Show all sessions
python -m colosseum.cli list-sessions

# Show conversation for a specific session
python -m colosseum.cli show-conversation demo-session-001

# Show agent state
python -m colosseum.cli show-state demo-session-001

# Database statistics
python -m colosseum.cli stats
```

## Interactive Mode

Start an interactive agent session:

```bash
# Start interactive session
python -m colosseum.cli interactive

# With custom agent name and model
python -m colosseum.cli interactive --agent-name my-agent --model gpt-4

# Resume a previous session
python -m colosseum.cli interactive --session-id demo-session-001
```

## Environment Variables

Set your OpenAI API key:

```bash
export OPENAI_API_KEY="sk-your-key-here"
```

For PostgreSQL (production):

```bash
export DATABASE_URL="postgresql://colosseum:password@localhost:5432/colosseum"
```

## Adding Your Own Tools

Create custom tools for your agents:

```python
from langchain_core.tools import tool
from colosseum import SupervisorAgent

@tool
def my_custom_tool(input: str) -> str:
    """Description of what the tool does."""
    # Your tool logic here
    return f"Processed: {input}"

# Create agent with your tool
agent = SupervisorAgent(
    tools=[my_custom_tool],
    agent_name="my-agent",
    session_id="my-session"
)

# Use the agent
result = agent.run("Please use my custom tool")
```

## MCP Server Integration

If you have MCP servers configured:

```bash
# Copy example config
mkdir -p ~/.config/colosseum
cp ../mcp.json ~/.config/colosseum/mcp.json

# Edit with your credentials
nano ~/.config/colosseum/mcp.json
```

The agent will automatically load and make MCP servers available:

```python
agent = SupervisorAgent(...)
# Access MCP servers
print(f"Available MCP servers: {list(agent.mcp_servers.keys())}")
```

## Next Steps

- Explore the source code to understand the implementation
- Modify the examples to test different scenarios
- Create your own specialized agents
- Build multi-agent workflows for your use case
- Integrate with your own data sources via MCP servers

## Troubleshooting

**Database connection errors:**
```bash
# Check database status (if using Quadlets)
systemctl --user status colosseum-db.service

# View database logs
journalctl --user -u colosseum-db.service -f

# Test database connection
podman exec -it colosseum-db psql -U colosseum -d colosseum
```

**Import errors:**
```bash
# Ensure package is installed
pip install -e .

# Check installation
python -c "import colosseum; print(colosseum.__version__)"
```

**OpenAI API errors:**
- Verify your API key is set: `echo $OPENAI_API_KEY`
- Check your OpenAI account has credits
- Try with a different model (e.g., `gpt-3.5-turbo`)
