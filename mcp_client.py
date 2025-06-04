import asyncio
import sys
from typing import Optional
from contextlib import AsyncExitStack
from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client

load_dotenv()  # Load environment variables from .env

class MCPClient:
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()

    async def connect(self):
        # Connect to the MCP server using SSE transport
        self.sse_ctx = sse_client(f"{self.server_url}/sse")
        self.sse = await self.exit_stack.enter_async_context(self.sse_ctx)
        self.session = await self.exit_stack.enter_async_context(ClientSession(*self.sse))
        await self.session.initialize()
        # List available tools
        response = await self.session.list_tools()
        self.tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in self.tools])

    async def process_query(self, query: str) -> str:
        messages = [
            {"role": "user", "content": query}
        ]
        # Prepare tool schemas for Claude
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            } for tool in self.tools
        ]
        # Initial Claude API call
        response = self.anthropic.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            messages=messages,
            tools=available_tools
        )
        final_text = []
        assistant_message_content = []
        for content in response.content:
            if content.type == 'text':
                final_text.append(content.text)
                assistant_message_content.append(content)
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input
                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                assistant_message_content.append(content)
                messages.append({
                    "role": "assistant",
                    "content": assistant_message_content
                })
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": result.content if hasattr(result, 'content') else str(result)
                        }
                    ]
                })
                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools
                )
                final_text.append(response.content[0].text)
        return "\n".join(final_text)

    async def chat_loop(self):
        print("\nMCP Client Chatbot Started!")
        print("Type your queries or 'quit' to exit.")
        while True:
            try:
                query = input("\nYou: ").strip()
                if query.lower() in ('quit', 'exit'):
                    print("\nGoodbye!")
                    break
                response = await self.process_query(query)
                print("\nAssistant:\n" + response)
            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        await self.exit_stack.aclose()

async def main():
    import argparse
    parser = argparse.ArgumentParser(description='MCP Client Chatbot')
    parser.add_argument('--server', default='http://localhost:8000', help='MCP server URL')
    args = parser.parse_args()
    client = MCPClient(server_url=args.server)
    try:
        await client.connect()
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
