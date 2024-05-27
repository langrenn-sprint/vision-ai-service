"""Module for application looking at video and detecting line crossings."""

import logging
from logging.handlers import RotatingFileHandler
import os
import time

import click
from events_adapter import EventsAdapter
from vision_ai_service_v2 import VisionAIService2

# get base settings
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
photos_file_path = os.getenv("PHOTOS_FILE_PATH", ".")

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


@click.command(context_settings=CONTEXT_SETTINGS)
def main() -> None:
    """CLI for analysing video stream."""  # noqa: D301
    click.echo(f"\nWorking directory {os.getcwd()}")
    click.echo(f"Logging level {LOGGING_LEVEL}")
    click.echo("Press Control-C to stop.")
    EventsAdapter().add_video_service_message("Vision AI is ready.")

    while True:
        try:
            click.echo("Vision AI is idle...")
            analytics_running = EventsAdapter().get_global_setting_bool(
                "VIDEO_ANALYTICS_RUNNING"
            )
            analytics_start = EventsAdapter().get_global_setting_bool(
                "VIDEO_ANALYTICS_START"
            )
            stop_tracking = EventsAdapter().get_global_setting_bool(
                "VIDEO_ANALYTICS_STOP"
            )
            draw_trigger_line = EventsAdapter().get_global_setting_bool(
                "DRAW_TRIGGER_LINE"
            )

            if stop_tracking:
                EventsAdapter().update_global_setting("VIDEO_ANALYTICS_STOP", "false")
            elif (not analytics_running) and (analytics_start):
                click.echo("Vision AI video detection is started...")
                EventsAdapter().add_video_service_message("Starter AI video detection.")
                EventsAdapter().update_global_setting("VIDEO_ANALYTICS_START", "False")
                result = VisionAIService2().detect_crossings_with_ultraltyics(
                    photos_file_path
                )

                EventsAdapter().add_video_service_message(
                    "Avsluttet AI video detection."
                )
                click.echo(f"Video detection complete - {result}")
            elif (not analytics_running) and (draw_trigger_line):
                click.echo("Vision trigger line detection is started...")
                EventsAdapter().update_global_setting("DRAW_TRIGGER_LINE", "False")
                result = VisionAIService2().draw_trigger_line_with_ultraltyics(
                    photos_file_path
                )
                click.echo(f"Trigger line complete - {result}")
            elif analytics_running:
                # invalid scenario - reset
                EventsAdapter().update_global_setting(
                    "VIDEO_ANALYTICS_RUNNING", "False"
                )
            time.sleep(5)

        except Exception as e:
            EventsAdapter().add_video_service_message(
                f"Critical Error - exiting program: {e}"
            )
            logging.error(f"{e}")
            click.echo("Critical Error - exiting program!\n")
            break

    click.echo("Bye!\n")


if __name__ == "__main__":
    main()
