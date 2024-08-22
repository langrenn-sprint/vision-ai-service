"""Module for application looking at video and detecting line crossings."""

import asyncio
import logging
from logging.handlers import RotatingFileHandler
import os

from dotenv import load_dotenv
from vision_ai_service.adapters import ConfigAdapter
from vision_ai_service.adapters import EventsAdapter
from vision_ai_service.adapters import StatusAdapter
from vision_ai_service.adapters import UserAdapter
from vision_ai_service.services import VisionAIService

# get base settings
load_dotenv()
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
photos_file_path = f"{os.getcwd()}/vision_ai_service/files"
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
    """CLI for analysing video stream."""  # noqa: D301
    try:
        # login to data-source
        login_success = False
        uid = os.getenv("ADMIN_USERNAME", "")
        pw = os.getenv("ADMIN_PASSWORD", "")
        while not login_success:
            try:
                token = await UserAdapter().login(uid, pw)
                if token:
                    login_success = True
                    break
            except Exception as e:
                logging.error(f"{e}")
            logging.info("Vision AI is waiting for db connection")
            await asyncio.sleep(5)

        event = await get_event(token)
        status_type = await ConfigAdapter().get_config(
            token, event, "VIDEO_ANALYTICS_STATUS_TYPE"
        )
        await StatusAdapter().create_status(
            token, event, status_type, "Vision AI is started."
        )
        logging.info(f"Vision AI is started. Event: {event}")

        while True:
            ai_config = await get_config(token, event)
            try:
                if ai_config["stop_tracking"]:
                    await ConfigAdapter().update_config(
                        token, event, "VIDEO_ANALYTICS_STOP", "false"
                    )
                elif (not ai_config["analytics_running"]) and (
                    ai_config["analytics_start"]
                ):
                    await VisionAIService().detect_crossings_with_ultraltyics(
                        token, event, status_type, photos_file_path
                    )
                elif (not ai_config["analytics_running"]) and ai_config[
                    "draw_trigger_line"
                ]:
                    await ConfigAdapter().update_config(
                        token, event, "DRAW_TRIGGER_LINE", "False"
                    )
                    await VisionAIService().print_image_with_trigger_line_v2(
                        token, event, status_type, photos_file_path
                    )
                elif ai_config["analytics_running"]:
                    # invalid scenario - reset
                    await ConfigAdapter().update_config(
                        token, event, "VIDEO_ANALYTICS_RUNNING", "False"
                    )
            except Exception as e:
                logging.error(f"{e}")
                err_string = str(e)
                if ("Download" in err_string) or ("Video" in err_string):
                    await StatusAdapter().create_status(
                        token,
                        event,
                        status_type,
                        f"Video stream not found: {err_string}",
                    )
                    await ConfigAdapter().update_config(
                        token, event, "VIDEO_ANALYTICS_RUNNING", "False"
                    )
                    await ConfigAdapter().update_config(
                        token, event, "VIDEO_ANALYTICS_START", "False"
                    )
                else:
                    await StatusAdapter().create_status(
                        token,
                        event,
                        status_type,
                        f"Critical Error - exiting program: {err_string}",
                    )
                    break
            logging.info("Vision AI er klar til å starte analyse.")
            await asyncio.sleep(5)
    except Exception as e:
        logging.error(f"{e}")
        await StatusAdapter().create_status(
            token, event, status_type, f"Critical Error - exiting program: {err_string}"
        )
    logging.info("Goodbye!")


async def get_event(token: str) -> dict:
    """Get event_details - use info from config and db."""
    event = {}
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
            if event_id_config:
                event["id"] = event_id_config
            else:
                event["id"] = events_db[0]["id"]
    return event


async def get_config(token: str, event: dict) -> dict:
    """Get config details - use info from db."""
    analytics_running = await ConfigAdapter().get_config_bool(
        token, event, "VIDEO_ANALYTICS_RUNNING"
    )
    analytics_start = await ConfigAdapter().get_config_bool(
        token, event, "VIDEO_ANALYTICS_START"
    )
    stop_tracking = await ConfigAdapter().get_config_bool(
        token, event, "VIDEO_ANALYTICS_STOP"
    )
    draw_trigger_line = await ConfigAdapter().get_config_bool(
        token, event, "DRAW_TRIGGER_LINE"
    )
    return {
        "analytics_running": analytics_running,
        "analytics_start": analytics_start,
        "stop_tracking": stop_tracking,
        "draw_trigger_line": draw_trigger_line,
    }


if __name__ == "__main__":
    asyncio.run(main())
