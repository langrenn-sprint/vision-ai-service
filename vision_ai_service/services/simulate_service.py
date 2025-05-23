"""Module for video services."""

import datetime
import logging
import random
from http import HTTPStatus
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from vision_ai_service.adapters.config_adapter import ConfigAdapter
from vision_ai_service.adapters.status_adapter import StatusAdapter
from vision_ai_service.adapters.vision_ai_service import VisionAIService

MAX_ERROR_COUNT = 3


class SimulateService:
    """Class simulating video analytics."""

    async def simulate_crossings(
        self,
        token: str,
        event: dict,
        status_type: str,
        photos_file_path: str,
    ) -> str:
        """Simulate line crossings for contestants from an input file.

        Args:
            token: To update databes
            event: (dict) Event details
            status_type: To update status messages
            photos_file_path: The path to the directory where simulated photos will be saved.

        Returns:
            Information about the simulation process.

        """
        informasjon = ""
        input_file = await ConfigAdapter().get_config(
            token, event["id"], "SIMULATION_START_LIST_FILE"
        )
        await ConfigAdapter().update_config(
            token, event["id"], "SIMULATION_CROSSINGS_START", "False"
        )
        camera_location = await ConfigAdapter().get_config(
            token, event["id"], "CAMERA_LOCATION"
        )
        fastest_time = await ConfigAdapter().get_config_int(
            token, event["id"], "SIMULATION_FASTEST_TIME"
        )
        try:
            contestants = get_contestant_list(input_file)
            contestants = add_random_crossing_time(contestants, fastest_time)
        except Exception as e:
            err_message = f"Error processing file {input_file} - {e}"
            await StatusAdapter().create_status(
                token,
                event,
                status_type,
                err_message,
            )
            logging.exception(err_message)
            return err_message

        for contestant in contestants:
            SimulateService().save_image(
                camera_location,
                photos_file_path,
                contestant,
            )
        await StatusAdapter().create_status(
            token,
            event,
            status_type,
            f"Simulering fullført for {len(contestants)} passeringer.",
        )
        return f"Simulation completed {informasjon}."

    def save_image(
        self,
        camera_location: str,
        photos_file_path: str,
        contestant: dict,
    ) -> None:
        """Generate and save a simulated image for a contestant.

        Args:
            camera_location: The name of the camera location.
            photos_file_path: The path to the directory where the image will be saved.
            contestant: A dictionary containing contestant information.

        """
        current_time = datetime.datetime.now(datetime.UTC)
        time_text = f"{contestant['crossing_time']}"
        exif_bytes = VisionAIService().get_image_info(camera_location, time_text)

        # Write info on image
        im = Image.new("RGB", (800, 600), color="yellow")
        font = ImageFont.load_default(size=25)
        draw = ImageDraw.Draw(im)
        info_1 = f"{contestant['name']}, {contestant['club']}"
        draw.text((50, 50), info_1, font=font, fill="black")
        info_2 = f"Start: {contestant['start_time']} - passering: {contestant['crossing_time']}"
        draw.text((50, 100), info_2, font=font, fill="black")
        info_3 = f"Lokasjon: {camera_location}"
        draw.text((50, 150), info_3, font=font, fill="black")
        font = ImageFont.load_default(size=100)
        draw.text((400, 300), str(contestant["bib"]), font=font, fill="black")

        # save image to file - full size
        timestamp = current_time.strftime("%Y%m%d_%H%M%S")
        im.save(
            f"{photos_file_path}/{camera_location}_{timestamp}_{contestant['bib']}.jpg",
            exif=exif_bytes,
        )

        # crop image
        im_c = Image.new("RGB", (400, 300), color="yellow")
        draw_c = ImageDraw.Draw(im_c)
        draw_c.text((150, 100), str(contestant["bib"]), font=font, fill="black")
        im_c.save(
            f"{photos_file_path}/{camera_location}_{timestamp}_{contestant['bib']}_crop.jpg",
            exif=exif_bytes,
        )


def add_random_crossing_time(contestants: list, fastest_time: int) -> list:
    """Add a random crossing time to each contestant's data.

    Args:
        contestants: (list) A list of contestant dictionaries.
        fastest_time: (int) The time in seconds. Crossing time for fastest racer.

    Returns:
        A list of contestant dictionaries with added crossing times.

    """
    contestants_with_crossing_time = []
    random.shuffle(contestants)
    for i, contestant in enumerate(contestants):
        contestant["crossing_time"] = add_seconds_to_time(
            contestant["start_time"], fastest_time + i
        )
        contestants_with_crossing_time.append(contestant)
    return contestants_with_crossing_time


def get_contestant_list(file_name: str) -> list:
    """Load contestant data from a CSV file.

    Args:
        file_name: The path to the CSV file.

    Returns:
        A list of dictionaries, each containing data for one contestant.

    Raises:
        Exception: If there are errors opening or parsing the file.

    """
    error_text = ""
    index_row = 0
    headers = {}
    i_errors = 0
    contestant_list = []

    input_list = get_input_as_list(file_name)

    for raw_line in input_list:
        str_oneline = raw_line.replace("\n", "")
        try:
            index_row += 1
            # split by ; or ,
            if str_oneline.find(";") == -1:
                clean_line = str_oneline.replace(",", ";")
                elements = clean_line.split(";")
            else:
                elements = str_oneline.split(";")
            # identify headers
            if index_row == 1:
                for index_column, element in enumerate(elements):
                    # special case to handle random bytes first in file
                    if index_column == 0 and element.endswith("bib"):
                        headers["bib"] = 0
                    headers[element] = index_column
            else:
                request_body = get_contestant_dict(elements, headers)
                contestant_list.append(request_body)

        except Exception as e:
            if "401" in str(e):
                error_text = f"401 Ingen tilgang, vennligst logg inn på nytt. {e}"
                break
            i_errors += 1
            error_text = f"Feil i linje {index_row}: {str_oneline}. {e}"
            logging.exception(error_text)
            error_text += f"<br>{e}"
        if i_errors > MAX_ERROR_COUNT:
            error_text = f"For mange feil i filen - avsluttet import. {error_text}"
            raise Exception(error_text)

    return contestant_list


def get_input_as_list(file_name: str) -> list:
    """Retrieve input as a list from a file or url."""
    input_list = []

    if file_name.startswith("http"):
        # read from url
        response = requests.get(file_name, timeout=10)
        if response.status_code == HTTPStatus.OK:
            text_content = response.text
            # Directly create the list from split lines
            input_list = text_content.splitlines()
        else:
            error_text = f"Fant ikke filen på url: {file_name}. {response}"
            raise Exception(error_text)
    else:
        file_path = Path(file_name)
        with file_path.open() as file:
            for line in file:
                cleaned_line = line.replace("\n", "")
                input_list.append(cleaned_line)
    return input_list


def get_contestant_dict(elements: list, headers: dict) -> dict:
    """Map data from a CSV line to a contestant dictionary.

    Args:
        elements: A list of strings representing the data elements from a CSV line.
        headers: A dictionary mapping header names to their column indices.

    Returns:
        A dictionary containing the contestant's data.

    """
    return {
        "bib": int(elements[headers["bib"]]),
        "start_time": elements[headers["scheduled_start_time"]],
        "name": elements[headers["name"]],
        "club": elements[headers["club"]],
    }


def add_seconds_to_time(time_str: str, seconds_to_add: int) -> str:
    """Add seconds to a time string in the format HH:MM:SS.

    Args:
        time_str: The time string in HH:MM:SS format.
        seconds_to_add: The number of seconds to add.

    Returns:
        A str where given seconds are added.

    """
    try:
        time_obj = datetime.datetime.fromisoformat(time_str)
        new_datetime_obj = time_obj + datetime.timedelta(seconds=seconds_to_add)
        return new_datetime_obj.isoformat()
    except ValueError:
        logging.exception(f"Invalid time format: {time_str}. Using original time.")
        return time_str
