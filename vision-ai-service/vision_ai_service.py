"""Module for video services."""
import datetime
import json
import logging

import piexif
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from ultralytics import YOLO

from events_adapter import EventsAdapter

PHOTOS_FILE_PATH = EventsAdapter().get_global_setting("PHOTOS_FILE_PATH")
SKI_TRACKER_YAML = EventsAdapter().get_global_setting("SKI_TRACKER_YAML")


class VisionAIService:
    """Class representing video services."""

    def detect_crossings_with_ultraltyics(self, video_uri: str, point: str, posFinishLine: float) -> int:
        """Analyze video and capture screenshots of line crossings."""
        # point is the name of the point, e.g. "start" or "finish"
        # position of the finish line, horisontal line at % of the height
        first_detection = True
        crossedLineList = []  # list of people who crossed the line

        # Load an official or custom model
        model = YOLO('yolov8n.pt')  # Load an official Detect model

        # Perform tracking with the model
        results = model.track(source=video_uri, show=False, stream=True, tracker=SKI_TRACKER_YAML)

        for result in results:
            boxes = result.boxes
            if boxes:
                class_values = boxes.cls
                for y in range(len(class_values)):
                    if class_values[y] == 0:  # identify person
                        try:
                            xyxyn = boxes.xyxyn[y]
                            yLowerPosition = xyxyn.tolist()[3]

                            id = boxes.id[y]
                            if (yLowerPosition >= posFinishLine) or first_detection:
                                if id not in crossedLineList:
                                    crossedLineList.append(id)
                                    logging.info(f"A person crossed the line! ID: {boxes.id[y]}, position: {xyxyn}")
                                    # Show the results
                                    im_array = result.plot()  # plot a BGR numpy array of predictions
                                    im = Image.fromarray(im_array[..., ::-1])  # RGB PIL image
                                    # set a timestamp with font size 50
                                    draw = ImageDraw.Draw(im)

                                    # draw an horisontal line across the image to illustrate
                                    # the finish line
                                    draw.line(
                                        (
                                            50,
                                            posFinishLine * im.size[1],
                                            im.size[0] - 50,
                                            posFinishLine * im.size[1]
                                        ),
                                        fill=(255, 255, 0),
                                        width=3
                                    )

                                    # set the font size and color
                                    font_size = 50
                                    font_color = (255, 0, 0)  # red
                                    font = ImageFont.truetype("Arial", font_size)

                                    # get the current time
                                    current_time = datetime.datetime.now()
                                    time_text = current_time.strftime('%Y:%m:%d %H:%M:%S') + f" - id:{id}"
                                    if first_detection:
                                        logging.info(f"First detection - Time: {time_text}")
                                        first_detection = False
                                        time_text = f"First detection - {time_text}"

                                    draw.text((50, 50), time_text, font=font, fill=font_color)

                                    # crop to only person in box
                                    xyxy = boxes.xyxy[y]
                                    imCrop = im.crop((xyxy.tolist()[0], xyxy.tolist()[1], xyxy.tolist()[2], xyxy.tolist()[3]))

                                    # set the params
                                    image_info = {
                                        "passeringspunkt": point,
                                        "passeringstid": time_text
                                    }

                                    # create the EXIF data and convert to bytes
                                    exif_dict = {
                                        "0th": {piexif.ImageIFD.ImageDescription: json.dumps(image_info)}
                                    }
                                    exif_bytes = piexif.dump(exif_dict)

                                    # save image to file - full size
                                    im.save(f"{PHOTOS_FILE_PATH}/{point}_{id}_main.jpg", exif=exif_bytes)
                                    imCrop.save(f"{PHOTOS_FILE_PATH}/{point}_{id}_crop.jpg", exif=exif_bytes)
                        except TypeError as e:
                            logging.debug(f"TypeError: {e}")
                            pass  # ignore
        return 200
