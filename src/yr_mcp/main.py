import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx2
from mcp.server import MCPServer

from yr_mcp.config import BASE_WEATHER_URL, USER_AGENT
from yr_mcp.context import AppContext
from yr_mcp.prompts import travel_planner
from yr_mcp.tools import (
    get_location_forecast,
    get_met_alerts,
    get_now_cast,
    get_sun_moon_events,
)

logging.basicConfig(
    format="%(levelname)s [%(asctime)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncGenerator[AppContext]:
    """Open and close the shared weather API client."""
    headers: dict[str, str] = {"User-Agent": USER_AGENT}

    async with httpx2.AsyncClient(
        base_url=BASE_WEATHER_URL,
        timeout=30,
        limits=httpx2.Limits(max_connections=10, max_keepalive_connections=10),
        headers=headers,
    ) as client:
        yield AppContext(http_client=client)


mcp = MCPServer("Yr weather app", lifespan=lifespan)

mcp.add_tool(
    get_location_forecast,
    title="Weather forecasts for any location on earth",
    description="This service delivers weather forecasts for any given coordinate for the next nine days",
)
mcp.add_tool(
    get_now_cast,
    title="Immediate weather forecast for specified locations in the Nordic area",
    description="""
        This service delivers two-hour weather forecasts in GeoJSON or XML for locations in Norway, Sweden, Finland and Denmark. 
        Forecasts are updated every 5 minutes. 
        It is our best estimate of the current weather conditions, and is especially useful for predicting immediate precipitation.
    """,
)
mcp.add_tool(
    get_sun_moon_events,
    title="Calculate sun or moon events, as seen from a specific location on Earth",
    description="""
    Returns a GeoJSON document indicating time and direction to when the sun (or moon) is on its highest point on a given date (defaults to today) as seen from a specified point on Earth, as well as the preceding sun/moonrise and following sun/moonset (which may not be on the same date).
    The lowest point in the cycle is also returned. 
    Note that any or all of these may be null.
    """,
)
mcp.add_tool(
    get_met_alerts,
    title="Weather alerts from the Norwegian Meteorological Institute",
    description="""
    This service provides meteorological warnings for land, coastal and sea regions for the next days. 
    Each alert message (identified by its CAP id) is only issued once, and is valid until the expires time or updated by another alert message.
    """,
)


def main() -> None:
    print("Hello from yr-mcp!")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

mcp.prompt(description="Preparing for weather focused travel")(travel_planner)
