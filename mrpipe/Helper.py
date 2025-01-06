import re
import os
from typing import List
from mrpipe.meta import LoggerModule
import mrpipe.meta.PathClass as Pathclass
import mrpipe
logger = LoggerModule.Logger()

class Helper(object):
    @staticmethod
    def flatten(lst):
        result = []
        for i in lst:
            if isinstance(i, list):
                result.extend(Helper.flatten(i))
            else:
                result.append(i)
        return result

    @staticmethod
    def ensure_list(x, flatten=False) -> List:
        if isinstance(x, list):
            if flatten:
                return Helper.flatten(x)
            else:
                return x
        else:
            return [x]

    @staticmethod
    def shorten_name(name: str, n=8):
        # Split the filename into words
        words = re.sub(r"([A-Z])", r"_\1", name).split('_')

        # Calculate the number of characters to take from each word
        num_chars = n // len(words)
        if num_chars < 1:
            num_chars = 1

        # Shorten each word and join them together
        shortened_words = [word[:num_chars] for word in words]
        shortened_filename = ''.join(shortened_words)

        # If the filename is still too long, truncate it
        if len(shortened_filename) > n:
            shortened_filename = shortened_filename[:n]

        return shortened_filename

    @staticmethod
    def clean(varStr):
        varClean = Helper.add_letter_if_starts_with_number(varStr)
        varClean = re.sub(r'\W+|^(?=\d)', '_', varClean)
        return varClean

    @staticmethod
    def add_letter_if_starts_with_number(s):
        if s and s[0].isdigit():
            return 'd' + s
        return s

    @staticmethod
    def separate_files(filenames, suffix, ensureEqual = False, makePaths = True):
        original_files = []
        suffixed_files = []

        for filename in filenames:
            # Split the filename into name and extension
            #name = os.path.basename(filename).split(".")[0] #failes when a dot is in the filename
            name = os.path.splitext(os.path.basename(filename).rstrip(".gz"))[0] #only works with single filetype endings or with an extra .gz ending
            #TODO: Find a proper way to seperate dots for fileendings from dots within the filename itself

            # Check if the name ends with the suffix
            if any([name.endswith(s) for s in Helper.ensure_list(suffix, flatten=True)]):
                # Remove the suffix to get the original filename
                suffixed_files.append(filename)
            else:
                original_files.append(filename)
        if ensureEqual and len(original_files) != len(suffixed_files):
            logger.error(f"Filenames were not split into equal number of files: {original_files}, {suffixed_files}. Returning None, None")
            return None, None
        if makePaths:
            original_files = [Pathclass.Path(p) for p in original_files]
            suffixed_files = [Pathclass.Path(p) for p in suffixed_files]
        logger.debug(f"Split files into: {original_files} and {suffixed_files}")
        return original_files, suffixed_files

    @staticmethod
    def get_libpath():
        return str(os.path.abspath(os.path.dirname(mrpipe.__file__)))

    @staticmethod
    def verifyFormattableString(inputs, formattable_string):
        # Find all the numbered placeholders in the format string
        placeholders = re.findall(r'{\d+}', formattable_string)
        # Check if the number of placeholders matches the number of inputs
        if len(placeholders) == len(inputs):
            logger.debug(f"The format string {formattable_string} has the correct number of placeholders: {inputs}")
            return True
        else:
            logger.debug(f"Mismatch: Expected {len(inputs)} placeholders, found {len(placeholders)}: {formattable_string} with input {inputs}")
            return False

