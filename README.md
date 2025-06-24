# MCP Jira Integration

This project demonstrates how to use the Model Context Protocol (MCP) to interact with Jira using a simple client-server architecture.

## Setup

1. Create a virtual environment and activate it:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

## Configuration

The Jira MCP server is now configurable through environment variables that can be set in your MCP server configuration. You have two options:

### Option 1: Configure in MCP Server (Recommended)

Update your MCP server configuration (e.g., in Cursor's `mcp.json` or your MCP client config) to include the Jira credentials:

```json
{
  "mcpServers": {
    "jiraServer": {
      "command": "python",
      "args": ["jira_server.py"],
      "env": {
        "JIRA_SERVER": "your-domain.atlassian.net",
        "JIRA_EMAIL": "your-email@example.com",
        "JIRA_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

### Option 2: Use .env file (Fallback)

Create a `.env` file in the project root with your Jira credentials:
```
JIRA_SERVER=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-api-token
```

### Getting Your Jira API Token

To get your Jira API token:
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a name and copy the token value

## Running the Jira Server

Start the Jira MCP server:
```bash
python jira_server.py
```

The server will start and listen for MCP requests on the default port.

## Available Actions

The Jira MCP server supports the following actions:

1. `get_issue`: Get details of a specific Jira issue
   - Parameters: `issue_key` (e.g., "PROJ-123")

2. `search_issues`: Search for issues using JQL
   - Parameters: `jql` (Jira Query Language string)

3. `get_my_issues`: Get issues assigned to the current user
   - No parameters required

## Example Usage

You can use the MCP client to interact with the Jira server. Here's an example:

```python
from mcp import MCPClient

async def main():
    client = MCPClient()
    
    # Get a specific issue
    response = await client.send_request(
        action="get_issue",
        parameters={"issue_key": "PROJ-123"}
    )
    
    # Search for issues
    response = await client.send_request(
        action="search_issues",
        parameters={"jql": "project = PROJ AND status = 'In Progress'"}
    )
    
    # Get my issues
    response = await client.send_request(
        action="get_my_issues"
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Security Note

Never commit your `.env` file or share your Jira API token. The token provides access to your Jira account and should be kept secure. 