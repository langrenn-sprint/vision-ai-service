"""Module for cli application monitoring directory and handle image."""
import logging
import os
from typing import Any

import click
from dotenv import load_dotenv

from . import __version__


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
load_dotenv()
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL")
WEBSERVER_TOKEN = os.getenv("WEBSERVER_TOKEN", "DUMMY")

logging.basicConfig(
    level=LOGGING_LEVEL,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__)
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
def cli(url: str, directory: Any) -> None:
    """CLI for analysing video stream.

    To stop the vision-ai-service, press Control-C.
    \f
    Args:
        url: the URL to a video stream.
        directory: relative path to the directory to watch
    """  # noqa: D301
    click.echo(f"\nWorking directory {os.getcwd()}")
    click.echo(f"Analysing video at {url}")

    click.echo("Bye!\n")
