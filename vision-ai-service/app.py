"""Module for application looking at video and detecting line crossings."""
import logging
import os

import click
from dotenv import load_dotenv
from vision_ai_service import VisionAIService


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
load_dotenv()
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
VIDEO_URL = os.getenv("VIDEO_URL")
CAMERA_LOCATION = os.getenv("CAMERA_LOCATION")
PHOTOS_FILE_PATH = os.getenv("PHOTOS_FILE_PATH")
TRIGGER_LINE_XYXY = VisionAIService().get_trigger_line_xyxy_list(os.getenv("TRIGGER_LINE_XYXY"))

logging.basicConfig(
    level=LOGGING_LEVEL,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@click.command(context_settings=CONTEXT_SETTINGS)
def main() -> None:
    """CLI for analysing video stream."""  # noqa: D301
    click.echo(f"\nWorking directory {os.getcwd()}")
    click.echo(f"Analysing video at {VIDEO_URL}")

    try:
        click.echo(f"Watching video at {VIDEO_URL}")
        click.echo(f"Logging level {LOGGING_LEVEL}")
        click.echo("Press Control-C to stop.")
        click.echo("Waiting for a person to cross the finish line...")
        VisionAIService().detect_crossings_with_ultraltyics(
            VIDEO_URL,
            CAMERA_LOCATION,
            PHOTOS_FILE_PATH,
            TRIGGER_LINE_XYXY
        )
    except Exception as e:
        click.echo(f"Error: {e}\n")

    click.echo("Bye!\n")


if __name__ == "__main__":
    main()
