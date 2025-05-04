"""Module for application looking at video and detecting line crossings."""

import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

from vision_ai_service.adapters import (
    ConfigAdapter,
    EventsAdapter,
    StatusAdapter,
    UserAdapter,
)
from vision_ai_service.services import VideoAIService
from vision_ai_service.services.simulate_service import SimulateService

# get base settings
load_dotenv()
CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}
photos_file_path = f"{Path.cwd()}/vision_ai_service/files"
event = {"id": ""}
status_type = ""

# set up logging
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
logging.basicConfig(
    level=LOGGING_LEVEL,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Separate logging for errors
file_handler = RotatingFileHandler("error.log", maxBytes=1024 * 1024, backupCount=5)
file_handler.setLevel(logging.ERROR)
# Create a formatter with the desired format
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logging.getLogger().addHandler(file_handler)


async def main() -> None:
    """CLI for analysing video stream."""
    token = ""
    event = {}
    status_type = ""
    try:
        # login to data-source
        token = await do_login()
        event = await get_event(token)
        information = (
            f"vision-ai-service is ready! - {event['name']}, {event['date_of_event']}"
        )
        status_type = await ConfigAdapter().get_config(
            token, event["id"], "VIDEO_ANALYTICS_STATUS_TYPE"
        )
        await StatusAdapter().create_status(
            token, event, status_type, information
        )

        # service ready!
        await ConfigAdapter().update_config(
            token, event["id"], "VIDEO_ANALYTICS_AVAILABLE", "True"
        )
        while True:
            ai_config = await get_config(token, event["id"])
            try:
                # run simulation
                if ai_config["start_simulation"]:
                    await SimulateService().simulate_crossings(
                        token, event, status_type, photos_file_path
                    )
                if ai_config["stop_tracking"]:
                    await ConfigAdapter().update_config(
                        token, event["id"], "VIDEO_ANALYTICS_STOP", "False"
                    )
                elif ai_config["analytics_start"]:
                    await VideoAIService().detect_crossings_with_ultraltyics(
                        token, event, status_type, photos_file_path
                    )
                elif ai_config["draw_trigger_line"]:
                    await ConfigAdapter().update_config(
                        token, event["id"], "DRAW_TRIGGER_LINE", "False"
                    )
                    await VideoAIService().print_image_with_trigger_line_v2(
                        token, event, status_type, photos_file_path
                    )
                elif ai_config["analytics_running"]:
                    # should be invalid (no muliti thread) - reset
                    await ConfigAdapter().update_config(
                        token, event["id"], "VIDEO_ANALYTICS_RUNNING", "False"
                    )
            except Exception as e:
                err_string = str(e)
                logging.exception(err_string)
                await StatusAdapter().create_status(
                    token,
                    event,
                    status_type,
                    f"Error in Vision AI: {err_string}",
                )
                await ConfigAdapter().update_config(
                    token, event["id"], "VIDEO_ANALYTICS_RUNNING", "False"
                )
                await ConfigAdapter().update_config(
                    token, event["id"], "VIDEO_ANALYTICS_START", "False"
                )
            logging.info("Vision AI er klar til å starte analyse.")
            await asyncio.sleep(15)
    except Exception as e:
        err_string = str(e)
        logging.exception(err_string)
        await StatusAdapter().create_status(
            token, event, status_type, f"Critical Error - exiting program: {err_string}"
        )
    await ConfigAdapter().update_config(
        token, event["id"], "VIDEO_ANALYTICS_AVAILABLE", "False"
    )
    logging.info("Goodbye!")


async def do_login() -> str:
    """Login to data-source."""
    uid = os.getenv("ADMIN_USERNAME", "a")
    pw = os.getenv("ADMIN_PASSWORD", ".")
    while True:
        try:
            token = await UserAdapter().login(uid, pw)
            if token:
                return token
        except Exception as e:
            err_string = str(e)
            logging.info(err_string)
        logging.info("Vision AI is waiting for db connection")
        await asyncio.sleep(5)


async def get_event(token: str) -> dict:
    """Get event_details - use info from config and db."""
    def raise_multiple_events_error(events_db: list) -> None:
        """Raise an exception for multiple events found."""
        information = (
            f"Multiple events found. Please specify an EVENT_ID in .env: {events_db}"
        )
        raise Exception(information)

    event = {}
    while True:
        try:
            events_db = await EventsAdapter().get_all_events(token)
            event_id_config = os.getenv("EVENT_ID")
            if len(events_db) == 1:
                event = events_db[0]
            elif len(events_db) == 0:
                event["id"] = event_id_config
            else:
                for _event in events_db:
                    if _event["id"] == event_id_config:
                        event = _event
                        break
                else:
                    raise_multiple_events_error(events_db)
            if event:
                break
        except Exception as e:
            err_string = str(e)
            logging.info(err_string)
        logging.info("vision-ai-service is waiting for an event to work on.")
        await asyncio.sleep(5)

    return event


async def get_config(token: str, event_id: str) -> dict:
    """Get config details - use info from db."""
    analytics_running = await ConfigAdapter().get_config_bool(
        token, event_id, "VIDEO_ANALYTICS_RUNNING"
    )
    analytics_start = await ConfigAdapter().get_config_bool(
        token, event_id, "VIDEO_ANALYTICS_START"
    )
    stop_tracking = await ConfigAdapter().get_config_bool(
        token, event_id, "VIDEO_ANALYTICS_STOP"
    )
    start_simulation = await ConfigAdapter().get_config_bool(
        token, event_id, "SIMULATION_CROSSINGS_START"
    )
    draw_trigger_line = await ConfigAdapter().get_config_bool(
        token, event_id, "DRAW_TRIGGER_LINE"
    )
    return {
        "analytics_running": analytics_running,
        "analytics_start": analytics_start,
        "start_simulation": start_simulation,
        "stop_tracking": stop_tracking,
        "draw_trigger_line": draw_trigger_line,
    }


if __name__ == "__main__":
    asyncio.run(main())
