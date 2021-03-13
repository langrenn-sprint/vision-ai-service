"""Module for image services."""
from ftplib import FTP
import io
import json
import logging
import os

from google.cloud import vision
from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import TAGS


class ImageService:
    """Class representing image services."""

    def analyze_photo_with_vision_detailed(self, infile: str) -> dict:
        """Send infile to Vision API, return dict with all labels, objects and texts."""
        logging.debug("Enter vision")
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
            logging.info(f"Found label: {label.description}")
            _tags["Label"] = label.description

        # Performs object detection on the image file
        objects = client.object_localization(image=image).localized_object_annotations
        for object_ in objects:
            logging.info(
                "Found object: {} (confidence: {})".format(object_.name, object_.score)
            )
            _tags["Object"] = object_.name

        # Performs text detection on the image file
        response = client.document_text_detection(image=image)
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                logging.info("\nBlock confidence: {}\n".format(block.confidence))

                for paragraph in block.paragraphs:
                    logging.info(
                        "Paragraph confidence: {}".format(paragraph.confidence)
                    )

                    for word in paragraph.words:
                        word_text = "".join([symbol.text for symbol in word.symbols])
                        logging.info(
                            "Word text: {} (confidence: {})".format(
                                word_text, word.confidence
                            )
                        )

                        for symbol in word.symbols:
                            logging.info(
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

    def analyze_photo_with_vision_for_langrenn(self, infile: str) -> dict:
        """Send infile to Vision API, return dict with langrenn info."""
        logging.debug("Enter vision")
        _tags = {}
        count_persons = 0
        count_skiitems = 0
        # TODO - should be moved to config file
        confidence_limit = 0.85

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
            if confidence_limit < label.score:
                logging.debug(
                    "Found label: {} (confidence: {})".format(
                        label.description, label.score
                    )
                )
                _desc = label.description
                if _desc.count("Ski") > 0:
                    count_skiitems = count_skiitems + 1
        _tags["Ski_items"] = str(count_skiitems)

        # Performs object detection on the image file
        objects = client.object_localization(image=image).localized_object_annotations
        for object_ in objects:
            if confidence_limit < object_.score:
                logging.debug(
                    "Found object: {} (confidence: {})".format(
                        object_.name, object_.score
                    )
                )
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
                        if confidence_limit < word.confidence:
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

    def create_thumb(self, infile: str, outfile: str) -> None:
        """Create thumb from infile."""
        size = (180, 180)

        try:
            with Image.open(infile) as im:
                logging.debug(f"Photo size: {im.size}")
                im.thumbnail(size)
                im.save(outfile, "JPEG")
                logging.debug(f"Created thumb: {outfile}")
        except OSError:
            logging.info(f"cannot create thumbnail for {infile} {OSError}")

    def ftp_upload(self, infile: str, outfile: str) -> str:
        """Upload infile to outfile on ftp server, return url to file."""
        photoftcred = os.environ["FTP_PHOTO_CREDENTIALS"]
        with open(photoftcred) as json_file:
            ftp_credentials = json.load(json_file)

        ftp_dest = ftp_credentials["PHOTO_FTP_DEST"]
        ftp_uid = ftp_credentials["PHOTO_FTP_UID"]
        ftp_pw = ftp_credentials["PHOTO_FTP_PW"]

        session = FTP(ftp_dest, ftp_uid, ftp_pw)
        file = open(infile, "rb")  # file to send
        session.storbinary("STOR " + outfile, file)  # send the file
        file.close()  # close file and FTP
        session.quit()

        url = ftp_credentials["PHOTO_FTP_BASE_URL"] + outfile
        logging.debug(f"FTP Upload file {url}")
        return url

    def identify_tags(self, infile: str) -> dict:
        """Read infile, return dict with relevant tags."""
        _tags = {}

        with Image.open(infile) as im:
            exifdata = im.getexif()
            for tag_id in exifdata:
                # get the tag name, instead of human unreadable tag id
                tag = TAGS.get(tag_id, tag_id)
                data = exifdata.get(tag_id)
                if tag == "DateTime":
                    _tags[tag] = data
            # TODO - look for information in filename
            locationtags = ["start", "race", "finish", "prize", "press"]
            _filename = infile.lower()
            for location in locationtags:
                if location in _filename:
                    _tags["Location"] = location
                    logging.debug(f"Location found: {location}")

        logging.debug(f"Return tags: {_tags}")
        return _tags

    def watermark_image(self, infile: str, outfile: str) -> None:
        """Watermark infile and move outfile to output folder."""
        tatras = Image.open(infile)
        idraw = ImageDraw.Draw(tatras)
        # TODO - move to innstillinger
        text = "Ragdesprinten"

        font = ImageFont.truetype("Pillow/Tests/fonts/FreeMono.ttf", size=120)
        idraw.text((tatras.width / 2, tatras.height - 200), text, font=font)
        tatras.save(outfile)
        logging.debug("Watermarked file: " + outfile)
