from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from jira import JIRA
import os
import json
import uuid

# Helper to get Jira client per request/session
def get_jira_client():
    jira_server = os.getenv('JIRA_SERVER', '')
    jira_email = os.getenv('JIRA_EMAIL', '')
    jira_api_token = os.getenv('JIRA_API_TOKEN', '')
    if not jira_server:
        raise ValueError("JIRA_SERVER environment variable is required")
    if not jira_email:
        raise ValueError("JIRA_EMAIL environment variable is required")
    if not jira_api_token:
        raise ValueError("JIRA_API_TOKEN environment variable is required")
    return JIRA(server=jira_server, basic_auth=(jira_email, jira_api_token))

# Remove global credential validation and global jira client initialization

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
    acceptance_criteria: Optional[str] = None

def extract_acceptance_criteria(issue) -> Optional[str]:
    """
    Extract acceptance criteria from customfield_10127.
    """
    try:
        if hasattr(issue.fields, 'customfield_10127'):
            ac_field = issue.fields.customfield_10127
            if ac_field:
                # Handle different field value formats
                if isinstance(ac_field, str):
                    return ac_field.strip()
                elif hasattr(ac_field, 'content'):
                    # Handle structured content
                    if isinstance(ac_field.content, list):
                        return '\n'.join([str(item) for item in ac_field.content if item])
                    else:
                        return str(ac_field.content)
                else:
                    return str(ac_field).strip()
        return None
    except Exception as e:
        print(f"Error extracting acceptance criteria: {str(e)}")
        return None

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
                jira = get_jira_client()
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
                    "acceptance_criteria": extract_acceptance_criteria(issue),
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
                jira = get_jira_client()
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
                    "acceptance_criteria": extract_acceptance_criteria(issue),
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
                jira = get_jira_client()
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
                    "acceptance_criteria": extract_acceptance_criteria(issue),
                    "success": True
                } for issue in issues]
            except Exception as e:
                return [{
                    "error": str(e),
                    "success": False
                }]

        @self.tool("get_acceptance_criteria")
        async def get_acceptance_criteria(issue_key: str) -> Dict[str, Any]:
            """
            Get acceptance criteria for a specific Jira issue from customfield_10127.
            
            Args:
                issue_key: The Jira issue key (e.g., PROJ-123)
                
            Returns:
                Acceptance criteria details if found
            """
            try:
                jira = get_jira_client()
                issue = jira.issue(issue_key)
                ac = extract_acceptance_criteria(issue)
                
                return {
                    "issue_key": issue.key,
                    "summary": issue.fields.summary,
                    "acceptance_criteria": ac,
                    "has_acceptance_criteria": ac is not None,
                    "success": True
                }
            except Exception as e:
                return {
                    "error": str(e),
                    "success": False
                }

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