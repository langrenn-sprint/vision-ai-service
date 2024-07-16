"""Module for events adapter."""

from datetime import datetime
import logging
import os
from typing import List
from zoneinfo import ZoneInfo

from aiohttp import ClientSession
from aiohttp import hdrs
from dotenv import load_dotenv
from multidict import MultiDict

# get base settings
load_dotenv()
EVENTS_HOST_SERVER = os.getenv("EVENTS_HOST_SERVER", "localhost")
EVENTS_HOST_PORT = os.getenv("EVENTS_HOST_PORT", "8082")
EVENT_SERVICE_URL = f"http://{EVENTS_HOST_SERVER}:{EVENTS_HOST_PORT}"


class EventsAdapter:
    """Class representing events."""

    async def get_all_events(self, token: str) -> List:
        """Get all events function."""
        events = []
        headers = MultiDict(
            [
                (hdrs.CONTENT_TYPE, "application/json"),
                (hdrs.AUTHORIZATION, f"Bearer {token}"),
            ]
        )

        async with ClientSession() as session:
            async with session.get(
                f"{EVENT_SERVICE_URL}/events", headers=headers
            ) as resp:
                logging.debug(f"get_all_events - got response {resp.status}")
                if resp.status == 200:
                    events = await resp.json()
                    logging.debug(f"events - got response {events}")
                elif resp.status == 401:
                    raise Exception(f"Login expired: {resp}")
                else:
                    logging.error(f"Error {resp.status} getting events: {resp} ")
        return events

    def get_local_datetime_now(self, event: dict) -> datetime:
        """Return local datetime object, time zone adjusted from event info."""
        timezone = event["timezone"]
        if timezone:
            local_time_obj = datetime.now(ZoneInfo(timezone))
        else:
            local_time_obj = datetime.now()
        return local_time_obj

    def get_local_time(self, event: dict, format: str) -> str:
        """Return local time string, time zone adjusted from event info."""
        local_time = ""
        timezone = event["timezone"]
        if timezone:
            t_n = datetime.now(ZoneInfo(timezone))
        else:
            t_n = datetime.now()

        if format == "HH:MM":
            local_time = f"{t_n.strftime('%H')}:{t_n.strftime('%M')}"
        elif format == "log":
            local_day = (
                f"{t_n.strftime('%Y')}-{t_n.strftime('%m')}-{t_n.strftime('%d')}"
            )
            local_time = f"{local_day}T{t_n.strftime('%X')}"
        else:
            local_time = t_n.strftime("%X")
        return local_time
