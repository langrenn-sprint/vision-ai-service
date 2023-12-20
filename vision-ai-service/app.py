"""Module for application looking at video and detecting line crossings."""
#!/usr/bin/env python3
import logging
import os
from typing import Any

import click
from dotenv import load_dotenv

from vision_ai_service import VisionAIService


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
load_dotenv()
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL")

logging.basicConfig(
    level=LOGGING_LEVEL,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("url", type=click.STRING)
@click.option(
    "-d",
    "--directory",
    default=os.getcwd(),
    help="Relative path to the directory to watch",
    show_default=True,
    type=click.Path(
        exists=True,
        file_okay=False,
    ),
)


def main(url: str, directory: Any):
    """CLI for analysing video stream.

    To stop the vision-ai-service, press Control-C.
    \f
    Args:
        url: the URL to a video stream.
        directory: relative path to the directory to watch
    """  # noqa: D301
    click.echo(f"\nWorking directory {os.getcwd()}")
    click.echo(f"Analysing video at {url}")

    try:
        click.echo(f"Watching video at {url}")
        click.echo(f"Logging level {LOGGING_LEVEL}")
        click.echo("Press Control-C to stop.")
        click.echo("Waiting for a person to cross the finish line...")
        ai_video_service = VisionAIService().detect_crossings_with_ultraltyics(url, "Finish", 0.8) 
        click.echo(f"Got result {ai_video_service}")
    except Exception as e:
        click.echo(f"Error: {e}\n")

    click.echo("Bye!\n")

if __name__ == "__main__":
    main()
