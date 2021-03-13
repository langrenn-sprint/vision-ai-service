"""Module for image services."""
import io
import logging

from google.cloud import vision
from PIL import Image, ImageDraw, ImageFont


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
        numbers = ""
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
                                numbers = numbers + word_text + ";"
        _tags["Numbers"] = numbers

        if response.error.message:
            raise Exception(
                "{}\nFor more info on error messages, check: "
                "https://cloud.google.com/apis/design/errors".format(
                    response.error.message
                )
            )

        return _tags

    def watermark_image(self, infile: str, outfile: str) -> None:
        """Watermark infile and move outfile to output folder."""
        tatras = Image.open(infile)
        idraw = ImageDraw.Draw(tatras)
        text = "Ragdesprinten 2021, Kjelsås IL"

        font = ImageFont.truetype("Pillow/Tests/fonts/FreeMono.ttf", size=120)
        idraw.text((tatras.width / 2, tatras.height - 200), text, font=font)
        tatras.save(outfile)
        logging.debug("Watermarked file: " + outfile)
