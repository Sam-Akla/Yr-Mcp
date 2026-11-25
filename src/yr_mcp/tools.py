import datetime
import logging
from typing import Any, Literal

import httpx2
from mcp.server.mcpserver import Context

from yr_mcp.context import AppContext

logger = logging.getLogger(__name__)


async def make_weather_request(
    client: httpx2.AsyncClient, endpoint: str, params: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    try:
        response = await client.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()

    except (httpx2.HTTPError, ValueError):
        return None


async def get_location_forecast(
    ctx: Context[AppContext],
    longitude: float,
    latitude: float,
    altitude: int | None = None,
    usage_method: Literal["compact", "complete"] = "complete",
) -> dict[str, Any] | None:

    client = ctx.request_context.lifespan_context.http_client

    params = {
        "lat": round(latitude, 4),
        "lon": round(longitude, 4),
    }

    if altitude != None:
        params["altitude"] = altitude

    logger.info("Fetching weather forecast")
    return await make_weather_request(
        client=client,
        endpoint=f"/locationforecast/2.0/{usage_method}",
        params=params,
    )


async def get_now_cast(
    ctx: Context[AppContext],
    longitude: float,
    latitude: float,
    altitude: int | None = None,
    usage_method: Literal["classic", "complete"] = "complete",
) -> dict[str, Any] | None:

    client = ctx.request_context.lifespan_context.http_client

    logger.info("Fetching weather forecast")
    return await make_weather_request(
        client=client,
        endpoint=f"/nowcast/2.0/{usage_method}",
        params={
            "lat": round(latitude, 4),
            "lon": round(longitude, 4),
            "altitude": altitude,
        },
    )


async def get_sun_moon_events(
    ctx: Context[AppContext],
    longitude: float,
    latitude: float,
    date: datetime.date,
    offset: str | None = None,
    usage_method: Literal["sun", "moon"] = "sun",
) -> dict[str, Any] | None:

    client = ctx.request_context.lifespan_context.http_client

    logger.info("Fetching weather forecast")
    return await make_weather_request(
        client=client,
        endpoint=f"/sunrise/3.0/{usage_method}",
        params={
            "lat": round(latitude, 4),
            "lon": round(longitude, 4),
            "date": date.isoformat(),
            "offset": offset,
        },
    )


async def get_met_alerts(
    ctx: Context[AppContext],
    longitude: float,
    latitude: float,
    sort: Literal["area", "event", "incidentName", "t_onset", "t_published", "type"],
    lang: Literal["no", "en"] = "en",
    geographicDomain: Literal["land", "marine"] = "land",
    usage_method: Literal["current", "all", "archive"] = "current",
    county: Literal[3, 11, 15, 18, 31, 32, 33, 34, 39, 40, 42, 46, 50, 55, 56]
    | None = None,
    event: Literal[
        "blowingSnow",
        "forestFire",
        "gale",
        "ice",
        "icing",
        "lightning",
        "polarLow",
        "rain",
        "rainFlood",
        "snow",
        "stormSurge",
        "wind",
    ]
    | None = None,
    incidentName: str | None = None,
    period: datetime.date | None = None,
    date: datetime.date | None = None,
) -> dict[str, Any] | None:
    client = ctx.request_context.lifespan_context.http_client

    params = {
        "lat": round(latitude, 4),
        "lon": round(longitude, 4),
        "lang": lang,
        "geographicDomain": geographicDomain,
    }

    if geographicDomain == "land" and county != None:
        params["county"] = f"{county:02d}"

    if event != None:
        params["event"] = event

    if incidentName != None:
        params["incidentName"] = incidentName

    if sort != None:
        params["sort"] = sort

    if usage_method == "archive":
        if date != None:
            params["date"] = date.isoformat()
        elif period != None:
            params["period"] = period.strftime("%Y-%m")
        else:
            logger.error("Specify date or period to use with /archive")
            raise ValueError("Specify date or period for archive alerts.")

    logger.info("Fetching alerts")

    return await make_weather_request(
        client=client, endpoint=f"/metalerts/2.0/{usage_method}.json", params=params
    )
