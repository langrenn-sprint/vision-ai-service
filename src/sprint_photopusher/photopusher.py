"""Module for cli application monitoring directory and handle image."""
import json
import logging
import os
import time
from typing import Any

import click
from dotenv import load_dotenv
import requests
from sprint_photopusher.image_service import ImageService
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


from . import __version__

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
load_dotenv()
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")

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
    """CLI for monitoring directory and send content of files as json.

    URL is the url to a webserver exposing an endpoint accepting your json.

    To stop the photopusher, press Control-C.
    \f
    Args:
        url: the URL to a webserver exposing an endpoint accepting json.
        directory: relative path to the directory to watch
    """  # noqa: D301
    # Check if webserver is alive:
    if _webserver_allive(url):
        click.echo(f"\nWorking directory {os.getcwd()}")
        click.echo(f"Watching {os.path.join(os.getcwd(), directory)}")
        click.echo(f"Sending photos to webserver at {url}")
    else:
        exit(2)

    monitor = FileSystemMonitor(directory=directory, url=url)
    monitor.start(loop_action=lambda: time.sleep(100))

    click.echo("Bye!\n")


def _webserver_allive(url: str) -> bool:
    try:
        _url = f"{url}/ping"
        logging.debug(f"Trying to ping webserver at {url}")
        response = requests.get(_url)
        if response.status_code == 200:
            logging.info(f"Connected to {url}")
            return True
        else:
            logging.error(f"Webserver error : {response.status_code}")
    except Exception:
        logging.error("Webserver not available. Exiting....")
    return False


class FileSystemMonitor:
    """Monitor directory and send content of files as json to webserver URL."""

    def __init__(self, url: str, directory: Any) -> None:
        """Initalize the monitor."""
        self.url = url
        self.path = directory
        self.handler = EventHandler(url)

    def start(self, loop_action: Any) -> None:
        """Start the monitor and start oberserver loop_action."""
        observer = Observer()
        observer.schedule(self.handler, self.path, recursive=True)
        observer.start()
        try:
            while True:
                loop_action()
        except KeyboardInterrupt:
            observer.stop()

        observer.join()


class EventHandler(FileSystemEventHandler):
    """Custom eventhandler class."""

    def __init__(self, url: str) -> None:
        """Init the monitor."""
        super(EventHandler, self).__init__()
        self.url = url

    def on_any_event(self, event: FileSystemEvent) -> None:
        """Handle any events primarily for logging."""
        super(EventHandler, self).on_any_event(event)

        what = "directory" if event.is_directory else "file"
        logging.info(
            f"{event.event_type} {what}: {event.src_path}",
        )

    # TODO - change to: def on_created(self, event: FileSystemEvent) -> None:
    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        super(EventHandler, self).on_created(event)

        src_path = event.src_path
        filename = src_path.split(os.path.sep)[-1]

        if not event.is_directory:
            if not filename.startswith("_"):
                handle_photo(self.url, event.src_path)


def find_url_photofile_type(url: str, src_path: str) -> tuple:
    """Determine and return url and photo type based src_path."""
    datafile_type = ""
    _url = f"{url}/foto"
    if ".jpg" in src_path.split(os.path.sep)[-1]:
        datafile_type = "jpg"
    elif ".JPG" in src_path.split(os.path.sep)[-1]:
        datafile_type = "jpg"
    return _url, datafile_type


def handle_photo(url: str, src_path: Any) -> None:
    """Convert file content to json and push to webserver at url."""
    tags = {}
    _url, datafile_type = find_url_photofile_type(url, src_path)
    logging.debug(f"Server url: {_url} - datafile: {datafile_type}")

    if _url:

        try:
            # TODO - need to enhance name & move to folder thumbs
            filename = src_path.split(os.path.sep)[-1]

            # create thumb
            directory = src_path.replace(filename, "")
            outfile_thumb = directory + "_thumb_" + filename
            outfile_main = directory + "_web_" + filename
            ImageService.create_thumb(ImageService(), src_path, outfile_thumb)

            # add watermark
            ImageService.watermark_image(ImageService(), src_path, outfile_main)

            # update webserver and link to results
            tags = ImageService.identify_tags(ImageService(), src_path)
            tags["Filename"] = filename
            logging.debug(f"Tags: {tags}")

            google_tags = ImageService.analyze_photo_with_vision_for_langrenn(
                ImageService(),
                outfile_main,
            )
            tags.update(google_tags)

            # upload files
            photo_url = ""
            photo_url = ImageService.ftp_upload(ImageService(), outfile_main, filename)
            tags["Url_photo"] = photo_url
            photo_url = ImageService.ftp_upload(
                ImageService(), outfile_thumb, "thumb_" + filename
            )
            tags["Url_thumb"] = photo_url

            headers = {"content-type": "application/json; charset=utf-8"}
            body = json.dumps(tags)
            logging.debug(f"sending body {body}")
            response = requests.post(_url, headers=headers, data=body)
            if response.status_code == 201:
                logging.info(
                    f"Converted and pushed {src_path} -> {response.status_code}"
                )
            else:
                logging.error(f"got status {response.status_code}")
        except Exception as e:
            logging.error(f"got exceptions {e}")
    else:
        logging.info(f"Ignoring event on file {src_path}")
