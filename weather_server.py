import asyncio
import random
from datetime import datetime
from mcp.types import Tool, TextContent
from mcp.server.lowlevel.server import Server
from mcp.server.stdio import stdio_server

# Define the tool schema
weather_tool = Tool(
    name="get_weather",
    description="Get the current weather for a location",
    inputSchema={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city name to get weather for"
            }
        },
        "required": ["location"]
    }
)

# Create the server
server = Server("WeatherServer", version="1.0.0")

# Register the list_tools handler
@server.list_tools()
async def handle_list_tools():
    return [weather_tool]

# Register the call_tool handler
@server.call_tool()
async def handle_call_tool(name, arguments):
    if name == "get_weather":
        location = arguments.get("location", "Unknown")
        temperature = random.randint(0, 35)
        conditions = random.choice(["Sunny", "Cloudy", "Rainy", "Snowy", "Partly Cloudy"])
        humidity = random.randint(30, 90)
        weather_data = (
            f"Weather for {location}:\n"
            f"Temperature: {temperature}°C\n"
            f"Conditions: {conditions}\n"
            f"Humidity: {humidity}%\n"
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return [TextContent(type="text", text=weather_data)]
    return [TextContent(type="text", text="Unknown tool")] 

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )

if __name__ == "__main__":
    asyncio.run(main()) 