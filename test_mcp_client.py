import asyncio
from mcp_client import MCPClient

def print_section(title):
    print("\n" + "=" * 60)
    print(f"{title}")
    print("=" * 60)

def print_tool_result(tool_name, response):
    print(f"\n--- {tool_name} Result ---")
    print(response)
    print("-" * 60)

async def main():
    client = MCPClient()
    try:
        print_section("Connecting to MCP server...")
        await client.connect()
        print(f"\nConnected! Tools: {[tool.name for tool in client.tools]}")

        # Test each tool if available
        tool_names = [tool.name for tool in client.tools]
        if 'get_my_issues' in tool_names:
            print_section("Testing 'get_my_issues'")
            response = await client.process_query("Show my issues")
            print_tool_result('get_my_issues', response)
        if 'search_issues' in tool_names:
            print_section("Testing 'search_issues'")
            response = await client.process_query("Search for issues in project = DVT")
            print_tool_result('search_issues', response)
        if 'get_issue' in tool_names:
            print_section("Testing 'get_issue'")
            response = await client.process_query("Show details for issue DVT-123")
            print_tool_result('get_issue', response)
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 