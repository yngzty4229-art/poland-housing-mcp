"""MCP server: Polish housing prices from official notarial deeds and developers' price lists.

Every tool runs a ready-made Apify Actor (pay per event) on the Apify account of the user,
authorised with the APIFY_TOKEN environment variable. The data come from Poland's official
Real Estate Price Register (Rejestr Cen Nieruchomości, RCN – notarial deeds, published by GUGiK)
and from the price lists Polish developers must publish daily on dane.gov.pl.
"""
from __future__ import annotations

import json
import os
from typing import Any, Literal

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

OWNER = "kris_fili"
APIFY_RUN = "https://api.apify.com/v2/acts/{owner}~{actor}/run-sync-get-dataset-items"
READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True, idempotentHint=True)

server = MCPServer(
    name="poland-housing",
    title="Poland housing prices (notarial deeds)",
    instructions=(
        "Polish housing market data from official sources. Use value_apartment to estimate what a specific "
        "apartment is worth, transaction_prices for what buyers actually paid around an address, new_build_prices "
        "for developers' current asking prices, and asking_vs_deed_gap to compare the two. Locations must be in "
        "Poland: use Polish characters (e.g. 'Kraków, Długa 12', 'Wrocław', 'Gdańsk, Grunwaldzka 100') or coordinates "
        "'50.06, 19.94'. Prices are in PLN. Each call runs a paid Apify Actor on the user's account."),
    website_url="https://apify.com/kris_fili",
    version="0.1.0",
)


async def _run_actor(actor: str, payload: dict[str, Any]) -> list[dict[str, Any]] | str:
    token = os.environ.get("APIFY_TOKEN", "").strip()
    if not token:
        return ("APIFY_TOKEN is not set. Create a free Apify account at https://apify.com, copy the API token "
                "from Console → Settings → API & Integrations and add it to this server's environment.")
    url = APIFY_RUN.format(owner=OWNER, actor=actor)
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(330, connect=30)) as client:
            response = await client.post(url, params={"timeout": 300}, json=payload,
                                         headers={"Authorization": f"Bearer {token}",
                                                  "User-Agent": "poland-housing-mcp/0.1.0"})
    except httpx.HTTPError as error:
        return f"Could not reach Apify: {error}"
    if response.status_code == 401:
        return "Apify rejected the token – check APIFY_TOKEN."
    if response.status_code not in (200, 201):
        return f"The Actor run failed (HTTP {response.status_code}): {response.text[:500]}"
    try:
        items = response.json()
    except ValueError:
        return "Apify returned an unreadable response."
    return items if isinstance(items, list) else [items]


def _as_text(result: list[dict[str, Any]] | str) -> str:
    if isinstance(result, str):
        return result
    if not result:
        return "No results for this location. Check the address (use Polish characters) or widen the area."
    return json.dumps(result, ensure_ascii=False)


@server.tool(annotations=READ_ONLY)
async def value_apartment(location: str, area_m2: float, rooms: int | None = None, floor: int | None = None,
                          market: Literal["secondary", "primary", "any"] = "secondary", months_back: int = 24,
                          include_comparables: bool = True) -> str:
    """Estimate the market value of an apartment in Poland from comparable sales in official notarial deeds (AVM).

    Returns the estimated value and price per m² in PLN, a value range, a confidence level, the most similar
    sales nearby (when include_comparables) and the local market context.
    Cost: about 0.49 USD per successful valuation (charged to the user's Apify account; nothing when no estimate).

    Args:
        location: Street and building number in Poland with Polish characters (e.g. "Kraków, Długa 12") or "lat, lon".
        area_m2: Usable floor area in square metres (10–400).
        rooms: Number of rooms as in listings, kitchen not counted (optional).
        floor: Floor, 0 = ground floor (optional).
        market: "secondary" (resale, default), "primary" (new from a developer) or "any".
        months_back: How many months of sales to use, 12–60 (default 24).
        include_comparables: Include the 10 most similar sales used for the estimate.
    """
    payload: dict[str, Any] = {"location": location, "areaM2": area_m2, "market": market,
                               "monthsBack": max(12, min(60, months_back)),
                               "includeComparables": include_comparables, "includeNewBuildAskingPrices": False}
    if rooms is not None:
        payload["rooms"] = rooms
    if floor is not None:
        payload["floor"] = floor
    return _as_text(await _run_actor("poland-apartment-valuation", payload))


@server.tool(annotations=READ_ONLY)
async def transaction_prices(location: str, radius_m: int = 1000, whole_city: bool = False, months_back: int = 24,
                             property_type: Literal["apartment", "house", "land", "commercial_unit", "garage"] = "apartment",
                             market: Literal["any", "primary", "secondary"] = "any", max_transactions: int = 20) -> str:
    """What buyers actually paid around an address in Poland – statistics from official notarial deeds (RCN).

    Returns a summary (median price per m² in PLN, quartiles, quarterly trend, primary vs secondary market,
    year-on-year change, newest deed) and up to max_transactions individual sales.
    Cost: about 0.25 USD per report plus 0.003 USD per returned transaction (user's Apify account).

    Args:
        location: Address, district or city in Poland with Polish characters (e.g. "Warszawa, Puławska 100"), or "lat, lon".
        radius_m: Search radius in metres, 100–5000 (ignored when whole_city is true).
        whole_city: Use the whole city or municipality instead of a radius.
        months_back: How many months back, 1–240 (default 24).
        property_type: apartment (default), house, land, commercial_unit or garage.
        market: any (default), primary (new from developers) or secondary (resale).
        max_transactions: How many individual transactions to return, 0–200 (default 20).
    """
    payload = {"location": location, "searchArea": "whole_city" if whole_city else "radius",
               "radiusMeters": max(100, min(5000, radius_m)), "monthsBack": max(1, min(240, months_back)),
               "propertyType": property_type, "market": market,
               "includeTransactions": max_transactions > 0, "maxTransactions": max(0, min(200, max_transactions))}
    return _as_text(await _run_actor("poland-real-estate-transaction-prices", payload))


@server.tool(annotations=READ_ONLY)
async def new_build_prices(location: str, radius_m: int = 2000, whole_city: bool = False, min_rooms: int | None = None,
                           max_rooms: int | None = None, max_offers: int = 20) -> str:
    """Developers' current asking prices for new apartments in Poland, from their mandatory daily price lists.

    Returns a summary (median asking price per m² in PLN, number of offers and investments, size buckets)
    and up to max_offers individual offers with developer, investment, price, area and rooms.
    Cost: about 0.20 USD per report plus 0.002 USD per returned offer (user's Apify account).

    Args:
        location: Address, district or city in Poland with Polish characters (e.g. "Gdańsk"), or "lat, lon".
        radius_m: Search radius in metres, 100–20000 (ignored when whole_city is true).
        whole_city: Use the whole city instead of a radius.
        min_rooms: Minimum number of rooms (optional).
        max_rooms: Maximum number of rooms (optional).
        max_offers: How many individual offers to return, 0–200 (default 20).
    """
    payload: dict[str, Any] = {"location": location, "searchArea": "whole_city" if whole_city else "radius",
                               "radiusMeters": max(100, min(20000, radius_m)), "propertyType": "apartment",
                               "onlyAvailable": True, "includeOffers": max_offers > 0,
                               "maxOffers": max(0, min(200, max_offers))}
    if min_rooms:
        payload["minRooms"] = min_rooms
    if max_rooms:
        payload["maxRooms"] = max_rooms
    return _as_text(await _run_actor("poland-new-build-apartment-prices", payload))


@server.tool(annotations=READ_ONLY)
async def asking_vs_deed_gap(location: str, radius_m: int = 1500, whole_city: bool = False, months_back: int = 12) -> str:
    """How far Polish developers' asking prices are above (or below) prices actually paid in notarial deeds.

    Compares today's developer price lists with primary- and secondary-market deeds around a location:
    medians per m² in PLN, the gap in percent and the same by apartment size.
    Cost: about 0.49 USD per report (user's Apify account; nothing when one side has no data).

    Args:
        location: Address, district or city in Poland with Polish characters (e.g. "Wrocław, Świdnicka 10"), or "lat, lon".
        radius_m: Search radius in metres, 200–5000 (ignored when whole_city is true).
        whole_city: Use the whole city instead of a radius.
        months_back: How many months of deeds to use, 3–60 (default 12).
    """
    payload = {"location": location, "searchArea": "whole_city" if whole_city else "radius",
               "radiusMeters": max(200, min(5000, radius_m)), "monthsBack": max(3, min(60, months_back))}
    return _as_text(await _run_actor("poland-housing-price-gap", payload))


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
