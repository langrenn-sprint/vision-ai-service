"""Module for image services."""
from ftplib import FTP
import io
import json
import logging
import os

from aiohttp import ClientSession, hdrs, web
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
import cv2
from google.cloud import videointelligence
from google.cloud import vision
from msrest.authentication import CognitiveServicesCredentials
from multidict import MultiDict
from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import TAGS

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL")


class ImageService:
    """Class representing image services."""

    def analyze_photo(self, photo_file: str) -> dict:
        """Analyse photo with selected service."""
        _tags = {}
        use_azure = get_global_setting("AZURE_VISION_TEXT_SERVICE")

        if use_azure == "True":
            _tags = self.analyze_photo_with_azure_vision(
                photo_file,
            )
            logging.info(f"Analysed photo with Azure {_tags}")
        else:
            _tags = self.analyze_photo_with_google_for_langrenn(
                photo_file,
            )
            logging.info(f"Analysed photo with Google {_tags}")

        return _tags

    def analyze_photo_with_google_detailed(self, infile: str) -> dict:
        """Send infile to Google Vision API, return dict with all labels, objects and texts."""
        logging.debug("Enter Google vision API")
        _tags = {}

        # Instantiates a client
        client = vision.ImageAnnotatorClient()

        # Loads the image into memory
        with io.open(infile, "rb") as image_file:
            content = image_file.read()

        image = vision.Image(content=content)

        # Performs label detection on the image file
        response = client.label_detection(image=image)
        labels = response.label_annotations
        for label in labels:
            logging.debug(f"Found label: {label.description}")
            _tags["Label"] = label.description

        # Performs object detection on the image file
        objects = client.object_localization(image=image).localized_object_annotations
        for object_ in objects:
            logging.debug(
                "Found object: {} (confidence: {})".format(object_.name, object_.score)
            )
            _tags["Object"] = object_.name

        # Performs text detection on the image file
        response = client.document_text_detection(image=image)
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                logging.debug("\nBlock confidence: {}\n".format(block.confidence))

                for paragraph in block.paragraphs:
                    logging.debug(
                        "Paragraph confidence: {}".format(paragraph.confidence)
                    )

                    for word in paragraph.words:
                        word_text = "".join([symbol.text for symbol in word.symbols])
                        logging.debug(
                            "Word text: {} (confidence: {})".format(
                                word_text, word.confidence
                            )
                        )

                        for symbol in word.symbols:
                            logging.debug(
                                "\tSymbol: {} (confidence: {})".format(
                                    symbol.text, symbol.confidence
                                )
                            )

        if response.error.message:
            raise Exception(
                "{}\nFor more info on error messages, check: "
                "https://cloud.google.com/apis/design/errors".format(
                    response.error.message
                )
            )

        return _tags

    def analyze_photo_with_azure_vision(self, infile: str) -> dict:
        """Send infile to Azure Computer Vision API, return texts."""
        logging.debug("Enter Azure vision API")
        _tags = {}
        count_persons = 0
        _numbers = ""
        _texts = ""

        # Get credentials for Azure vision API
        subscription_key = os.getenv("AZURE_VISION_SUBSCRIPTION_KEY")
        endpoint = os.getenv("AZURE_VISION_ENDPOINT")

        # Connect to service API
        computervision_client = ComputerVisionClient(
            endpoint, CognitiveServicesCredentials(subscription_key)
        )

        # Open local image file
        local_image = io.open(infile, "rb")

        # Call API to detect texts
        description_result = computervision_client.recognize_printed_text_in_stream(
            local_image
        )

        # Get the captions (descriptions) from the response, with confidence level
        for region in description_result.regions:
            for line in region.lines:
                for word in line.words:
                    word_text = word.text
                    if word_text.isnumeric():
                        _numbers = _numbers + word_text + ";"
                    else:
                        _texts = _texts + word_text + ";"
        _tags["Numbers"] = _numbers
        _tags["Texts"] = _texts

        # Call API to get tags
        local_image = io.open(infile, "rb")
        try:
            tags_result_local = computervision_client.tag_image_in_stream(local_image)

            # Print results with confidence score
            print("Tags in the local image: ")
            if len(tags_result_local.tags) == 0:
                logging.debug("No tags detected.")
            else:
                for tag in tags_result_local.tags:
                    logging.info(
                        "'{}' with confidence {:.2f}%".format(
                            tag.name, tag.confidence * 100
                        )
                    )
                    if tag.name == "person":
                        if (
                            float(get_global_setting("CONFIDENCE_LIMIT"))
                            < tag.confidence
                        ):
                            count_persons = count_persons + 1
        except Exception as e:
            logging.error(f"Got exceptions detecting tags with Azure: {e}")

        _tags["Persons"] = str(count_persons)

        return _tags

    def analyze_photo_with_google_for_langrenn(self, infile: str) -> dict:
        """Send infile to Vision API, return dict with langrenn info."""
        logging.debug("Enter vision")
        _tags = {}
        count_persons = 0

        # Instantiates a client
        client = vision.ImageAnnotatorClient()

        # Loads the image into memory
        with io.open(infile, "rb") as image_file:
            content = image_file.read()

        image = vision.Image(content=content)

        # Performs object detection on the image file
        objects = client.object_localization(image=image).localized_object_annotations
        for object_ in objects:
            logging.debug(
                "Found object: {} (confidence: {})".format(object_.name, object_.score)
            )
            if float(get_global_setting("CONFIDENCE_LIMIT")) < object_.score:
                if object_.name == "Person":
                    count_persons = count_persons + 1
        _tags["Persons"] = str(count_persons)

        # Performs text detection on the image file
        _numbers = ""
        _texts = ""
        response = client.document_text_detection(image=image)
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        if (
                            float(get_global_setting("CONFIDENCE_LIMIT"))
                            < word.confidence
                        ):
                            word_text = "".join(
                                [symbol.text for symbol in word.symbols]
                            )
                            logging.debug(
                                "Word text: {} (confidence: {})".format(
                                    word_text, word.confidence
                                )
                            )
                            if word_text.isnumeric():
                                _numbers = _numbers + word_text + ";"
                            else:
                                _texts = _texts + word_text + ";"
        _tags["Numbers"] = _numbers
        _tags["Texts"] = _texts

        if response.error.message:
            raise Exception(
                "{}\nFor more info on error messages, check: "
                "https://cloud.google.com/apis/design/errors".format(
                    response.error.message
                )
            )

        return _tags

    def analyze_video_with_intelligence_detailed(self, infile: str) -> dict:
        """Send infile to Vision API, return dict with all labels, objects and texts."""
        logging.debug("Enter vision API")
        _tags = {}

        """Detect text in a local video."""
        video_client = videointelligence.VideoIntelligenceServiceClient()
        features = [videointelligence.Feature.TEXT_DETECTION]
        video_context = videointelligence.VideoContext()

        with io.open(infile, "rb") as file:
            input_content = file.read()

        operation = video_client.annotate_video(
            request={
                "features": features,
                "input_content": input_content,
                "video_context": video_context,
            }
        )

        logging.debug("\nProcessing video for text detection.")
        result = operation.result(timeout=300)

        # The first result is retrieved because a single video was processed.
        annotation_result = result.annotation_results[0]
        _texts = ""

        for text_annotation in annotation_result.text_annotations:
            logging.debug("\nText: {}".format(text_annotation.text))

            # Get the first text segment
            text_segment = text_annotation.segments[0]

            start_time = text_segment.segment.start_time_offset
            end_time = text_segment.segment.end_time_offset
            logging.debug(
                "start_time: {}, end_time: {}".format(
                    start_time.seconds + start_time.microseconds * 1e-6,
                    end_time.seconds + end_time.microseconds * 1e-6,
                )
            )

            logging.debug("Confidence: {}".format(text_segment.confidence))

            # Show the result for the first frame in this segment.
            frame = text_segment.frames[0]
            time_offset = frame.time_offset
            logging.debug(
                "Time offset for the first frame: {}".format(
                    time_offset.seconds + time_offset.microseconds * 1e-6
                )
            )
            _texts = _texts + text_annotation.text + ";"

        _tags["Texts"] = _texts
        return _tags

    def capture_camera_image(self, cam_id: int, outfile: str) -> None:
        """Capture image from connected camera."""
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            logging.error("Cannot open camera")
        else:
            ret, frame = camera.read()
            if ret:
                cv2.imwrite(outfile, frame)
        camera.release()
        cv2.destroyAllWindows()

    def create_thumb(self, infile: str, outfile: str) -> None:
        """Create thumb with selected service."""
        use_azure = get_global_setting("AZURE_THUMB_SERVICE")

        if use_azure == "True":
            self.create_thumb_with_azure_vision(
                infile,
                outfile,
            )
        else:
            self.create_thumb_with_pillow(
                infile,
                outfile,
            )

    def create_thumb_with_azure_vision(self, infile: str, outfile: str) -> None:
        """Send infile to Azure Computer Vision API, return new thumb."""
        logging.debug("Enter Google vision API")

        # Get credentials for Azure vision API
        subscription_key = os.getenv("AZURE_VISION_SUBSCRIPTION_KEY")
        endpoint = os.getenv("AZURE_VISION_ENDPOINT")

        # Connect to service API
        computervision_client = ComputerVisionClient(
            endpoint, CognitiveServicesCredentials(subscription_key)
        )

        # Open local image file
        local_image = io.open(infile, "rb")
        thumb_width = int(get_global_setting("PHOTO_THUMB_WIDTH"))
        thumb_heigth = int(get_global_setting("PHOTO_THUMB_HEIGTH"))

        # Returns a Generator object, a thumbnail image binary (list).
        thumb_local = computervision_client.generate_thumbnail_in_stream(
            thumb_width, thumb_heigth, local_image, True
        )

        # Write the image binary to file
        with open(outfile, "wb") as f:
            for chunk in thumb_local:
                f.write(chunk)

    def create_thumb_with_pillow(self, infile: str, outfile: str) -> None:
        """Create thumb from infile."""
        thumb_size = int(get_global_setting("PHOTO_THUMB_SIZE"))
        size = (thumb_size, thumb_size)

        try:
            with Image.open(infile) as im:
                logging.debug(f"Photo size: {im.size}")
                im.thumbnail(size)
                im.save(outfile, "JPEG")
                logging.debug(f"Created thumb: {outfile}")
        except OSError:
            logging.error(f"cannot create thumbnail for {infile} {OSError}")

    def ftp_upload(self, infile: str, outfile: str) -> str:
        """Upload infile to outfile on ftp server, return url to file."""
        ftp_dest = os.getenv("PHOTO_FTP_DEST")
        ftp_uid = os.getenv("PHOTO_FTP_UID")
        ftp_pw = os.getenv("PHOTO_FTP_PW")

        session = FTP(str(ftp_dest), str(ftp_uid), str(ftp_pw))
        file = open(infile, "rb")  # file to send
        session.storbinary("STOR " + outfile, file)  # send the file
        file.close()  # close file and FTP
        session.quit()

        url = str(os.getenv("PHOTO_FTP_BASE_URL")) + outfile
        logging.debug(f"FTP Upload file {url}")
        # ensure web safe urls
        url = url.replace(" ", "%20")

        return url

    async def get_webserver_token(self) -> str:
        """Perform login function."""
        request_body = {
            "username": os.getenv("WEBSERVER_UID"),
            "password": os.getenv("WEBSERVER_PW"),
        }
        headers = MultiDict(
            {
                hdrs.CONTENT_TYPE: "application/json",
            },
        )
        async with ClientSession() as session:
            async with session.post(
                f"{USER_SERVICE_URL}/login", headers=headers, json=request_body
            ) as response:
                result = response.status
                logging.info(f"do login - got response {result}")
                if result == 200:
                    body = await response.json()
                    token = body["token"]
                else:
                    logging.error(f"delete_user failed - {response.status}, {response}")
                    raise web.HTTPBadRequest(reason="Login to webserver failed.")

        return token

    def identify_tags(self, infile: str) -> dict:
        """Read infile, return dict with relevant tags."""
        _tags = {}
        logging.debug(f"identify_tags: {infile}")

        with Image.open(infile) as im:
            exifdata = im.getexif()
            for tag_id in exifdata:
                # get the tag name, instead of human unreadable tag id
                tag = TAGS.get(tag_id, tag_id)
                data = exifdata.get(tag_id)
                if tag == "DateTime":
                    _tags[tag] = data
                logging.debug(f"Tag: {tag} - data: {data}")

        logging.debug(f"Return tags: {_tags}")
        return _tags

    def watermark_image(self, infile: str, outfile: str) -> None:
        """Resize, watermark and save to outfile."""
        im = Image.open(infile)

        maxsize = int(get_global_setting("PHOTO_OUTPUT_MAXSIZE"))
        if (im.height > maxsize) or (im.width > maxsize):
            factor = float(1)
            if im.height > im.width:
                factor = maxsize / im.height
            else:
                factor = maxsize / im.width
            newheight = int(im.height * factor)
            newwidth = int(im.width * factor)
            im = im.resize((newwidth, newheight), Image.ANTIALIAS)

        idraw = ImageDraw.Draw(im)
        font = ImageFont.truetype("Pillow/Tests/fonts/FreeMono.ttf", size=120)
        idraw.text(
            (im.width / 2, im.height - 200),
            get_global_setting("PHOTO_WATERMARK_TEXT"),
            font=font,
        )
        im.save(outfile)
        logging.debug("Rezised and watermarked file: " + outfile)


def get_global_setting(param_name: str) -> str:
    """Get global settings from .env file."""
    photo_settings = str(os.getenv("PHOTOPUSHER_SETTINGS_FILE"))
    with open(photo_settings) as json_file:
        photopusher_settings = json.load(json_file)
    return photopusher_settings[param_name]
