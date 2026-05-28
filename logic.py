import os
import shutil
import time
import logging
import traceback
from PIL import Image


class UIConstants:
    OUTPUT_FOLDER = "corrected"
    IMAGE_FORMATS = ('.jpg', '.jpeg', '.png')


class ImageProcessor:

    @staticmethod
    def get_resample_filter():
        if hasattr(Image, 'Resampling'):
            return Image.Resampling.LANCZOS
        return Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.BICUBIC

    @staticmethod
    def load_and_resize_image(img_path, max_size=None):
        try:
            img = Image.open(img_path)

            if max_size:
                img.thumbnail(max_size, ImageProcessor.get_resample_filter())

            return img

        except Exception as e:
            logging.error(f"Failed to load image: {img_path} - {e}")
            return None


class LoggerManager:

    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def log_error(self, msg, e=None):
        logging.error(msg)

        if e:
            logging.error(traceback.format_exc())


class ImageOrderLogic:

    @staticmethod
    def correct_image_order(all_files, first_count, last_count):

        total = len(all_files)

        interm_start = first_count
        interm_end = total - last_count

        if interm_start >= interm_end:
            return all_files

        interm_files = all_files[interm_start:interm_end]

        interm_corrected = []

        for i in range(0, len(interm_files), 2):

            if i + 1 < len(interm_files):
                interm_corrected.append(interm_files[i + 1])

            interm_corrected.append(interm_files[i])

        return (
            all_files[:interm_start]
            + interm_corrected
            + all_files[interm_end:]
        )

    @staticmethod
    def create_preview_pairs(all_files, corrected_files):

        max_pairs = max(
            (len(all_files) + 1) // 2,
            (len(corrected_files) + 1) // 2
        )

        pairs = []

        for i in range(max_pairs):

            before_pair = [
                all_files[2 * i] if 2 * i < len(all_files) else None,
                all_files[2 * i + 1] if 2 * i + 1 < len(all_files) else None
            ]

            after_pair = [
                corrected_files[2 * i] if 2 * i < len(corrected_files) else None,
                corrected_files[2 * i + 1] if 2 * i + 1 < len(corrected_files) else None
            ]

            pairs.append((before_pair, after_pair))

        return pairs