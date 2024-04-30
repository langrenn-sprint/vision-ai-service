"""Module for ultralytics object counting service."""
import logging

import cv2
from events_adapter import EventsAdapter
from ultralytics import YOLO
from ultralytics.solutions import object_counter

class ObjectCountingService:
    """Class representing video services."""

    def detect_crossings_with_ultraltyics(
        self,
        photos_file_path: str,
    ) -> str:
        """Analyze video and capture screenshots of line crossings."""
        video_url = EventsAdapter().get_global_setting("VIDEO_URL")

        # Initialize YOLO model
        model = YOLO("yolov8n.pt")

        # Set up your video source
        cap = cv2.VideoCapture(video_url)

        # Initialize Object Counter for your line
        trigger_line = get_trigger_line_coordinates()
        classes_to_count = [0]  # person class for count

        counter = object_counter.ObjectCounter()
        counter.set_args(view_img=True,
                         reg_pts=trigger_line,
                         classes_names=model.names,
                         draw_tracks=True,
                         line_thickness=2)

        while cap.isOpened():
            ret, im0 = cap.read()
            if not ret:
                break

            # Track objects
            results = model.track(im0, persist=True, show=False, classes=classes_to_count)

            # Start counting based on tracks and your line
            im0 = counter.start_counting(im0, results)

            # Display
            cv2.imshow("Count", im0)
            if cv2.waitKey(1) == ord('q'):  # press q to quit
                break

        cap.release()
        cv2.destroyAllWindows()

def get_trigger_line_coordinates() -> list:
    """Get list of trigger line coordinates."""
    trigger_line_xyxy = EventsAdapter().get_global_setting("TRIGGER_LINE_XYXYN")
    trigger_line_xyxy_list = []

    try:
        trigger_line_xyxy_list = [float(i) for i in trigger_line_xyxy.split(":")]
        trigger_line_xyxy_list = [
             (trigger_line_xyxy_list[0], trigger_line_xyxy_list[1]),
             (trigger_line_xyxy_list[0], trigger_line_xyxy_list[3]),
             (trigger_line_xyxy_list[2], trigger_line_xyxy_list[1]),
             (trigger_line_xyxy_list[2], trigger_line_xyxy_list[3])]
    except Exception as e:
            logging.error(f"Error: {e}")
    return trigger_line_xyxy_list


