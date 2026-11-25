# The purpose of this test is to check if all the tools are being loaded and called from the client


import asyncio
import logging

from mcp import Client

from yr_mcp.main import mcp

logger = logging.getLogger(__name__)


async def main():
    async with Client(mcp) as client:
        list_tools = await client.list_tools()
        tools_name = [tool.name for tool in list_tools.tools]
        logger.info(f"Here are all the tools: {tools_name}")

        assert "get_location_forecast" in tools_name, "Forecast tool is missing"

        call_forecast_tool = await client.call_tool(
            "get_location_forecast",
            {"latitude": 59.9139, "longitude": 10.7522, "usage_method": "compact"},
        )
        assert not call_forecast_tool.is_error, call_forecast_tool.content

        logger.info(call_forecast_tool.structured_content)


if __name__ == "__main__":
    asyncio.run(main())
