"""Module for events adapter."""
from datetime import datetime
import json
import logging
import os
from zoneinfo import ZoneInfo


class EventsAdapter:
    """Class representing events."""

    def get_global_setting(self, param_name: str) -> str:
        """Get global settings from .env file."""
        config_files_directory = f"{os.getcwd()}/config"
        try:
            with open(f"{config_files_directory}/global_settings.json") as json_file:
                settings = json.load(json_file)
                global_setting = settings[param_name]
        except Exception as e:
            logging.error(
                f"Global setting {param_name} not found. File path {config_files_directory} - {e}"
            )
            raise Exception from e
        return global_setting

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
            time_now = datetime.now(ZoneInfo(timezone))
        else:
            time_now = datetime.now()

        if format == "HH:MM":
            local_time = f"{time_now.strftime('%H')}:{time_now.strftime('%M')}"
        elif format == "log":
            local_time = f"{time_now.strftime('%Y')}-{time_now.strftime('%m')}"
            local_time += f"-{time_now.strftime('%d')}T{time_now.strftime('%X')}"
        else:
            local_time = time_now.strftime("%X")
        return local_time
