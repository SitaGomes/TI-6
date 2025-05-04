# -*- coding: utf-8 -*-

import re
import sys
from string import punctuation
from typing import List, Tuple, Dict

# Temporary replacement
PUNCTUATION = '''!"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~'''
# The descriptions that contain () at the end must adapt to the new policy later
punctuation = punctuation.replace('()', '')

anchor = '###'
auth_keys = ['apiKey', 'OAuth', 'X-Mashape-Key', 'User-Agent', 'No']
https_keys = ['Yes', 'No']
cors_keys = ['Yes', 'No', 'Unknown']

index_title = 0
index_desc = 1
# Remove unused variables as they are not being used in the code.
# index_auth = 2
# index_https = 3
# index_cors = 4
num_segments = 5
min_entries_per_category = 3
max_description_length = 100

anchor_re = re.compile(anchor + '\s(.+)')
NUM_SEGMENTS = 5
MIN_ENTRIES_PER_CATEGORY = 3

category_title_in_index_re = re.compile('\*\s\[(.*)\]')
link_re = re.compile('\[(.+)\]\((http.*)\)')

# Type aliases
APIList = List[str]
Categories = Dict[str, APIList]
CategoriesLineNumber = Dict[str, int]


def error_message(line_number: int, message: str) -> str:
    line = line_number + 1
    return f'(L{line:03d}) {message}'


def get_categories_content(contents: List[str]) -> Tuple[Categories, CategoriesLineNumber]:

    categories = {}
    category_line_num = {}

    for line_num, line_content in enumerate(contents):

        if line_content.startswith(anchor):
def process_category_line(line_content: str, anchor: str, line_num: int, categories: List[str], category_line_num: List[int]) -> Tuple[str, List[str], List[int]]:
    """
    Parse a category line and update the categories and category_line_num lists accordingly.

    Args:
        line_content (str): The content of the line to be parsed.
        anchor (str): The current anchor.
        line_num (int): The current line number.
        categories (List[str]): The list of categories.
        category_line_num (List[int]): The list of line numbers for categories.

    Returns:
        Tuple[str, List[str], List[int]]: Updated category, categories, and category_line_num.
    """
    category, categories, category_line_num = parse_category_line(line_content, anchor, line_num, categories, category_line_num)
    return category, categories, category_line_num
            continue

        if not line_content.startswith('|') or line_content.startswith('|---'):
            continue

        raw_title = [
            raw_content.strip() for raw_content in line_content.split('|')[1:-1]
        ][0]

        categories[category] = parse_and_add_title(raw_title, categories[category])

    return (categories, category_line_num)


def parse_category_line(line_content: str, anchor: str, line_num: int, categories: Dict[str, List[str]], category_line_num: Dict[str, int]) -> Tuple[str, Dict[str, List[str]], Dict[str, int]]:
    """Parse a category line and update the categories dictionary and category_line_num dictionary."""
    category = line_content.split(anchor)[1].strip()
    categories[category] = []
    category_line_num[category] = line_num
    return category, categories, category_line_num


def parse_and_add_title(raw_title: str, titles: List[str]) -> List[str]:
    """Parse a raw title and add it to the list of titles if it matches the expected format."""
class ValidationMethods:
    """A class containing methods to validate various parts of an API entry."""
    def __init__(self, raw_title: str, line_num: int):
        self.raw_title = raw_title
        self.line_num = line_num

    def check_title(self, title: str, line_num: int) -> None:
        """Check that the title is valid and not the same as another entry."""
        if not title.strip():
            # Special case for titles that are empty after stripping whitespace
            print(f"Entry with Title:'{self.raw_title}' on Line:{self.line_num} have Title:blank")
            return

        # Example usage: title_match = link_re.match(self.title)
        # Ensure that the title contains no invalid characters or formatting
        # and that it doesn't duplicate another entry's title.
        # This is a placeholder for actual validation logic.
        pass

    def check_description(self, description: str, line_num: int) -> None:
        # Placeholder for actual description validation logic.
        pass

    def check_auth(self, auth: str, line_num: int) -> None:
        # Placeholder for actual auth validation logic.
        pass

    def check_https(self, https: str, line_num: int) -> None:
        # Placeholder for actual https validation logic.
        pass

    def check_cors(self, cors: str, line_num: int) -> None:
        # Placeholder for actual cors validation logic.
        pass

# Example usage in the original code:
# val = ValidationMethods(raw_title, i)
# val.check_title(title, i)
# val.check_description(description, i)
# val.check_auth(auth, i)
# val.check_https(https, i)
# val.check_cors(cors, i)
    if title_match:
        title = title_match.group(1).upper()
        titles.append(title)
def check_alphabetical_order(lines: List[str]) -> List[str]:
    """
    Check that all lines are in alphabetical order. Returns a list of error messages.
    """
    errors = []
    prev_name = None
    for line_num, line in enumerate(lines, start=1):
        name = line.strip()
        if prev_name is not None and name < prev_name:
            errors.append(error_message(
                line_num, f"Line is out of alphabetical order: {prev_name} < {name}"
            ))
        prev_name = name
    return errors

def check_section_headers(lines: List[str]) -> List[str]:
    """
    Check that all sections start with `##` and have alphabetical titles. Returns a list of error messages.
    """
    errors = []
    is_in_section = False
    for line_num, line in enumerate(lines, start=1):
        name = line.strip()
        if line.startswith("##"):
            is_in_section = True
            if not name[2:].strip():
                errors.append(error_message(line_num, "Section header is empty"))
            prev_name = name
        elif is_in_section and name:
            is_in_section = False
            if name < prev_name[2:].strip():
                errors.append(error_message(
                    line_num, f"Section is out of alphabetical order: {prev_name[2:].strip()} < {name}"
                ))
    return errors

def error_message(line_num: int, message: str) -> str:
    return f"Line {line_num}: {message}"
    """Check if the titles within each category are in alphabetical order."""
    err_msgs = []

    categories, category_line_num = get_categories_content(contents=lines)

    for category, api_list in categories.items():
        if sorted(api_list) != api_list:
            err_msg = error_message(
                category_line_num[category], 
                f'{category} category is not alphabetical order'
            )
            err_msgs.append(err_msg)

    return err_msgs
    
    return err_msgs


def check_title(line_num: int, raw_title: str) -> List[str]:

    err_msgs = []

    title_match = link_re.match(raw_title)

    # url should be wrapped in "[TITLE](LINK)" Markdown syntax
    if not title_match:
        err_msg = error_message(line_num, 'Title syntax should be "[TITLE](LINK)"')
        err_msgs.append(err_msg)
    else:
        # do not allow "... API" in the entry title
        title = title_match.group(1)
        if title.upper().endswith(' API'):
            err_msg = error_message(line_num, 'Title should not end with "... API". Every entry is an API here!')
            err_msgs.append(err_msg)

    return err_msgs


def check_description(line_num: int, description: str) -> List[str]:

    err_msgs = []

    first_char = description[0]
    if first_char.upper() != first_char:
        err_msg = error_message(line_num, 'first character of description is not capitalized')
        err_msgs.append(err_msg)

    last_char = description[-1]
    if last_char in punctuation:
        err_msg = error_message(line_num, f'description should not end with {last_char}')
        err_msgs.append(err_msg)

    desc_length = len(description)
    if desc_length > max_description_length:
        err_msg = error_message(line_num, f'description should not exceed {max_description_length} characters (currently {desc_length})')
        err_msgs.append(err_msg)
    
    return err_msgs


def check_auth(line_num: int, auth: str) -> List[str]:

    err_msgs = []

    backtick = '`'
    if auth != 'No' and (not auth.startswith(backtick) or not auth.endswith(backtick)):
        err_msg = error_message(line_num, 'auth value is not enclosed with `backticks`')
        err_msgs.append(err_msg)

    if auth.replace(backtick, '') not in auth_keys:
        err_msg = error_message(line_num, f'{auth} is not a valid Auth option')
        err_msgs.append(err_msg)
    
    return err_msgs


def check_https(line_num: int, https: str) -> List[str]:

    err_msgs = []

    if https not in https_keys:
        err_msg = error_message(line_num, f'{https} is not a valid HTTPS option')
        err_msgs.append(err_msg)

    return err_msgs
def check_cors(line_num: int, cors: str) -> List[str]:
    err_msgs = []

    if cors not in cors_keys:
        err_msg = error_message(line_num, f'{cors} is not a valid CORS option')
        err_msgs.append(err_msg)
    
    return err_msgs

class EntryChecker:
    def __init__(self, segments: List[str]):
        self.raw_title = segments[index_title]
        self.description = segments[index_desc]
        self.auth = segments[index_auth]
        self.https = segments[index_https]
        self.cors = segments[index_cors]
    
    def check_all(self, line_num: int) -> List[str]:
        err_msgs = []
        err_msgs.extend(check_title(line_num, self.raw_title))
        err_msgs.extend(check_description(line_num, self.description))
        err_msgs.extend(check_auth(line_num, self.auth))
        err_msgs.extend(check_https(line_num, self.https))
        err_msgs.extend(check_cors(line_num, self.cors))
        return err_msgs

def check_entry(line_num: int, segments: List[str]) -> List[str]:
    entry_checker = EntryChecker(segments)
    return entry_checker.check_all(line_num)
        *title_err_msgs,
        *desc_err_msgs,
        *auth_err_msgs,
        *https_err_msgs,
        *cors_err_msgs
    ]

    return err_msgs


def check_file_format(lines: List[str]) -> List[str]:

    err_msgs = []
    category_title_in_index = []

    alphabetical_err_msgs = check_alphabetical_order(lines)
    err_msgs.extend(alphabetical_err_msgs)

    num_in_category = min_entries_per_category + 1
def check_file_format(filename: str) -> List[str]:
    """Check the format of the Awesome List file."""
    err_msgs = []
    with open(filename, 'r') as file:
        lines = file.readlines()

    err_msgs.extend(validate_index_and_category_titles(lines))

    category = ''
    category_line = 0
    num_in_category = 0

    for line_num, line_content in enumerate(lines):
        if line_content.startswith(anchor):
            err_msgs.extend(check_category_header(line_num, line_content, category_title_in_index))
            if num_in_category < min_entries_per_category:
                err_msgs.append(error_message(category_line, f'{category} category does not have the minimum {min_entries_per_category} entries (only has {num_in_category})'))
            
            category = line_content.split(' ')[1]
            category_line = line_num
            num_in_category = 0
            continue

        if not line_content.startswith('|') or line_content.startswith('|---'):
            continue

        num_in_category += 1
        err_msgs.extend(validate_segments(line_num, line_content))

    return err_msgs

def validate_index_and_category_titles(lines: List[str]) -> List[str]:
    err_msgs = []
    category_title_in_index = get_category_titles_in_index(lines)
    for line_num, line_content in enumerate(lines):
        # Check each category for the minimum number of entries
        if line_content.startswith(anchor):
            err_msgs.extend(check_category_header(line_num, line_content, category_title_in_index))
    return err_msgs

def check_category_header(line_num: int, line_content: str, category_title_in_index: List[str]) -> List[str]:
    err_msgs = []
    category_match = anchor_re.match(line_content)
    if category_match:
        if category_match.group(1) not in category_title_in_index:
            err_msgs.append(error_message(line_num, f'category header ({category_match.group(1)}) not added to Index section'))
    else:
        err_msgs.append(error_message(line_num, 'category header is not formatted correctly'))
    return err_msgs

def get_category_titles_in_index(lines: List[str]) -> List[str]:
    category_title_in_index = []
    for line_content in lines:
        category_title_match = category_title_in_index_re.match(line_content)
        if category_title_match:
            category_title_in_index.append(category_title_match.group(1))
    return category_title_in_index

def validate_segments(line_num: int, line_content: str) -> List[str]:
    err_msgs = []
    segments = line_content.split('|')[1:-1]
    if len(segments) < num_segments:
        err_msgs.append(error_message(line_num, f'entry does not have all the required columns (have {len(segments)}, need {num_segments})'))
        return err_msgs
    
    for segment in segments:
        if len(segment) - len(segment.lstrip()) != 1 or len(segment) - len(segment.rstrip()) != 1:
            err_msgs.append(error_message(line_num, 'each segment must start and end with exactly 1 space'))
    
    segments = [segment.strip() for segment in segments]
    entry_err_msgs = check_entry(line_num, segments)
    err_msgs.extend(entry_err_msgs)
    return err_msgs
    with open(filename, mode='r', encoding='utf-8') as file:
        lines = list(line.rstrip() for line in file)

    file_format_err_msgs = check_file_format(lines)

    if file_format_err_msgs:
        for err_msg in file_format_err_msgs:
            print(err_msg)
        sys.exit(1)


if __name__ == '__main__':

    num_args = len(sys.argv)

    if num_args < 2:
        print('No .md file passed (file should contain Markdown table syntax)')
        sys.exit(1)

    filename = sys.argv[1]

    main(filename)