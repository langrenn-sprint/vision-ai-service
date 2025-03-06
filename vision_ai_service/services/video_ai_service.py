"""Module for video services."""

import datetime
import logging

import cv2
from torch import Tensor
from ultralytics import YOLO
from ultralytics.engine.results import Results

from vision_ai_service.adapters import (
    ConfigAdapter,
    StatusAdapter,
    VideoStreamNotFoundError,
    VisionAIService,
)

DETECTION_BOX_MINIMUM_SIZE = 0.08
DETECTION_BOX_MAXIMUM_SIZE = 0.9
EDGE_MARGIN = 0.02
MIN_CONFIDENCE = 0.6
DETECTION_CLASSES = [0]  # person



class VideoAIService:
    """Class representing video analytics with high definition photos."""

    async def detect_crossings_with_ultraltyics(
        self,
        token: str,
        event: dict,
        status_type: str,
        photos_file_path: str,
    ) -> str:
        """Analyze video and capture screenshots of line crossings.

        Args:
            token: To update databes
            event: Event details
            status_type: To update status messages
            photos_file_path: The path to the directory where the photos will be saved.

        Returns:
            A string indicating the status of the video analytics.

        Raises:
            VideoStreamNotFoundError: If the video stream cannot be found.

        """
        crossings = {"100": [], "90": {}, "80": {}}
        first_detection = True
        informasjon = ""
        camera_location = await ConfigAdapter().get_config(
            token, event, "CAMERA_LOCATION"
        )
        show_video = await ConfigAdapter().get_config_bool(token, event, "SHOW_VIDEO")
        video_stream_url = await ConfigAdapter().get_config(token, event, "VIDEO_URL")
        await StatusAdapter().create_status(
            token,
            event,
            status_type,
            f"Starter AI analyse av <a href={video_stream_url}>video</a>.",
        )
        await ConfigAdapter().update_config(
            token, event, "VIDEO_ANALYTICS_START", "False"
        )

        # Load an official or custom model
        model = YOLO("yolov8n.pt")  # Load an official Detect model

        # Define the desired image size as a tuple (width, height)
        image_size = await ConfigAdapter().get_config_img_res_tuple(
            token, event, "VIDEO_ANALYTICS_IMAGE_SIZE"
        )
        trigger_line = (
            await VisionAIService().get_trigger_line_xyxy_list(
                token, event
            )
        )

        # Perform tracking with the model
        try:
            results = model.track(
                source=video_stream_url,
                show=show_video,
                conf=MIN_CONFIDENCE,
                classes=DETECTION_CLASSES,
                stream=True,
                imgsz=image_size,
                persist=True
            )
        except Exception as e:
            informasjon = f"Error opening video stream from: {video_stream_url}"
            logging.exception(informasjon)
            raise VideoStreamNotFoundError(informasjon) from e

        await ConfigAdapter().update_config(
            token, event, "VIDEO_ANALYTICS_RUNNING", "True"
        )
        for result in results:

            if first_detection:
                first_detection = False
                await self.print_image_with_trigger_line_v2(
                    token, event, status_type, photos_file_path
                )

            self.process_boxes(result, trigger_line, crossings, camera_location, photos_file_path)

            check_stop_tracking = await VisionAIService().check_stop_tracking(
                token, event, status_type
            )
            if check_stop_tracking:
                informasjon = "Tracking terminated on stop command."
                break

        await ConfigAdapter().update_config(
            token, event, "VIDEO_ANALYTICS_RUNNING", "false"
        )
        await StatusAdapter().create_status(
            token, event, status_type, "Avsluttet AI video analyse."
        )

        if show_video:
            cv2.destroyAllWindows()
        return f"Analytics completed {informasjon}."

    def process_boxes(self, result: Results, trigger_line: list, crossings: dict, camera_location: str, photos_file_path: str) -> None:
        """Process result from video analytics."""
        boxes = result.boxes
        if boxes:
            class_values = boxes.cls

            for y in range(len(class_values)):
                try:

                    d_id = int(boxes.id[y].item())  # type: ignore[attr-defined]
                    # identify person - class value 0
                    if (class_values[y] == 0) and (boxes.conf[y].item() > MIN_CONFIDENCE):
                        xyxyn = boxes.xyxyn[y]
                        crossed_line = self.is_below_line(
                            xyxyn, trigger_line
                        )
                        # ignore small boxes
                        box_validation = self.validate_box(xyxyn)
                        if (crossed_line != "false") and box_validation:
                            # Extract screenshot image from the results
                            xyxy = boxes.xyxy[y]
                            if crossed_line != "100":
                                if d_id not in crossings[crossed_line]:
                                    crossings[crossed_line][d_id] = (
                                        VisionAIService().get_crop_image(result.orig_img, xyxy)
                                    )
                            elif d_id not in crossings[crossed_line]:
                                crossings[crossed_line].append(d_id)
                                VisionAIService().save_image(
                                    result,
                                    camera_location,
                                    photos_file_path,
                                    d_id,
                                    crossings,
                                    xyxy,
                                )

                except TypeError as e:
                    logging.debug(f"TypeError: {e}")
                    # ignore


    def validate_box(self, xyxyn: Tensor) -> bool:
        """Filter out boxes not relevant."""
        box_validation = True
        box_with = xyxyn.tolist()[2] - xyxyn.tolist()[0]
        box_heigth = xyxyn.tolist()[3] - xyxyn.tolist()[1]

        # check if box is too small and at the edge
        if (box_with < DETECTION_BOX_MINIMUM_SIZE) or (box_heigth < DETECTION_BOX_MINIMUM_SIZE):
            if (xyxyn.tolist()[2] > (1 - EDGE_MARGIN)) or (xyxyn.tolist()[3] > (1 - EDGE_MARGIN)):
                return False

        if (box_with > DETECTION_BOX_MAXIMUM_SIZE) or (box_heigth > DETECTION_BOX_MAXIMUM_SIZE):
            return False

        return box_validation

    def is_below_line(self, xyxyn: Tensor, trigger_line: list) -> str:
        """Check if a point is below a trigger line."""
        x_center_pos = (xyxyn.tolist()[2] + xyxyn.tolist()[0]) / 2
        y_lower_pos = xyxyn.tolist()[3]
        x1 = trigger_line[0]
        y1 = trigger_line[1]
        x2 = trigger_line[2]
        y2 = trigger_line[3]
        # check if more than half of the box is outside line x values
        if (x_center_pos < x1) or (x_center_pos > x2):
            return "false"
        # get line derivated
        a = (y2 - y1) / (x2 - x1)
        # get line y value at point x and check if point y is below
        y = a * (x_center_pos - x1) + y1
        y_80 = a * (x_center_pos - x1) + (y1 * 0.8)
        y_90 = a * (x_center_pos - x1) + (y1 * 0.9)
        if y_lower_pos > y:
            return "100"
        if y_lower_pos > y_90:
            return "90"
        if y_lower_pos > y_80:
            return "80"
        return "false"

    async def print_image_with_trigger_line_v2(
        self,
        token: str,
        event: dict,
        status_type: str,
        photos_file_path: str,
    ) -> None:
        """Print an image with a trigger line."""
        trigger_line_xyxyn = await VisionAIService().get_trigger_line_xyxy_list(
            token, event
        )
        video_stream_url = await ConfigAdapter().get_config(token, event, "VIDEO_URL")

        cap = cv2.VideoCapture(video_stream_url)
        # check if video stream is opened
        if not cap.isOpened():
            informasjon = f"Error opening video stream from: {video_stream_url}"
            logging.error(informasjon)
            raise VideoStreamNotFoundError(informasjon) from None
        try:
            # Show the results
            ret_save, im = cap.read()
            # Convert the frame to RBG
            im_rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)

            # Draw the trigger line
            x1, y1, x2, y2 = map(float, trigger_line_xyxyn)  # Ensure integer coordinates
            cv2.line(
                im_rgb,
                (int(x1 * im.shape[1]), int(y1 * im.shape[0])),
                (int(x2 * im.shape[1]), int(y2 * im.shape[0])),
                (255, 0, 0),  # Color (BGR)
                5
            )  # Thickness

            # Draw the grid lines
            for x in range(10, 100, 10):
                cv2.line(
                    im_rgb,
                    (int(x * im.shape[1] / 100), 0),
                    (int(x * im.shape[1] / 100), im.shape[0]),
                    (255, 255, 255),
                    1
                )
            for y in range(10, 100, 10):
                cv2.line(
                    im_rgb,
                    (0, int(y * im.shape[0] / 100)),
                    (im.shape[1], int(y * im.shape[0] / 100)),
                    (255, 255, 255),
                    1
                )

            # Add text (using OpenCV)
            font_face = 1
            font_scale = 1
            font_color = (255, 0, 0)  # red

            # get the current time with timezone
            current_time = datetime.datetime.now(datetime.UTC)
            time_text = current_time.strftime("%Y%m%d_%H%M%S")
            image_time_text = (
                f"Line coordinates: {trigger_line_xyxyn}. Time: {time_text}"
            )
            cv2.putText(im_rgb, image_time_text, (50, 50), font_face, font_scale, font_color, 2, cv2.LINE_AA)

            # save image to file
            trigger_line_config_file = await ConfigAdapter().get_config(
                token, event, "TRIGGER_LINE_CONFIG_FILE"
            )
            file_name = f"{photos_file_path}/{time_text}_{trigger_line_config_file}"
            cv2.imwrite(file_name, cv2.cvtColor(im_rgb, cv2.COLOR_RGB2BGR))  # Convert back to BGR for saving
            informasjon = f"Trigger line <a title={file_name}>photo</a> created."
            await StatusAdapter().create_status(token, event, status_type, informasjon)

        except TypeError as e:
            logging.debug(f"TypeError: {e}")
            # ignore
