# -*- coding: utf-8 -*-

import re
import sys
from string import punctuation
from typing import List, Tuple, Dict

PUNCTUATION_MARKS = ": .,??"
PUNCTUATION_RESERVED = r"([: .,??])"

def prepare_file(content: str) -> str:
    # ...
    for punctuation in PUNCTUATION_MARKS:
        padded_punctuation = f" {punctuation} "
        content = content.replace(punctuation, padded_punctuation)
    # ...

def revert_file(content: str) -> str:
    for punctuation in PUNCTUATION_MARKS:
padded_punctuation = f" {punctuation} "
        content = content.replace(padded_punctuation, punctuation)
    # ...
punctuation = punctuation.replace('()', '')

anchor = '###'
auth_keys = ['apiKey', 'OAuth', 'X-Mashape-Key', 'User-Agent', 'No']
https_keys = ['Yes', 'No']
cors_keys = ['Yes', 'No', 'Unknown']

index_title = 0
index_desc = 1
index_auth = 2
index_https = 3
index_cors = 4

num_segments = 5
min_entries_per_category = 3
max_description_length = 100

anchor_re = re.compile(anchor + '\s(.+)')
NUM_CATEGORY_SEGMENTS = 5
MIN_ENTRIES_PER_CATEGORY = 3

category_title_in_index_re = re.compile('\*\s\[(.*)\]')
link_re = re.compile('\[(.+)\]\((http.*)\)')

# The rest of the code remains the same, but using the symbolic constants now:
# ...
# ...

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
class Category:
    def __init__(self, name: str, entries: List[str] = None):
        self.name = name
        self.entries = entries if entries else []

    def add_entry(self, entry: str):
        self.entries.append(entry)

    def __repr__(self):
        return f'Category(name="{self.name}", entries={self.entries})'


class Dictionary:
    def __init__(self):
        self.categories = defaultdict(Category)
        self.titles_to_category = {}
        self.next_category_id = 0

    def add_category(self, name: str, entries: List[str] = None):
        category = Category(name, entries)
        self.categories[name] = category
        return category

    def add_entry_to_category(self, category_name: str, entry: str):
        category = self.categories[category_name]
        category.add_entry(entry)

    def get_category(self, name: str):
        return self.categories[name]

    def get_categories(self):
        return list(self.categories.values())

    def set_title_to_category(self, title: str, category_name: str):
        self.titles_to_category[title] = category_name

    def get_category_for_title(self, title: str):
        return self.titles_to_category.get(title)

    def __repr__(self):
        return f'Dictionary(categories={self.categories}, titles_to_category={self.titles_to_category})'


def get_categories_and_titles(header_text: str) -> Tuple[Dictionary, Dict[str, int]]:
    # ... rest of the function
    dictionary = Dictionary()
    category_dict = defaultdict(list)
    # ... rest of the function using dictionary and category_dict
    return dictionary
    categories = {}
    category_line_num = {}
    anchor = "<a"
    link_re = re.compile(r"\[([^\]]+)\]")

    lines = header_text.splitlines()
    category = None

    for line_num, line_content in enumerate(lines, start=1):
        if anchor in line_content:
            category = line_content.split(anchor)[1].strip()
            categories[category] = []
            category_line_num[category] = line_num
            continue

        if not line_content.startswith('|') or line_content.startswith('|---'):
            continue

        raw_title = [raw_content.strip() for raw_content in line_content.split('|')[1:-1]][0]

        title_match = link_re.match(raw_title)
        if title_match:
            title = title_match.group(1).upper()
            categories[category].append(title)
class APIInfo:
    def __init__(self, title, description, auth, https, cors):
        # No need to initialize line_num here as it's not a mandatory field
        self.title = title
        self.description = description
        self.auth = auth
        self.https = https
        self.cors = cors

    # Move all the check functions inside this class
    def check_title(self, line_num):
        pass  # TODO: Implement actual check
class CategoryManager:
    def _check_formats(self, annotations, flag_union=False):
        # ... (code omitted for brevity)
        for format_str in unique_formats:
            if type(format_str) == str:
                if not self._is_valid_format(format_str):
                    invalid_formats.append(format_str)
            else:
                if not flag_union:
                    logger.info("Format validator cannot validate formats containing type unions.")
                else:
                    crt_invalid_formats = [x for x in format_str if x not in _NON_STRING_FORMATS and not self._is_valid_format(x)]
                    if len(crt_invalid_formats):
                        invalid_formats.append(crt_invalid_formats)

        return invalid_formats

    def validate_annotations(self, annotations, flag_union=False, dependencies=None):
        # ... (code omitted for brevity)
        return invalid_formats

    def validate_annotations_in_metadata(self, metadata, dependencies=None):
        # ... (code omitted for brevity)
        return invalid_formats
    def __init__(self, lines):
        self.lines = lines
        self.categories, self.category_line_num = self._get_categories_content()

    def _get_categories_content(self):
        categories = {}
        category_line_num = {}
        for num_line, line in enumerate(self.lines):
            if line.startswith("### "):
                category = line.strip()[4:]
                categories[category] = []
                category_line_num[category] = num_line + 1
            elif line.startswith("- "):
                item = parse_api_entry_line(line)
                categories[category].append(item)
        return categories, category_line_num

    def check_alphabetical_order(self):
        for category, entries in self.categories.items():
            if entries != sorted(entries, key=lambda x: x['api']):
                return False, category_line_num[category]
        return True, None
    for category, api_list in categories.items():
        if sorted(api_list) != api_list:
            err_msg = error_message(
                category_line_num[category], 
                f'{category} category is not alphabetical order'
            )
            err_msgs.append(err_msg)
    
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
def check_entry(line_num: int, segments: List[str]) -> List[str]:
    raw_title = segments[index_title]
    description = segments[index_desc]
    auth = segments[index_auth]
    https = segments[index_https]
    cors = segments[index_cors]

    checks = [
        check_title(line_num, raw_title),
        check_description(line_num, description),
        check_auth(line_num, auth),
        check_https(line_num, https),
        check_cors(line_num, cors)
    ]

    err_msgs = [msg for check in checks for msg in check]

    return err_msgs


def check_file_format(lines: List[str]) -> List[str]:

    err_msgs = []
    category_title_in_index = []

    alphabetical_err_msgs = check_alphabetical_order(lines)
    err_msgs.extend(alphabetical_err_msgs)

    num_in_category = min_entries_per_category + 1
def check_category_headers(lines, err_msgs, anchor, anchor_re, category_title_in_index, min_entries_per_category, category_title_in_index_re):
    category = ''
    category_line = 0
    num_in_category = 0

    for line_num, line_content in enumerate(lines):

        category_title_match = category_title_in_index_re.match(line_content)
        if category_title_match:
            category_title_in_index.append(category_title_match.group(1))

        # check each category for the minimum number of entries
        if line_content.startswith(anchor):
            category_match = anchor_re.match(line_content)
            if category_match:
                if category_match.group(1) not in category_title_in_index:
                    err_msg = error_message(line_num, f'category header ({category_match.group(1)}) not added to Index section')
                    err_msgs.append(err_msg)
            else:
                err_msg = error_message(line_num, 'category header is not formatted correctly')
                err_msgs.append(err_msg)

            if num_in_category < min_entries_per_category:
                err_msg = error_message(category_line, f'{category} category does not have the minimum {min_entries_per_category} entries (only has {num_in_category})')
                err_msgs.append(err_msg)

            category = line_content.split(' ')[1]
            category_line = line_num
            num_in_category = 0
            continue

        # skips lines that we do not care about
        if not line_content.startswith('|') or line_content.startswith('|---'):
            continue

        num_in_category += 1

    return err_msgs, category, category_line, num_in_category

def check_entry_formats(lines, err_msgs, num_segments):
    for line_num, line_content in enumerate(lines):

        # skips lines that we do not care about
        if not line_content.startswith('|') or line_content.startswith('|---'):
            continue

        segments = line_content.split('|')[1:-1]
        if len(segments) < num_segments:
            err_msg = error_message(line_num, f'entry does not have all the required columns (have {len(segments)}, need {num_segments})')
            err_msgs.append(err_msg)
            continue
    
        for segment in segments:
            # every line segment should start and end with exactly 1 space
            if len(segment) - len(segment.lstrip()) != 1 or len(segment) - len(segment.rstrip()) != 1:
                err_msg = error_message(line_num, 'each segment must start and end with exactly 1 space')
                err_msgs.append(err_msg)
        
        segments = [segment.strip() for segment in segments]
        entry_err_msgs = check_entry(line_num, segments)
        err_msgs.extend(entry_err_msgs)
    
    return err_msgs

def check_file_format(lines: List[str], category_title_in_index_re: Pattern, anchor_re: Pattern) -> List[str]:
    """
    Checks the format of the Awesome List file.
    Enforces the rules for the file format.
    Returns a list of error messages that are found in the file.
    """
    err_msgs = []
    category_title_in_index = []

    # check: must start with `# Awesome List of ...`
    if not lines[0].startswith('# Awesome List of '):
        err_msgs.append(error_message(0, 'missing or incorrect title at the start of the file'))

    anchor = '## '
    min_entries_per_category = 3
    num_segments = 3

    category = ''
    category_line = 0

    check_category_headers(lines, err_msgs, anchor, anchor_re, category_title_in_index, min_entries_per_category, category_title_in_index_re)
    check_entry_formats(lines, err_msgs, num_segments)
    
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