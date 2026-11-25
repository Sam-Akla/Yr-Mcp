import asyncio

from mcp import Client, StdioServerParameters


async def check_startup() -> None:
    server = StdioServerParameters(command="uv", args=["run", "yr-mcp"])
    async with Client(server) as client:
        result = await client.list_tools()
        names = {tool.name for tool in result.tools}
        assert names == {
            "get_location_forecast",
            "get_met_alerts",
            "get_now_cast",
            "get_sun_moon_events",
        }, f"Unexpected tools: {sorted(names)}"
        print(*sorted(names), sep="\n")


if __name__ == "__main__":
    asyncio.run(check_startup())
