"""Module for video services."""

import ast
import datetime
import logging

import cv2
from torch import Tensor
from ultralytics import solutions
from vision_ai_service.adapters import ConfigAdapter
from vision_ai_service.adapters import StatusAdapter
from vision_ai_service.adapters import VideoStreamNotFoundException
from vision_ai_service.adapters import VisionAIService


class VideoAIServiceV2:
    """Class representing video analytics with ZoneTracking."""

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
            VideoStreamNotFoundException: If the video stream cannot be found.

        """
        crossings = {"100": [], "90": {}, "80": {}}  # type: ignore
        firstDetection = True
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

        # Perform tracking with the model
        try:
            cap = cv2.VideoCapture(video_stream_url)
            w, h = (
                int(cap.get(x)) for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT)
            )
            cap.release()

            # Define region points
            detection_zone_str = "[(0.4, 0.4), (0.95, 0.95)]"
            detection_zone = ast.literal_eval(detection_zone_str)
            zx1, zy1 = detection_zone[0]
            zx2, zy2 = detection_zone[1]
            region_points = [
                (int(zx1 * w), int(zy1 * h)),
                (int(zx2 * w), int(zy1 * h)),
                (int(zx2 * w), int(zy2 * h)),
                (int(zx1 * w), int(zy2 * h))
            ]

            # Init TrackZone (Object Tracking in Zones, not complete frame)
            trackzone = solutions.TrackZone(
                show=show_video,  # Display the output
                region=region_points,  # Pass region points
                model="yolo11n.pt"
            )

            results = trackzone.model.track(
                source=video_stream_url,
                show=show_video,
                classes=[0],  # person
                stream=True,
                persist=True
            )

        except Exception as e:
            logging.error(f"Error opening video stream from: {video_stream_url}")
            raise VideoStreamNotFoundException(
                f"Error opening video stream: {video_stream_url}"
            ) from e

        await ConfigAdapter().update_config(
            token, event, "VIDEO_ANALYTICS_RUNNING", "True"
        )

        # Process video
        for result in results:

            if firstDetection:
                firstDetection = False
                await self.print_image_with_trigger_line_v2(
                    token, event, status_type, photos_file_path
                )

            boxes = result.boxes
            if boxes:
                class_values = boxes.cls

                for y in range(len(class_values)):
                    try:
                        id = int(boxes.id[y].item())
                        # identify person, probability > 0.6
                        if (class_values[y] == 0) and (boxes.conf[y].item() > 0.6):
                            xyxyn = boxes.xyxyn[y]
                            trigger_line = (
                                await VisionAIService().get_trigger_line_xyxy_list(
                                    token, event
                                )
                            )
                            boxCrossedLine = self.is_below_line(
                                xyxyn, trigger_line
                            )
                            # ignore small boxes
                            boxValidation = await self.validate_box(
                                token, event, xyxyn
                            )

                            if (boxCrossedLine != "false") and boxValidation:
                                # Extract screenshot image from the results
                                xyxy = boxes.xyxy[y]
                                if boxCrossedLine != "100":
                                    if id not in crossings[boxCrossedLine].keys():  # type: ignore
                                        crossings[boxCrossedLine][id] = (  # type: ignore
                                            VisionAIService().get_crop_image(result.orig_img, xyxy)
                                        )
                                else:
                                    if id not in crossings[boxCrossedLine]:
                                        crossings[boxCrossedLine].append(id)  # type: ignore
                                        await VisionAIService().save_image(
                                            token,
                                            event,
                                            status_type,
                                            result.orig_img,
                                            camera_location,
                                            photos_file_path,
                                            id,
                                            crossings,
                                            xyxy,
                                        )

                    except TypeError as e:
                        logging.debug(f"TypeError: {e}")
                        pass  # ignore
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

    async def validate_box(self, token: str, event: dict, xyxyn: Tensor) -> bool:  # type: ignore
        """Function to filter out boxes not relevant."""
        boxValidation = True
        box_min_size = float(
            await ConfigAdapter().get_config(token, event, "DETECTION_BOX_MINIMUM_SIZE")
        )
        box_with = xyxyn.tolist()[2] - xyxyn.tolist()[0]  # type: ignore
        box_heigth = xyxyn.tolist()[3] - xyxyn.tolist()[1]  # type: ignore

        # check if box is too small and at the edge
        if (box_with < box_min_size) or (box_heigth < box_min_size):
            if (xyxyn.tolist()[2] > 0.98) or (xyxyn.tolist()[3] > 0.98):  # type: ignore
                return False

        # check if box is too big
        box_max_size = float(
            await ConfigAdapter().get_config(token, event, "DETECTION_BOX_MAXIMUM_SIZE")
        )
        if (box_with > box_max_size) or (box_heigth > box_max_size):
            return False

        return boxValidation

    def is_below_line(self, xyxyn: Tensor, trigger_line: list) -> str:  # type: ignore
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

    async def print_image_with_trigger_line_v2(
        self,
        token: str,
        event: dict,
        status_type: str,
        photos_file_path: str,
    ) -> None:
        """Function to print an image with a trigger line."""
        trigger_line_xyxyn = await VisionAIService().get_trigger_line_xyxy_list(
            token, event
        )
        video_stream_url = await ConfigAdapter().get_config(token, event, "VIDEO_URL")

        cap = cv2.VideoCapture(video_stream_url)
        # check if video stream is opened
        if not cap.isOpened():
            logging.error(f"Error opening video stream from: {video_stream_url}")
            raise VideoStreamNotFoundException(
                f"Error opening video stream: {video_stream_url}"
            ) from None
        try:
            # Show the results
            ret_save, im = cap.read()
            # Convert the frame to RBG
            im_rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
            h, w = im.shape[:2]

            # Draw the detection zone
            detection_zone_str = "[(0.3, 0), (0.95, 0.95)]"
            detection_zone = ast.literal_eval(detection_zone_str)
            zx1, zy1 = detection_zone[0]
            zx2, zy2 = detection_zone[1]
            cv2.line(
                im_rgb, (int(zx1 * w), int(zy1 * h)), (int(zx2 * w), int(zy1 * h)), (255, 0, 0), 3
            )
            cv2.line(
                im_rgb, (int(zx1 * w), int(zy1 * h)), (int(zx1 * w), int(zy2 * h)), (255, 0, 0), 3
            )
            cv2.line(
                im_rgb, (int(zx2 * w), int(zy1 * h)), (int(zx2 * w), int(zy2 * h)), (255, 0, 0), 3
            )
            cv2.line(
                im_rgb, (int(zx1 * w), int(zy2 * h)), (int(zx2 * w), int(zy2 * h)), (255, 0, 0), 3
            )

            # Draw the trigger line
            x1, y1, x2, y2 = map(float, trigger_line_xyxyn)  # Ensure integer coordinates
            cv2.line(
                im_rgb, (int(x1 * w), int(y1 * h)), (int(x2 * w), int(y2 * h)), (255, 0, 0), 5
            )

            # Draw the grid lines
            for x in range(10, 100, 10):
                cv2.line(
                    im_rgb, (int(x * w / 100), 0), (int(x * w / 100), h), (255, 255, 255), 1
                )
            for y in range(10, 100, 10):
                cv2.line(
                    im_rgb, (0, int(y * h / 100)), (w, int(y * h / 100)), (255, 255, 255), 1
                )

            # Add text (using OpenCV)
            font_face = 1
            font_scale = 2
            font_color = (255, 0, 0)  # red

            # get the current time
            current_time = datetime.datetime.now()
            image_time_text = (
                f"Crossing line & detection zone. Time: {current_time.strftime("%H:%M:%S")}"
            )
            cv2.putText(im_rgb, image_time_text, (50, 50), font_face, font_scale, font_color, 2, cv2.LINE_AA)

            # save image to file
            trigger_line_config_file = await ConfigAdapter().get_config(
                token, event, "TRIGGER_LINE_CONFIG_FILE"
            )
            time_text = current_time.strftime("%Y%m%d_%H%M%S")
            file_name = f"{photos_file_path}/{time_text}_{trigger_line_config_file}"
            cv2.imwrite(file_name, cv2.cvtColor(im_rgb, cv2.COLOR_RGB2BGR))  # Convert back to BGR for saving
            informasjon = f"Trigger line <a title={file_name}>photo</a> created."
            await StatusAdapter().create_status(token, event, status_type, informasjon)

        except TypeError as e:
            logging.debug(f"TypeError: {e}")
            pass  # ignore
