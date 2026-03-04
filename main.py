import asyncio
from datetime import datetime, timedelta
from typing import Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from calendar_client import CalendarClient

# Initialize server and calendar client
app = Server("calendar-mcp")
client = CalendarClient()

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """List all available calendar tools."""
    return [
        types.Tool(
            name="get_calendars",
            description="Get all available calendars",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        types.Tool(
            name="get_events",
            description="Get events between two dates",
            inputSchema={
                "type": "object",
                "properties": {
                    "start": {
                        "type": "string",
                        "description": "Start date in ISO format (e.g. 2026-03-01T00:00:00)"
                    },
                    "end": {
                        "type": "string",
                        "description": "End date in ISO format (e.g. 2026-03-31T23:59:59)"
                    },
                    "calendar_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of calendar IDs to filter by"
                    }
                },
                "required": ["start", "end"]
            }
        ),
        types.Tool(
            name="get_event",
            description="Get a single event by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "The event identifier"
                    }
                },
                "required": ["event_id"]
            }
        ),
        types.Tool(
            name="search_events",
            description="Search for events matching a keyword in their title",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword to search for"
                    },
                    "start": {
                        "type": "string",
                        "description": "Start date in ISO format"
                    },
                    "end": {
                        "type": "string",
                        "description": "End date in ISO format"
                    }
                },
                "required": ["query", "start", "end"]
            }
        ),
        types.Tool(
            name="create_event",
            description="Create a new calendar event",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Event title"
                    },
                    "start": {
                        "type": "string",
                        "description": "Start date in ISO format"
                    },
                    "end": {
                        "type": "string",
                        "description": "End date in ISO format"
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "Optional calendar ID to add the event to"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes for the event"
                    },
                    "alarm_minutes_before": {
                        "type": "integer",
                        "description": "Optional alarm in minutes before the event"
                    }
                },
                "required": ["title", "start", "end"]
            }
        ),
        types.Tool(
            name="update_event",
            description="Update an existing calendar event",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "The event identifier"
                    },
                    "title": {
                        "type": "string",
                        "description": "New title"
                    },
                    "start": {
                        "type": "string",
                        "description": "New start date in ISO format"
                    },
                    "end": {
                        "type": "string",
                        "description": "New end date in ISO format"
                    },
                    "notes": {
                        "type": "string",
                        "description": "New notes"
                    },
                    "calendar_id": {
                        "type": "string",
                        "description": "New calendar ID"
                    }
                },
                "required": ["event_id"]
            }
        ),
        types.Tool(
            name="delete_event",
            description="Delete a calendar event by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "The event identifier"
                    }
                },
                "required": ["event_id"]
            }
        ),
        types.Tool(
            name="add_alarm",
            description="Add an alarm to an existing event",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "The event identifier"
                    },
                    "minutes_before": {
                        "type": "integer",
                        "description": "Minutes before the event to trigger the alarm"
                    }
                },
                "required": ["event_id", "minutes_before"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls."""
    try:
        if name == "get_calendars":
            result = client.get_calendars()

        elif name == "get_events":
            start = datetime.fromisoformat(arguments["start"])
            end = datetime.fromisoformat(arguments["end"])
            calendar_ids = arguments.get("calendar_ids")
            result = client.get_events(start, end, calendar_ids)

        elif name == "get_event":
            result = client.get_event(arguments["event_id"])

        elif name == "search_events":
            start = datetime.fromisoformat(arguments["start"])
            end = datetime.fromisoformat(arguments["end"])
            result = client.search_events(arguments["query"], start, end)

        elif name == "create_event":
            start = datetime.fromisoformat(arguments["start"])
            end = datetime.fromisoformat(arguments["end"])
            result = client.create_event(
                title=arguments["title"],
                start=start,
                end=end,
                calendar_id=arguments.get("calendar_id"),
                notes=arguments.get("notes"),
                alarm_minutes_before=arguments.get("alarm_minutes_before")
            )

        elif name == "update_event":
            start = datetime.fromisoformat(arguments["start"]) if "start" in arguments else None
            end = datetime.fromisoformat(arguments["end"]) if "end" in arguments else None
            result = client.update_event(
                event_id=arguments["event_id"],
                title=arguments.get("title"),
                start=start,
                end=end,
                notes=arguments.get("notes"),
                calendar_id=arguments.get("calendar_id")
            )

        elif name == "delete_event":
            result = client.delete_event(arguments["event_id"])

        elif name == "add_alarm":
            result = client.add_alarm(
                event_id=arguments["event_id"],
                minutes_before=arguments["minutes_before"]
            )

        else:
            raise ValueError(f"Unknown tool: {name}")

        return [types.TextContent(type="text", text=str(result))]

    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Start the MCP server."""
    await client.request_access()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())