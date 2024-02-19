"""Module for video services."""
import datetime
import json
import logging
import os

from events_adapter import EventsAdapter
import piexif
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from torch import tensor
from ultralytics import YOLO

tracker_file = EventsAdapter().get_env("SKI_TRACKER_YAML")
SKI_TRACKER_YAML = f"{os.getcwd()}/{tracker_file}"


class VisionAIService:
    """Class representing video services."""

    def detect_crossings_with_ultraltyics(
        self,
        photos_file_path: str,
    ) -> str:
        """Analyze video and capture screenshots of line crossings."""
        lineCrossings = {}
        lineCrossings = reset_line_crossings(lineCrossings)
        firstDetection = True
        trigger_line_xyxyn = get_trigger_line_xyxy_list()
        video_url = EventsAdapter().get_global_setting("VIDEO_URL")
        camera_location = EventsAdapter().get_global_setting("CAMERA_LOCATION")

        # Load an official or custom model
        model = YOLO("yolov8n.pt")  # Load an official Detect model

        # Perform tracking with the model
        results = model.track(
            source=video_url,
            show=False,
            stream=True,
            persist=True,
            tracker=SKI_TRACKER_YAML,
        )
        EventsAdapter().update_global_setting("VIDEO_ANALYTICS_RUNNING", "true")

        for result in results:
            if firstDetection:
                firstDetection = False
                print_image_with_trigger_line(
                    result, camera_location, photos_file_path, trigger_line_xyxyn
                )
            current_time = datetime.datetime.now()
            if check_stop_tracking():
                return "Video analytics stopped."

            boxes = result.boxes
            if boxes:
                class_values = boxes.cls

                for y in range(len(class_values)):
                    try:
                        id = int(boxes.id[y].item())
                        # reset the list if counting is reset
                        if id == 1 and len(lineCrossings["100"]) > 1:
                            lineCrossings = reset_line_crossings(lineCrossings)
                        if class_values[y] == 0:  # identify person
                            xyxyn = boxes.xyxyn[y]
                            boxCrossedLine = is_below_line(xyxyn, trigger_line_xyxyn)
                            # ignore small boxes
                            boxValidation = validate_box(xyxyn)

                            if (boxCrossedLine != "false") and boxValidation:
                                # Extract screenshot image from the results
                                im_array = result.plot(labels=False, boxes=False)
                                im = Image.fromarray(
                                    im_array[..., ::-1]
                                )  # RGB PIL image
                                xyxy = boxes.xyxy[y]
                                if boxCrossedLine != "100":
                                    if id not in lineCrossings[boxCrossedLine].keys():
                                        lineCrossings[boxCrossedLine][id] = get_crop_image(im, xyxy)
                                else:
                                    if id not in lineCrossings[boxCrossedLine]:
                                        lineCrossings[boxCrossedLine].append(id)
                                        save_image(
                                            im,
                                            camera_location,
                                            current_time,
                                            photos_file_path,
                                            id,
                                            lineCrossings,
                                            xyxy,
                                        )

                    except TypeError as e:
                        logging.debug(f"TypeError: {e}")
                        pass  # ignore
        EventsAdapter().update_global_setting("VIDEO_ANALYTICS_RUNNING", "false")
        return "Video analysis complete"

    def draw_trigger_line_with_ultraltyics(
        self,
        photos_file_path: str,
    ) -> str:
        """Analyze video and capture screenshot of trigger line."""
        trigger_line_xyxyn = get_trigger_line_xyxy_list()
        video_url = EventsAdapter().get_global_setting("VIDEO_URL")
        camera_location = EventsAdapter().get_global_setting("CAMERA_LOCATION")

        # Load an official or custom model
        model = YOLO("yolov8n.pt")  # Load an official Detect model

        # Perform tracking with the model
        results = model.track(
            source=video_url,
            show=False,
            stream=True,
            persist=True,
            tracker=SKI_TRACKER_YAML,
        )

        for result in results:
            print_image_with_trigger_line(
                result, camera_location, photos_file_path, trigger_line_xyxyn
            )
            return "200 - updated trigger line photo"
        return "204 - no detection"


def get_trigger_line_xyxy_list() -> list:
    """Get list of trigger line coordinates."""
    trigger_line_xyxy = EventsAdapter().get_global_setting("TRIGGER_LINE_XYXYN")
    trigger_line_xyxy_list = []

    try:
        trigger_line_xyxy_list = [float(i) for i in trigger_line_xyxy.split(":")]
    except Exception as e:
        logging.error(f"Error: {e}")
    return trigger_line_xyxy_list


def validate_box(xyxyn: tensor) -> bool:  # type: ignore
    """Function to filter out boxes not relevant."""
    boxValidation = True
    box_min_size = float(EventsAdapter().get_global_setting("DETECTION_BOX_MINIMUM_SIZE"))
    box_with = xyxyn.tolist()[2] - xyxyn.tolist()[0]  # type: ignore
    box_heigth = xyxyn.tolist()[3] - xyxyn.tolist()[1]  # type: ignore

    # check if box is too small and at the edge
    if (box_with < box_min_size) or (box_heigth < box_min_size):
        if (xyxyn.tolist()[2] > 0.98) or (xyxyn.tolist()[3] > 0.98):  # type: ignore
            return False

    # check if box is too big
    box_max_size = float(EventsAdapter().get_global_setting("DETECTION_BOX_MAXIMUM_SIZE"))
    if (box_with > box_max_size) or (box_heigth > box_max_size):
        return False

    return boxValidation


def is_below_line(xyxyn: tensor, trigger_line: list) -> str:  # type: ignore
    """Function to check if a point is below a trigger line."""
    xCenterPosition = (xyxyn.tolist()[2] + xyxyn.tolist()[0]) / 2  # type: ignore
    yLowerPosition = xyxyn.tolist()[3]  # type: ignore

    x1 = trigger_line[0]
    y1 = trigger_line[1]
    x2 = trigger_line[2]
    y2 = trigger_line[3]
    # check if more than half of the box is outside line x values
    if (xCenterPosition < x1) or (xCenterPosition > x2):
        return "false"
    # get line derivated
    a = (y2 - y1) / (x2 - x1)
    # get line y value at point x and check if point y is below
    y = a * (xCenterPosition - x1) + y1
    y_80 = a * (xCenterPosition - x1) + (y1 * 0.8)
    y_90 = a * (xCenterPosition - x1) + (y1 * 0.9)
    if yLowerPosition > y:
        return "100"
    elif yLowerPosition > y_90:
        return "90"
    elif yLowerPosition > y_80:
        return "80"
    return "false"


def print_image_with_trigger_line(
    result: object,
    camera_location: str,
    photos_file_path: str,
    trigger_line_xyxyn: list,
) -> None:
    """Function to print an image with a trigger line."""
    try:
        # Show the results
        im_array = result.plot()  # type: ignore
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
            width=5,
        )

        # draw a dotted line grid across the image, for every 10% of the image
        for x in range(10, 100, 10):
            draw.line(
                (x * im.size[0] / 100, 0, x * im.size[0] / 100, im.size[1]),
                fill=(255, 255, 255),
                width=1,
            )
        for y in range(10, 100, 10):
            draw.line(
                (0, y * im.size[1] / 100, im.size[0], y * im.size[1] / 100),
                fill=(255, 255, 255),
                width=1,
            )

        # set the font size and color
        font_size = 50
        font_color = (255, 0, 0)  # red
        font = ImageFont.truetype("Arial", font_size)

        # get the current time
        current_time = datetime.datetime.now()
        time_text = current_time.strftime("%Y%m%d %H:%M:%S")
        image_time_text = (
            f"Crossing line coordinates: {trigger_line_xyxyn} - Time: {time_text}"
        )
        draw.text((50, 50), image_time_text, font=font, fill=font_color)

        # save image to file - full size
        im.save(f"{photos_file_path}/{camera_location}_line_config.jpg")
        EventsAdapter().add_video_service_message(
            "Trigger line photo created"
        )

    except TypeError as e:
        logging.debug(f"TypeError: {e}")
        pass  # ignore


def get_image_info(camera_location: str, time_text: str) -> bytes:
    """Create image info EXIF data."""
    # set the params
    image_info = {
        "passeringspunkt": camera_location,
        "passeringstid": time_text
    }

    # create the EXIF data and convert to bytes
    exif_dict = {"0th": {piexif.ImageIFD.ImageDescription: json.dumps(image_info)}}
    exif_bytes = piexif.dump(exif_dict)
    return exif_bytes


def get_crop_image(im: Image, xyxy: tensor) -> Image:  # type: ignore
    """Get cropped image."""
    imCrop = im.crop(  # type: ignore
        (xyxy.tolist()[0], xyxy.tolist()[1], xyxy.tolist()[2], xyxy.tolist()[3])  # type: ignore
    )
    return imCrop


def save_crop_images(
        image_list: list,
        photos_file_path: str,
        camera_location: str,
        current_time: datetime,
        id: str
) -> None:
    """Saves all crop images in one image file."""
    widths, heights = zip(*(i.size for i in image_list), strict=True)

    total_width = sum(widths)
    max_height = max(heights)

    new_im = Image.new("RGB", (total_width, max_height))

    x_offset = 0
    for im in image_list:
        new_im.paste(im, (x_offset, 0))
        x_offset += im.size[0]

    timestamp = current_time.strftime(
        "%Y%m%d_%H%M%S"
    )
    new_im.save(f"{photos_file_path}/{camera_location}_{timestamp}_{id}_crop.jpg")


def save_image(
        im: Image,
        camera_location: str,
        current_time: datetime,
        photos_file_path: str,
        id: str,
        lineCrossings: dict,
        xyxy: tensor
) -> None:
    """Save image and crop_images to file."""
    EventsAdapter().add_video_service_message(
        f"Line crossing! ID:{id}"
    )
    time_text = current_time.strftime("%Y%m%d %H:%M:%S")

    exif_bytes = get_image_info(
        camera_location, time_text
    )

    # save image to file - full size
    timestamp = current_time.strftime(
        "%Y%m%d_%H%M%S"
    )
    im.save(
        f"{photos_file_path}/{camera_location}_{timestamp}_{id}.jpg",
        exif=exif_bytes,
    )

    # save crop images
    crop_im_list = []
    if id in lineCrossings["80"].keys():
        crop_im_list.append(lineCrossings["80"][id])
        lineCrossings["80"].pop(id)
    if id in lineCrossings["90"].keys():
        crop_im_list.append(lineCrossings["90"][id])
        lineCrossings["90"].pop(id)
    crop_im_list.append(get_crop_image(im, xyxy))

    save_crop_images(
        crop_im_list,
        photos_file_path,
        camera_location,
        current_time,
        id,
    )


def check_stop_tracking() -> bool:
    """Check status flags and determine if tracking should continue."""
    stop_tracking = EventsAdapter().get_global_setting("VIDEO_ANALYTICS_STOP")
    if stop_tracking == "true":
        EventsAdapter().add_video_service_message(
            "Video analytics stopped."
        )
        EventsAdapter().update_global_setting(
            "VIDEO_ANALYTICS_RUNNING", "false"
        )
        EventsAdapter().update_global_setting("VIDEO_ANALYTICS_STOP", "false")
        return True
    return False


def reset_line_crossings(lineCrossings: dict) -> dict:
    """Reset and init line crossings."""
    lineCrossings.clear()
    lineCrossings = {
        "100": [],
        "90": {},
        "80": {}
    }
    return lineCrossings
