"""Module for cli application monitoring directory and handle image."""
import json
import logging
import os
import time
from typing import Any

from aiohttp import hdrs
import click
from dotenv import load_dotenv
from multidict import MultiDict
import requests
from sprint_photopusher.image_service import ImageService
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


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
    """CLI for monitoring directory and send content of files as json.

    URL is the url to a webserver exposing an endpoint accepting your json.

    To stop the photopusher, press Control-C.
    \f
    Args:
        url: the URL to a webserver exposing an endpoint accepting json.
        directory: relative path to the directory to watch
    """  # noqa: D301
    # Check if webserver is alive and perform login:
    if _webserver_allive(url) and _webserver_login():
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
            logging.info(f"Connected to webserver {url}")
            return True
        else:
            logging.error(f"Webserver error : {response.status_code}")
    except Exception:
        logging.error("Webserver not available. Exiting....")
    return False


def _webserver_login() -> bool:
    """Perform login function."""
    try:
        request_body = {
            "username": os.getenv("WEBSERVER_UID"),
            "password": os.getenv("WEBSERVER_PW"),
        }
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
            },
        )
        response = requests.post(
            f"{USER_SERVICE_URL}/login", headers=headers, json=request_body
        )
        if response.status_code == 200:
            response_json = response.json()
            global WEBSERVER_TOKEN
            WEBSERVER_TOKEN = response_json["token"]
            logging.info("Login successful, token retrieved")
            return True
        else:
            logging.error(f"Webserver error : {response.status_code}")
    except Exception:
        logging.error("Webserver login failed. Exiting....")
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

    # TODO: change to: def on_created(self, event: FileSystemEvent) -> None:
    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        super(EventHandler, self).on_created(event)

        src_path = event.src_path
        filename = src_path.split(os.path.sep)[-1]

        if not event.is_directory:
            if not filename.startswith("_"):
                handle_file(self.url, event.src_path)


def find_url_photofile_type(url: str, src_path: str) -> tuple:
    """Determine and return url and photo type based src_path."""
    datafile_type = ""
    _url = f"{url}/foto"
    _filename = src_path.split(os.path.sep)[-1]
    if ".jpg" in _filename:
        datafile_type = "jpg"
    elif ".JPG" in _filename:
        datafile_type = "jpg"
    elif ".mp4" in _filename:
        datafile_type = "mov"
    elif ".mov" in _filename:
        datafile_type = "mov"
    return _url, datafile_type


def handle_file(url: str, src_path: Any) -> None:
    """Convert file content to json and push to webserver at url."""
    _url, datafile_type = find_url_photofile_type(url, src_path)
    logging.debug(f"Server url: {_url} - datafile: {datafile_type}")

    if datafile_type == "mov":
        handle_video(_url, src_path)
    elif datafile_type == "jpg":
        handle_photo(_url, src_path)
    else:
        logging.info(f"Ignoring event on file {src_path}")


def handle_photo(url: str, src_path: Any) -> None:
    """Analyse photo and push to webserver at url."""
    tags = {}
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

        vision_tags = ImageService.analyze_photo(
            ImageService(),
            outfile_main,
        )
        tags.update(vision_tags)

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
        response = requests.post(url, headers=headers, data=body)
        if response.status_code == 201:
            logging.info(f"Converted and pushed {src_path} -> {response.status_code}")
        else:
            logging.error(f"got status {response.status_code}")
    except Exception as e:
        logging.error(f"got exceptions {e}")


def handle_video(url: str, src_path: Any) -> None:
    """Analyse video and push to webserver at url."""
    logging.info(f"Found video {src_path}")
    tags = {}
    # TODO - need to enhance name & move to folder thumbs
    filename = src_path.split(os.path.sep)[-1]

    tags["Filename"] = filename

    google_tags = ImageService.analyze_video_with_intelligence_detailed(
        ImageService(),
        src_path,
    )
    tags.update(google_tags)
    logging.info(f"Tags: {tags}")
