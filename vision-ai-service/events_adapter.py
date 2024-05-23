"""Module for events adapter."""

from datetime import datetime
import json
import logging
import os
from zoneinfo import ZoneInfo


class EventsAdapter:
    """Class representing events."""

    def get_env(self, param_name: str) -> str:
        """Get settings from .env file.

        Args:
            param_name: The name of the environment variable to retrieve.

        Returns:
            The value of the environment variable, or None if the variable is not found.

        Raises:
            Exception: If an error occurs while reading the .env file.
        """
        cf = ".env"
        config_file = f"{os.getcwd()}/{cf}"
        try:
            with open(config_file, "r") as file:
                lines = file.read()
                env_list = lines.split("\n")
                for line in env_list:
                    if line.startswith(param_name):
                        key, value = line.split("=")
                        return value
        except Exception as e:
            err_info = f"Erorr loading env {param_name}. File path {config_file} - {e}"
            logging.error(err_info)
            raise Exception(err_info) from None
        return None

    def get_global_setting(self, param_name: str) -> str:
        """Get global settings from global_settings.json file."""
        config_file = os.getenv("GLOBAL_SETTINGS_FILE")
        try:
            with open(config_file, "r") as json_file:
                settings = json.load(json_file)
                global_setting = settings[param_name]
        except Exception as e:
            logging.error(
                f"Global setting {param_name} not found. File path {config_file} - {e}"
            )
            raise Exception from e
        return global_setting

    def get_video_service_status_messages(self) -> list:
        """Get video service status."""
        video_status = []
        # cf = os.getenv("VIDEO_STATUS_FILE")
        # config_file = f"{os.getcwd()}/{cf}"
        config_file = "/Users/t520834/github/photo-service-gui/photo_service_gui/files/video_status.json"
        try:
            with open(config_file, "r") as json_file:
                video_status = json.load(json_file)
        except Exception as e:
            err_info = f"Erorr loading video status. File path {config_file} - {e}"
            logging.error(err_info)
            raise Exception(err_info) from None
        return video_status

    def add_video_service_message(self, message: str) -> None:
        """Get video service status."""
        current_time = datetime.now()
        time_text = current_time.strftime("%H:%M:%S")
        video_status = []
        # cf = os.getenv("VIDEO_STATUS_FILE")
        # config_file = f"{os.getcwd()}/{cf}"
        config_file = "/Users/t520834/github/photo-service-gui/photo_service_gui/files/video_status.json"
        try:
            with open(config_file, "r") as json_file:
                old_status = json.load(json_file)

            i = 0
            video_status.append(f"{time_text} {message}")
            for my_message in old_status:
                video_status.append(my_message)
                if i > 20:
                    break
                i += 1

            # Write the updated dictionary to the global settings file in write mode.
            with open(config_file, "w") as json_file:
                json.dump(video_status, json_file)

        except Exception as e:
            err_info = f"Erorr updating video status. File path {config_file} - {e}"
            logging.error(err_info)
            raise Exception(err_info) from None

    def update_global_setting(self, param_name: str, new_value: str) -> None:
        """Update global_settings file."""
        # cf = os.getenv("GLOBAL_SETTINGS_FILE")
        # config_file = f"{os.getcwd()}/{cf}"
        config_file = "/Users/t520834/github/photo-service-gui/photo_service_gui/config/global_settings.json"
        try:
            # Open the global settings file in read-only mode.
            with open(config_file, "r") as json_file:
                settings = json.load(json_file)

                # Update the value of the global setting in the dictionary.
                settings[param_name] = new_value

            # Write the updated dictionary to the global settings file in write mode.
            with open(config_file, "w") as json_file:
                json.dump(settings, json_file)

        except Exception as e:
            err_info = f"Erorr updating global setting {param_name}. File path {config_file} - {e}"
            logging.error(err_info)
            raise Exception(err_info) from None

    def get_local_datetime_now(self, event: dict) -> datetime:
        """Return local datetime object, time zone adjusted from event info."""
        timezone = event["timezone"]
        if timezone:
            local_time_obj = datetime.now(ZoneInfo(timezone))
        else:
            local_time_obj = datetime.now()
        return local_time_obj

    def get_local_time(self, event: dict, format: str) -> str:
        """Return local time string, time zone adjusted from event info."""
        local_time = ""
        timezone = event["timezone"]
        if timezone:
            t_n = datetime.now(ZoneInfo(timezone))
        else:
            t_n = datetime.now()

        if format == "HH:MM":
            local_time = f"{t_n.strftime('%H')}:{t_n.strftime('%M')}"
        elif format == "log":
            local_day = (
                f"{t_n.strftime('%Y')}-{t_n.strftime('%m')}-{t_n.strftime('%d')}"
            )
            local_time = f"{local_day}T{t_n.strftime('%X')}"
        else:
            local_time = t_n.strftime("%X")
        return local_time
