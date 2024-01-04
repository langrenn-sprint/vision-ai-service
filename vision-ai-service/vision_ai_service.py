"""Module for video services."""
import datetime
import json
import logging

from events_adapter import EventsAdapter
import piexif
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from ultralytics import YOLO

SKI_TRACKER_YAML = EventsAdapter().get_global_setting("SKI_TRACKER_YAML")


class VisionAIService:
    """Class representing video services."""

    def detect_crossings_with_ultraltyics(
            self,
            video_uri: str,
            camera_location: str,
            photos_file_path: str,
            trigger_line_xyxyn: list
    ) -> int:
        """Analyze video and capture screenshots of line crossings."""
        crossedLineList = []  # list of people who crossed the line
        firstDetection = True

        # Load an official or custom model
        model = YOLO("yolov8n.pt")  # Load an official Detect model

        # Perform tracking with the model
        results = model.track(source=video_uri, show=False, stream=True, tracker=SKI_TRACKER_YAML)

        for result in results:
            if firstDetection:
                firstDetection = False
                print_image_with_trigger_line(
                    result,
                    camera_location,
                    photos_file_path,
                    trigger_line_xyxyn
                )

            boxes = result.boxes
            if boxes:
                class_values = boxes.cls
                for y in range(len(class_values)):
                    if class_values[y] == 0:  # identify person
                        try:
                            xyxyn = boxes.xyxyn[y]
                            xLeftPosition = xyxyn.tolist()[0]
                            xRightPosition = xyxyn.tolist()[2]
                            xCenterPosition = (xLeftPosition + xRightPosition) / 2
                            yLowerPosition = xyxyn.tolist()[3]
                            boxCrossedLine = is_below_line(
                                [xCenterPosition, yLowerPosition],
                                trigger_line_xyxyn
                            )

                            id = boxes.id[y].item()
                            if id == 1 and len(crossedLineList) > 1:
                                crossedLineList = []  # reset the list if the first person crosses the line
                            if boxCrossedLine:
                                if id not in crossedLineList:
                                    crossedLineList.append(id)
                                    logging.info(f"Line crossing! ID:{id}, pos:{xyxyn}")
                                    # Show the results
                                    im_array = result.plot()  # plot a BGR numpy array of predictions
                                    im = Image.fromarray(im_array[..., ::-1])  # RGB PIL image
                                    # set a timestamp with font size 50
                                    draw = ImageDraw.Draw(im)
                                    font_size = 50
                                    font_color = (255, 0, 0)  # red
                                    font = ImageFont.truetype("Arial", font_size)
                                    current_time = datetime.datetime.now()
                                    time_text = current_time.strftime('%Y%m%d %H:%M:%S')
                                    draw.text((50, 50), time_text, font=font, fill=font_color)

                                    exif_bytes = create_image_info(camera_location, time_text)

                                    # save image to file - full size
                                    timestamp = current_time.strftime('%Y%m%d_%H%M%S')
                                    im.save(
                                        f"{photos_file_path}/{camera_location}_{timestamp}_{id}.jpg",
                                        exif=exif_bytes
                                    )

                                    # crop to only person in box
                                    create_crop_image(
                                        im,
                                        boxes.xyxy[y],
                                        f"{photos_file_path}/{camera_location}_{timestamp}_{id}_crop.jpg"
                                    )
                        except TypeError as e:
                            logging.debug(f"TypeError: {e}")
                            pass  # ignore
        return 200

    def get_trigger_line_xyxy_list(self, trigger_line_xyxy: str) -> list:
        """Get list of trigger line coordinates."""
        trigger_line_xyxy_list = []

        try:
            trigger_line_xyxy_list = [float(i) for i in trigger_line_xyxy.split(":")]
        except Exception as e:
            logging.error(f"Error: {e}")
        return trigger_line_xyxy_list


def is_below_line(point: list, trigger_line: list) -> bool:
    """Function to check if a point is below a trigger line."""
    bBelowLine = False
    x1 = trigger_line[0]
    y1 = trigger_line[1]
    x2 = trigger_line[2]
    y2 = trigger_line[3]
    # check if point x value is outside line x values
    if (point[0] < x1) or (point[0] > x2):
        return False
    # get line derivation
    a = (y2 - y1) / (x2 - x1)
    # get line y value at point x and check if point y is below
    y = a * (point[0] - x1) + y1
    if point[1] > y:
        bBelowLine = True

    return bBelowLine


def print_image_with_trigger_line(
    result: object,
    camera_location: str,
    photos_file_path: str,
    trigger_line_xyxyn: list
) -> None:
    """Function to print an image with a trigger line."""
    try:
        # Show the results
        im_array = result.plot()  # plot a BGR numpy array of predictions
        im = Image.fromarray(im_array[..., ::-1])  # RGB PIL image
        draw = ImageDraw.Draw(im)

        # draw a line across the image to illustrate the finish line
        draw.line(
            (
                trigger_line_xyxyn[0] * im.size[0],
                trigger_line_xyxyn[1] * im.size[1],
                trigger_line_xyxyn[2] * im.size[0],
                trigger_line_xyxyn[3] * im.size[1],
            ),
            fill=(255, 0, 0),
            width=5
        )

        # draw a dotted line grid across the image, for every 10% of the image
        for x in range(10, 100, 10):
            draw.line(
                (
                    x * im.size[0] / 100,
                    0,
                    x * im.size[0] / 100,
                    im.size[1]
                ),
                fill=(255, 255, 255),
                width=1
            )
        for y in range(10, 100, 10):
            draw.line(
                (
                    0,
                    y * im.size[1] / 100,
                    im.size[0],
                    y * im.size[1] / 100
                ),
                fill=(255, 255, 255),
                width=1
            )

        # set the font size and color
        font_size = 50
        font_color = (255, 0, 0)  # red
        font = ImageFont.truetype("Arial", font_size)

        # get the current time
        current_time = datetime.datetime.now()
        time_text = current_time.strftime('%Y%m%d %H:%M:%S')
        time_text = f"Crossing line coordinates: {trigger_line_xyxyn} - Time: {time_text}"

        draw.text((50, 50), time_text, font=font, fill=font_color)

        # save image to file - full size
        im.save(
            f"{photos_file_path}/{camera_location}_line_config.jpg"
        )
    except TypeError as e:
        logging.debug(f"TypeError: {e}")
        pass  # ignore


def create_image_info(camera_location: str, time_text: str) -> bytes:
    """Create image info EXIF data."""
    # set the params
    image_info = {
        "passeringspunkt": camera_location,
        "passeringstid": time_text
    }

    # create the EXIF data and convert to bytes
    exif_dict = {
        "0th": {piexif.ImageIFD.ImageDescription: json.dumps(image_info)}
    }
    exif_bytes = piexif.dump(exif_dict)
    return exif_bytes


def create_crop_image(
    im: object,
    xyxy: list,
    photos_file_name: str
) -> None:
    """Create cropped image."""
    imCrop = im.crop(
        (
            xyxy.tolist()[0],
            xyxy.tolist()[1] + 30,
            xyxy.tolist()[2],
            xyxy.tolist()[3]
        )
    )
    imCrop.save(photos_file_name)
    