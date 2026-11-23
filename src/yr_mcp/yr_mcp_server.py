import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from logging import Logger
from typing import Any

import httpx2
from mcp.server import MCPServer
from mcp.server.mcpserver import Context

from yr_mcp.config import BASE_URL, USER_AGENT

logger: Logger = logging.getLogger(__name__)

logging.basicConfig(
    format="%(levelname)s [%(asctime)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.DEBUG,
)


@dataclass
class AppContext:
    http_client: httpx2.AsyncClient


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncGenerator[AppContext]:
    """Make a request to the YR API with proper error handling"""
    headers: dict[str, str] = {"User-Agent": USER_AGENT}

    async with httpx2.AsyncClient(
        base_url=BASE_URL,
        timeout=30,
        limits=httpx2.Limits(max_connections=10, max_keepalive_connections=10),
        headers=headers,
    ) as client:
        yield AppContext(http_client=client)


mcp = MCPServer("Yr weather app", lifespan=lifespan)


async def make_weather_request(
    client: httpx2.AsyncClient, endpoint: str, params: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    try:
        response = await client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    except (httpx2.HTTPError, ValueError):
        return None


@mcp.tool(
    title="Get weather forecast",
    description="Get weather forecast from a specific location giving by the user",
)
async def get_weather(
    longitude: float, latitude: float, ctx: Context[AppContext]
) -> dict[str, Any] | None:
    client = ctx.request_context.lifespan_context.http_client

    logger.info("Fetching weather forecast")
    return await make_weather_request(
        client=client,
        endpoint="/weatherapi/locationforecast/2.0/compact",
        params={"lat": round(latitude, 4), "lon": round(longitude, 4)},
    )


@mcp.prompt(description="Preparing for weather focused travel")
def travel_planner(destination: str):
    return (
        f"Get the forecast weather for {destination}."
        "This information is for planning a trip to {destination}, therefore discuss temperature, wind, percipitation, etc for proper travel."
    )


if __name__ == "__main__":
    mcp.run()
