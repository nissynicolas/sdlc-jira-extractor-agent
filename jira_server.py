from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from jira import JIRA
import os
from dotenv import load_dotenv
import json
import uuid

load_dotenv()  # Load environment variables

# Initialize Jira client with proper URL formatting
jira_server = os.getenv('JIRA_SERVER', '')
if not jira_server.startswith('http'):
    jira_server = f'https://{jira_server}'

try:
    jira = JIRA(
        server=jira_server,
        basic_auth=(os.getenv('JIRA_EMAIL'), os.getenv('JIRA_API_TOKEN'))
    )
except Exception as e:
    print(f"Failed to connect to Jira: {str(e)}")
    raise

class Issue(BaseModel):
    key: str
    summary: str
    status: str
    assignee: Optional[str] = "Unassigned"
    created: str
    description: Optional[str] = "No description"
    issuetype: Optional[str] = None
    priority: Optional[str] = None
    sprint: Optional[str] = None

class JiraMCP(FastMCP):
    """Custom MCP server for Jira functionality"""
    
    def __init__(self):
        super().__init__("Jira MCP Server")
        
        @self.tool("get_issue")
        async def get_issue(issue_key: str) -> Dict[str, Any]:
            """
            Get details of a specific Jira issue.
            
            Args:
                issue_key: The Jira issue key (e.g., PROJ-123)
                
            Returns:
                Issue details if found
            """
            try:
                issue = jira.issue(issue_key)
                return {
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "status": issue.fields.status.name,
                    "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
                    "created": issue.fields.created,
                    "description": issue.fields.description if issue.fields.description else "No description",
                    "issuetype": issue.fields.issuetype.name,
                    "priority": issue.fields.priority.name if issue.fields.priority else None,
                    "sprint": issue.fields.customfield_10020[0].name if hasattr(issue.fields, 'customfield_10020') and issue.fields.customfield_10020 else None,
                    "success": True
                }
            except Exception as e:
                return {
                    "error": str(e),
                    "success": False
                }
        
        @self.tool("search_issues")
        async def search_issues(jql: str) -> List[Dict[str, Any]]:
            """
            Search for Jira issues using JQL.
            
            Args:
                jql: Jira Query Language string
                
            Returns:
                List of matching issues
            """
            try:
                issues = jira.search_issues(jql, maxResults=50)
                return [{
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "status": issue.fields.status.name,
                    "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
                    "created": issue.fields.created,
                    "description": issue.fields.description if issue.fields.description else "No description",
                    "issuetype": issue.fields.issuetype.name,
                    "priority": issue.fields.priority.name if issue.fields.priority else None,
                    "sprint": issue.fields.customfield_10020[0].name if hasattr(issue.fields, 'customfield_10020') and issue.fields.customfield_10020 else None,
                    "success": True
                } for issue in issues]
            except Exception as e:
                return [{
                    "error": str(e),
                    "success": False
                }]
        
        @self.tool("get_my_issues")
        async def get_my_issues() -> List[Dict[str, Any]]:
            """
            Get issues assigned to the current user.
            
            Returns:
                List of issues assigned to the current user
            """
            try:
                jql = f'assignee = currentUser() ORDER BY created DESC'
                issues = jira.search_issues(jql, maxResults=50)
                return [{
                    "key": issue.key,
                    "summary": issue.fields.summary,
                    "status": issue.fields.status.name,
                    "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
                    "created": issue.fields.created,
                    "description": issue.fields.description if issue.fields.description else "No description",
                    "issuetype": issue.fields.issuetype.name,
                    "priority": issue.fields.priority.name if issue.fields.priority else None,
                    "sprint": issue.fields.customfield_10020[0].name if hasattr(issue.fields, 'customfield_10020') and issue.fields.customfield_10020 else None,
                    "success": True
                } for issue in issues]
            except Exception as e:
                return [{
                    "error": str(e),
                    "success": False
                }]

def create_sse_server(mcp: JiraMCP):
    """Create a Starlette app that handles SSE connections and message handling"""
    transport = SseServerTransport("/messages/")

    # Define handler functions
    async def handle_sse(request):
        async with transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp._mcp_server.run(
                streams[0], streams[1], mcp._mcp_server.create_initialization_options()
            )

    # Create Starlette routes for SSE and message handling
    routes = [
        Route("/sse", endpoint=handle_sse),
        Mount("/messages", app=transport.handle_post_message),
    ]

    # Create a Starlette app
    return Starlette(routes=routes)

def create_mcp_app():
    """Create the FastAPI app with MCP integration"""
    app = FastAPI(title="Jira MCP Server")
    mcp = JiraMCP()
    
    # Mount the SSE server onto the main app
    app.mount("/", create_sse_server(mcp))
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    return app

# Create the FastAPI app
app = create_mcp_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 