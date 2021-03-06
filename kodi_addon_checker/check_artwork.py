import os
import re
import logging
from PIL import Image
from .report import Report
from .common import has_transparency, relative_path
from .record import PROBLEM, Record, WARNING, INFORMATION

LOGGER = logging.getLogger(__name__)


def check_artwork(report: Report, addon_path: str, parsed_xml, file_index: list):
    """Checks for icon/fanart/screenshot
        :addon_path: path to the folder having addon files
        :parsed_xml: xml file i.e addon.xml
        :file_index: list having name and path of all the files in an addon
    """
    art_type = ['icon', 'fanart', 'screenshot']
    for image_type in art_type:
        _check_image_type(report, image_type, parsed_xml, addon_path)

    for file in file_index:
        if re.match(r"(?!fanart\.jpg|icon\.png).*\.(png|jpg|jpeg|gif)$", file["name"]) is not None:
            image_path = os.path.join(file["path"], file["name"])
            try:
                Image.open(image_path)
            except IOError:
                report.add(
                    Record(PROBLEM, "Could not open image, is the file corrupted ? %s" % relative_path(image_path)))


def _check_image_type(report: Report, image_type: str, parsed_xml, addon_path: str):
    """Check for whether the given image type exists or not if they do """

    icon_fallback, fanart_fallback, images = _assests(image_type, parsed_xml, addon_path)

    for image in images:
        if image.text:
            filepath = os.path.join(addon_path, image.text)

            if os.path.isfile(filepath):

                report.add(Record(INFORMATION, "Image %s exists" % image_type))
                try:
                    im = Image.open(filepath)
                    width, height = im.size

                    if image_type == "icon":
                        _check_icon(report, im, width, height)

                    elif image_type == "fanart":
                        _check_fanart(report, width, height)
                    else:
                        # screenshots have no size definitions
                        LOGGER.info("Artwork was a screenshot")
                except IOError:
                    report.add(
                        Record(PROBLEM, "Could not open image, is the file corrupted? %s" % relative_path(filepath)))

            else:
                # if it's a fallback path addons.xml should still be able to
                # get build
                if fanart_fallback or icon_fallback:
                    if icon_fallback:
                        report.add(
                            Record(INFORMATION, "You might want to add a icon"))
                    elif fanart_fallback:
                        report.add(
                            Record(INFORMATION, "You might want to add a fanart"))
                # it's no fallback path, so building addons.xml will crash -
                # this is a problem ;)
                else:
                    report.add(
                        Record(PROBLEM, "%s does not exist at specified path." % image_type))
        else:
            report.add(
                Record(WARNING, "Empty image tag found for %s" % image_type))


def _assests(image_type: str, parsed_xml, addon_path: str):
    """"""
    images = parsed_xml.findall("*//" + image_type)

    icon_fallback = False
    fanart_fallback = False

    if not images and image_type == "icon":
        icon_fallback = True
        image = type('image', (object,), {'text': 'icon.png'})()
        images.append(image)
    elif not images and image_type == "fanart":
        skip_addon_types = [".module.", "metadata.", "context.", ".language."]
        for addon_type in skip_addon_types:
            if addon_type in addon_path:
                break
        else:
            fanart_fallback = True
            image = type('image', (object,), {'text': 'fanart.jpg'})()
            images.append(image)

    return icon_fallback, fanart_fallback, images


def _check_icon(report: Report, im, width, height):
    if has_transparency(im):
        report.add(Record(PROBLEM, "Icon.png should be solid. It has transparency."))

    icon_sizes = [(256, 256), (512, 512)]

    if (width, height) not in icon_sizes:
        report.add(Record(PROBLEM, "Icon should have either 256x256 or 512x512 but it has %sx%s" % (
            width, height)))
    else:
        report.add(
            Record(INFORMATION, "Icon dimensions are fine %sx%s" % (width, height)))


def _check_fanart(report: Report, width, height):
    fanart_sizes = [(1280, 720), (1920, 1080), (3840, 2160)]
    fanart_sizes_str = " or ".join(["%dx%d" % (w, h) for w, h in fanart_sizes])

    if (width, height) not in fanart_sizes:
        report.add(Record(PROBLEM, "Fanart should have either %s but it has %sx%s" % (
            fanart_sizes_str, width, height)))
    else:
        report.add(Record(INFORMATION, "Fanart dimensions are fine %sx%s" % (width, height)))
