import re
import os
from typing import List
from math import inf
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
    def match_lists(list1, list2):
        if not (list1 and list2):
            logger.info(f"Cannot Match lists when one list is None: \nList 1: {list1}, \nList 2: {list2}")
            return None, None
        # Create a dictionary with keys as filenames without extensions and values as file paths for list1
        dict1 = {os.path.basename(path).split(".")[0]: path for path in list1}
        # Create a dictionary with keys as filenames without extensions and values as file paths for list2
        dict2 = {os.path.basename(path).split(".")[0]: path for path in list2}

        # Find the common keys in both dictionaries
        common_keys = set(dict1.keys()).intersection(set(dict2.keys()))

        if not (all(key in common_keys for key in dict1.keys()) and all(key in common_keys for key in dict2.keys())):
            return None, None
        # Create sorted lists based on the common keys
        list1_sorted = [dict1[key] for key in common_keys]
        list2_sorted = [dict2[key] for key in common_keys]

        return list1_sorted, list2_sorted

    @staticmethod
    def match_lists_multi(*lists):
        # Works the same as match_lists, but for an arbitrary number of lists.
        # Returns a tuple of aligned lists, or a tuple of Nones (one per input list) on failure.
        if not lists or any(l is None or len(l) == 0 for l in lists):
            logger.info(f"Cannot Match lists when one list is None or empty: {lists}")
            return tuple(None for _ in lists)

        # Build dictionaries mapping basename (without extension) -> original path for each list
        dicts = [{os.path.basename(path).split(".")[0]: path for path in lst} for lst in lists]

        # Compute intersection of keys across all lists
        common_keys = set(dicts[0].keys())
        for d in dicts[1:]:
            common_keys = common_keys.intersection(d.keys())

        # Require that every key in every list is present in the common set (i.e., all lists must match exactly)
        if not all(all(k in common_keys for k in d.keys()) for d in dicts):
            return tuple(None for _ in lists)

        # Create lists aligned by the common keys (order follows set iteration, same as match_lists)
        aligned_lists = tuple([d[key] for key in common_keys] for d in dicts)
        return aligned_lists

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

    @staticmethod
    def clean_bash_command_for_printing(command):
        # Replace absolute paths with their basenames
        def replace_path(match):
            path = match.group()
            return os.path.basename(path)

        # Regex to match absolute paths (e.g., /some/path/file)
        command = re.sub(r'/[^\s]+', replace_path, command)

        # Replace sub-XXX_ses-XXX with "subject_session"
        command = re.sub(r'sub-[a-zA-Z0-9-]+_ses-[a-zA-Z0-9-]+', 'subject_session', command)

        return command

    @staticmethod
    def sanitize_dot_string(s):
        replacements = {
            '<': '&lt;',
            '>': '&gt;',
            '&': '&amp;',
            '"': '\\"',
            '\n': '\\n',
            '\r': '',     # Optional: remove carriage returns
            '\t': '\\t',
            '\\': '\\\\'  # Escape backslashes
        }
        for char, replacement in replacements.items():
            s = s.replace(char, replacement)
        return s

    @staticmethod
    def sanitize_bash_var_string(s, to_upper = True, basename = False):
        if basename:
            s = os.path.basename(s)
        s_sanitize = s.replace('/', '_').replace('-', '_').replace('.', '_')
        s_sanitize = re.sub(string=s_sanitize, pattern=r'_+', repl='_')
        if to_upper:
            s_sanitize = s_sanitize.upper()
        s_sanitize = s_sanitize.lstrip('_').rstrip('_')
        return s_sanitize

    @staticmethod
    def remove_strings(base_string, strings_to_remove):
        strings_to_remove = Helper.flatten(strings_to_remove)
        for s in strings_to_remove:
            base_string = base_string.replace(s, "")
        return base_string

    @staticmethod
    def replace_strings(base_string: str, strings_to_replace: List[str], replacement: str):
        for s in strings_to_replace:
            base_string = base_string.replace(s, replacement)
        return base_string

    @staticmethod
    def comp_string_overlap(source, target):
        source = str(source)
        target = str(target)
        if source == target:
            return inf
        if len(source) > len(target):
            return -1
        o = 0
        for i, s in enumerate(source):
            if s == target[i]:
                o = o + 1
            else:
                return o
        return o
