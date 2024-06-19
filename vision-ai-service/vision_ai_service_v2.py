"""Module for video services."""

import datetime
import json
import logging

import cv2
from events_adapter import EventsAdapter
from exceptions import VideoStreamNotFoundException
import piexif
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from torch import tensor
from ultralytics import YOLO

camera_location = EventsAdapter().get_global_setting("CAMERA_LOCATION")
show_video = EventsAdapter().get_global_setting_bool("SHOW_VIDEO")
trigger_line_config_file = EventsAdapter().get_global_setting(
    "TRIGGER_LINE_CONFIG_FILE"
)


class VisionAIService2:
    """Class representing video analytics v2 with higher definition photos."""

    def detect_crossings_with_ultraltyics(
        self,
        photos_file_path: str,
        video_stream_url: str,
    ) -> str:
        """Analyze video and capture screenshots of line crossings.

        Args:
            photos_file_path: The path to the directory where the photos will be saved.
            video_stream_url: The URL of the video stream or video file.

        Returns:
            A string indicating the status of the video analytics.

        Raises:
            VideoStreamNotFoundException: If the video stream cannot be found.

        """
        crossings = {}
        crossings = VisionAIService2().reset_line_crossings(crossings)
        firstDetection = True
        informasjon = ""

        # Load an official or custom model
        model = YOLO("yolov8n.pt")  # Load an official Detect model

        # Perform tracking with the model
        try:
            results = model.track(
                source=video_stream_url, show=show_video, stream=True, persist=True
            )
        except Exception as e:
            logging.error(f"Error opening video stream from: {video_stream_url}")
            raise VideoStreamNotFoundException(
                f"Error opening video stream: {video_stream_url}"
            ) from e

        # open new stream to capture higher quality image
        cap = cv2.VideoCapture(video_stream_url)
        # check if video stream is opened
        if not cap.isOpened():
            logging.error(f"Error opening video stream from: {video_stream_url}")
            raise VideoStreamNotFoundException(
                f"Error opening video stream: {video_stream_url}"
            ) from None

        EventsAdapter().update_global_setting("VIDEO_ANALYTICS_RUNNING", "true")
        for result in results:
            # get high res screenshot
            current_time = datetime.datetime.now()
            ret_save, img = cap.read()
            # Convert the frame to RBG
            img_array = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_highres = Image.fromarray(img_array)
            if firstDetection:
                firstDetection = False
                VisionAIService2().print_image_with_trigger_line_v2(
                    photos_file_path, video_stream_url
                )

            boxes = result.boxes
            if boxes:
                class_values = boxes.cls

                for y in range(len(class_values)):
                    try:
                        id = int(boxes.id[y].item())
                        # reset the list if counting is reset
                        if id == 1 and len(crossings["100"]) > 1:
                            crossings = VisionAIService2().reset_line_crossings(
                                crossings
                            )
                        if class_values[y] == 0:  # identify person
                            xyxyn = boxes.xyxyn[y]
                            boxCrossedLine = VisionAIService2().is_below_line(xyxyn)
                            # ignore small boxes
                            boxValidation = VisionAIService2().validate_box(xyxyn)

                            if (boxCrossedLine != "false") and boxValidation:
                                # Extract screenshot image from the results
                                xyxy = boxes.xyxy[y]
                                if boxCrossedLine != "100":
                                    if id not in crossings[boxCrossedLine].keys():
                                        crossings[boxCrossedLine][id] = (
                                            self.get_crop_image(img_highres, xyxy)
                                        )
                                else:
                                    if id not in crossings[boxCrossedLine]:
                                        crossings[boxCrossedLine].append(id)
                                        VisionAIService2().save_image(
                                            img_highres,
                                            camera_location,
                                            current_time,
                                            photos_file_path,
                                            id,
                                            crossings,
                                            xyxy,
                                        )

                    except TypeError as e:
                        logging.debug(f"TypeError: {e}")
                        pass  # ignore
            if VisionAIService2().check_stop_tracking():
                informasjon = "Tracking terminated on stop command."
                break

        EventsAdapter().update_global_setting("VIDEO_ANALYTICS_RUNNING", "false")

        if show_video:
            cv2.destroyAllWindows()
        cap.release()
        return f"Analytics completed {informasjon}."

    def get_trigger_line_xyxy_list(self) -> list:
        """Get list of trigger line coordinates."""
        trigger_line_xyxy = EventsAdapter().get_global_setting("TRIGGER_LINE_XYXYN")

        trigger_line_xyxy_list = []

        try:
            trigger_line_xyxy_list = [float(i) for i in trigger_line_xyxy.split(":")]
        except Exception as e:
            logging.error(f"Error reading TRIGGER_LINE_XYXYN: {e}")
            raise e

        # validate for correct number of coordinates
        if len(trigger_line_xyxy_list) != 4:
            informasjon = "TRIGGER_LINE_XYXYN must have 4 numbers, colon-separated."
            logging.error(f"{informasjon} {trigger_line_xyxy}")
            raise Exception(f"{informasjon} {trigger_line_xyxy}")
        return trigger_line_xyxy_list

    def validate_box(self, xyxyn: tensor) -> bool:  # type: ignore
        """Function to filter out boxes not relevant."""
        boxValidation = True
        box_min_size = float(
            EventsAdapter().get_global_setting("DETECTION_BOX_MINIMUM_SIZE")
        )
        box_with = xyxyn.tolist()[2] - xyxyn.tolist()[0]  # type: ignore
        box_heigth = xyxyn.tolist()[3] - xyxyn.tolist()[1]  # type: ignore

        # check if box is too small and at the edge
        if (box_with < box_min_size) or (box_heigth < box_min_size):
            if (xyxyn.tolist()[2] > 0.98) or (xyxyn.tolist()[3] > 0.98):  # type: ignore
                return False

        # check if box is too big
        box_max_size = float(
            EventsAdapter().get_global_setting("DETECTION_BOX_MAXIMUM_SIZE")
        )
        if (box_with > box_max_size) or (box_heigth > box_max_size):
            return False

        return boxValidation

    def is_below_line(self, xyxyn: tensor) -> str:  # type: ignore
        """Function to check if a point is below a trigger line."""
        xCenterPosition = (xyxyn.tolist()[2] + xyxyn.tolist()[0]) / 2  # type: ignore
        yLowerPosition = xyxyn.tolist()[3]  # type: ignore
        trigger_line = self.get_trigger_line_xyxy_list()

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

    def print_image_with_trigger_line_v2(
        self,
        photos_file_path: str,
        video_stream_url: str,
    ) -> None:
        """Function to print an image with a trigger line."""
        trigger_line_xyxyn = VisionAIService2().get_trigger_line_xyxy_list()

        cap = cv2.VideoCapture(video_stream_url)
        # check if video stream is opened
        if not cap.isOpened():
            logging.error(f"Error opening video stream from: {video_stream_url}")
            raise VideoStreamNotFoundException(
                f"Error opening video stream: {video_stream_url}"
            ) from None

        try:
            # Show the results
            ret_save, img = cap.read()
            # Convert the frame to RBG
            img_array = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            im = Image.fromarray(img_array)
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
            im.save(f"{photos_file_path}/{trigger_line_config_file}")
            EventsAdapter().add_video_service_message("Trigger line photo created")

        except TypeError as e:
            logging.debug(f"TypeError: {e}")
            pass  # ignore

    def get_image_info(self, camera_location: str, time_text: str) -> bytes:
        """Create image info EXIF data."""
        # set the params
        image_info = {"passeringspunkt": camera_location, "passeringstid": time_text}

        # create the EXIF data and convert to bytes
        exif_dict = {"0th": {piexif.ImageIFD.ImageDescription: json.dumps(image_info)}}
        exif_bytes = piexif.dump(exif_dict)
        return exif_bytes

    def get_crop_image(self, im: Image, xyxy: tensor) -> Image:  # type: ignore
        """Get cropped image."""
        imCrop = im.crop(  # type: ignore
            (xyxy.tolist()[0], xyxy.tolist()[1], xyxy.tolist()[2], xyxy.tolist()[3])  # type: ignore
        )
        return imCrop

    def save_crop_images(
        self,
        image_list: list,
        photos_file_path: str,
        camera_location: str,
        current_time: datetime,
        id: str,
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

        timestamp = current_time.strftime("%Y%m%d_%H%M%S")
        new_im.save(f"{photos_file_path}/{camera_location}_{timestamp}_{id}_crop.jpg")

    def save_image(
        self,
        im: Image,
        camera_location: str,
        current_time: datetime,
        photos_file_path: str,
        id: str,
        crossings: dict,
        xyxy: tensor,
    ) -> None:
        """Save image and crop_images to file."""
        EventsAdapter().add_video_service_message(f"Line crossing! ID:{id}")
        time_text = current_time.strftime("%Y%m%d %H:%M:%S")

        exif_bytes = VisionAIService2().get_image_info(camera_location, time_text)

        # save image to file - full size
        timestamp = current_time.strftime("%Y%m%d_%H%M%S")
        im.save(
            f"{photos_file_path}/{camera_location}_{timestamp}_{id}.jpg",
            exif=exif_bytes,
        )

        # save crop images
        crop_im_list = []
        if id in crossings["80"].keys():
            crop_im_list.append(crossings["80"][id])
            crossings["80"].pop(id)
        if id in crossings["90"].keys():
            crop_im_list.append(crossings["90"][id])
            crossings["90"].pop(id)
        crop_im_list.append(VisionAIService2().get_crop_image(im, xyxy))

        VisionAIService2().save_crop_images(
            crop_im_list,
            photos_file_path,
            camera_location,
            current_time,
            id,
        )

    def check_stop_tracking(self) -> bool:
        """Check status flags and determine if tracking should continue."""
        stop_tracking = EventsAdapter().get_global_setting_bool("VIDEO_ANALYTICS_STOP")
        if stop_tracking:
            EventsAdapter().add_video_service_message("Video analytics stopped.")
            EventsAdapter().update_global_setting("VIDEO_ANALYTICS_RUNNING", "False")
            EventsAdapter().update_global_setting("VIDEO_ANALYTICS_STOP", "False")
            return True
        return False

    def reset_line_crossings(self, crossings: dict) -> dict:
        """Reset and init line crossings."""
        crossings.clear()
        crossings = {"100": [], "90": {}, "80": {}}
        return crossings
