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

# Helper to get Jira client per request/session, using email to look up token
def get_jira_client(email: str):
    jira_server = os.getenv('JIRA_SERVER', '')
    if not jira_server:
        raise ValueError("JIRA_SERVER environment variable is required")
    jira_details_json = os.getenv('jira_details', '')
    if not jira_details_json:
        raise ValueError("jira_details environment variable is required")
    try:
        details = json.loads(jira_details_json)
        if isinstance(details, dict):
            details = [details]
    except Exception as e:
        raise ValueError(f"Invalid jira_details JSON: {str(e)}")
    match = next((d for d in details if d.get('jira_email') == email), None)
    if not match:
        raise ValueError(f"No jira_token found for email {email}")
    jira_token = match.get('jira_token')
    if not jira_token:
        raise ValueError(f"No jira_token found for email {email}")
    return JIRA(server=jira_server, basic_auth=(email, jira_token))

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
        async def get_issue(issue_key: str, email: str) -> Dict[str, Any]:
            """
            Get details of a specific Jira issue.
            
            Args:
                issue_key: The Jira issue key (e.g., PROJ-123)
                email: The Jira user email
                
            Returns:
                Issue details if found
            """
            try:
                jira = get_jira_client(email)
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
        async def search_issues(jql: str, email: str) -> List[Dict[str, Any]]:
            """
            Search for Jira issues using JQL.
            
            Args:
                jql: Jira Query Language string
                email: The Jira user email
                
            Returns:
                List of matching issues
            """
            try:
                jira = get_jira_client(email)
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
        async def get_my_issues(email: str) -> List[Dict[str, Any]]:
            """
            Get issues assigned to the current user.
            
            Returns:
                List of issues assigned to the current user
            """
            try:
                jira = get_jira_client(email)
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
        async def get_acceptance_criteria(issue_key: str, email: str) -> Dict[str, Any]:
            """
            Get acceptance criteria for a specific Jira issue from customfield_10127.
            
            Args:
                issue_key: The Jira issue key (e.g., PROJ-123)
                email: The Jira user email
                
            Returns:
                Acceptance criteria details if found
            """
            try:
                jira = get_jira_client(email)
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
        # Parse email from query string
        email = request.query_params.get('email')
        if not email:
            from starlette.responses import JSONResponse
            return JSONResponse({"error": "Missing email in query string"}, status_code=400)

        # Attach email to the MCP instance for use in tool calls (if needed)
        mcp._current_email = email

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