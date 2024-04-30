"""Module for application looking at video and detecting line crossings."""
import logging
import os
import time

import click
from events_adapter import EventsAdapter
from vision_ai_service import VisionAIService
from object_counting_service import ObjectCountingService
from object_detector_service import ObjectDetectorService

# CLI settings
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")

logging.basicConfig(
    level=LOGGING_LEVEL,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@click.command(context_settings=CONTEXT_SETTINGS)
def main() -> None:
    """CLI for analysing video stream."""  # noqa: D301
    click.echo(f"\nWorking directory {os.getcwd()}")
    click.echo(f"Logging level {LOGGING_LEVEL}")
    click.echo("Press Control-C to stop.")
    # photos_file_path = os.getenv("PHOTOS_FILE_PATH", "")
    photos_file_path = "../photo-service-gui/photo_service_gui/files"
    EventsAdapter().add_video_service_message("Vision AI is ready.")

    while True:
        try:
            click.echo("Vision AI is idle...")
            analytics_running = EventsAdapter().get_global_setting("VIDEO_ANALYTICS_RUNNING")
            analytics_start = EventsAdapter().get_global_setting("VIDEO_ANALYTICS_START")
            stop_tracking = EventsAdapter().get_global_setting("VIDEO_ANALYTICS_STOP")
            trigger_line = EventsAdapter().get_global_setting("DRAW_TRIGGER_LINE")

            if stop_tracking == "true":
                EventsAdapter().update_global_setting(
                    "VIDEO_ANALYTICS_STOP", "false"
                )
            elif (analytics_running == "false") and (analytics_start == "true"):
                click.echo("Vision AI video detection is started...")
                EventsAdapter().add_video_service_message("Starter AI video detection.")
                EventsAdapter().update_global_setting(
                    "VIDEO_ANALYTICS_START", "false"
                )
                # result = VisionAIService().detect_crossings_with_ultraltyics(photos_file_path)
                # result = ObjectCountingService().detect_crossings_with_ultraltyics(photos_file_path)
                detector = ObjectDetectorService(capture_index=0)
                detector()
                
                EventsAdapter().add_video_service_message("Avsluttet AI video detection.")

                click.echo(f"Video detection complete - {result}")
            elif (analytics_running == "false") and (trigger_line == "true"):
                click.echo("Vision trigger line detection is started...")
                EventsAdapter().update_global_setting(
                    "DRAW_TRIGGER_LINE", "false"
                )
                result = VisionAIService().draw_trigger_line_with_ultraltyics(photos_file_path)
                click.echo(f"Trigger line complete - {result}")
            elif (analytics_running == "true"):
                # invalid scenario - reset
                EventsAdapter().update_global_setting(
                    "VIDEO_ANALYTICS_RUNNING", "false"
                )
            time.sleep(5)

        except Exception as e:
            EventsAdapter().add_video_service_message(f"Critical AI Error: {e}")
            click.echo(f"Critical AI Error: {e}\n")

    click.echo("Bye!\n")


if __name__ == "__main__":
    main()
