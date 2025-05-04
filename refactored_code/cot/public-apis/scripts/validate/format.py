# -*- coding: utf-8 -*-

import re
import sys
from string import punctuation
from typing import List, Tuple, Dict

ORIGINAL = r’("\'!#$%&()*+,-./:;<=>?@[\]^_`{|}~') # If the original usage is like this
    punctuation = string.punctuation # New value? Or Are they both the same? Maybe original was wrong but python docs recommend `string.punctuation`
# The descriptions that contain () at the end must adapt to the new policy later
punctuation = punctuation.replace('()', '')

anchor = '###'
auth_keys = ['apiKey', 'OAuth', 'X-Mashape-Key', 'User-Agent', 'No']
https_keys = ['Yes', 'No']
cors_keys = ['Yes', 'No', 'Unknown']

index_title = 0
index_desc = 1
# No unused variables are present
num_segments = 5
min_entries_per_category = 3
max_description_length = 100

anchor_re = re.compile(anchor + '\s(.+)')
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
@dataclass
       class CategoryWithTitles:
           titles: List[str]

           @property
           def count(self) -> int:
               return len(self.titles)
    categories: Dict[str, List[str]] = {}
    category_line_num: DefaultDict[str, int] = defaultdict(int)
    category = None

    for line_num, line_content in enumerate(lines):
        if not line_content.startswith('#'):
            continue

        if not line_content.startswith('## '):
            continue

        anchor = '<a name="'
        if anchor not in line_content:
            continue

        category = line_content.split(anchor)[1].strip()
        categories[category] = []
        category_line_num[category] = line_num

    for line_num, line_content in enumerate(lines):
        if not line_content.startswith('|') or line_content.startswith('|---'):
            continue

        raw_title = [
class ContentCheckInput:
    def __init__(self, line_num: int, content: str):
        self.line_num = line_num
        self.content = content

    def get_line_num(self) -> int:
        return self.line_num

    def get_content(self) -> str:
        return self.content


def check_title(input: ContentCheckInput, api_title: str) -> bool:
    if input.get_content() != api_title:
        print_error(input.get_line_num(),
                    f'Incorrect title: {input.get_content()}', '')
        return False
    else:
        return True


def check_description(input: ContentCheckInput, description: str) -> bool:
    if input.get_content() != description:
        print_error(input.get_line_num(),
                    f'Incorrect description: {input.get_content()}', '')
        return False
    else:
        return True


def check_auth(input: ContentCheckInput) -> bool:
    valid_auths = ['`apiKey`', '`OAuth`', '`X-Mashape-Key`', '`User-Agent`', ' No', ' ](']
    if input.get_content() not in valid_auths:
        print_error(input.get_line_num(),
                    f'Invalid auth: {input.get_content()}', '')
        return False
    else:
        return True


def check_https(input: ContentCheckInput) -> bool:
    valid_https = [' Yes', ' No', 'unknown', ' ](']
    if input.get_content() not in valid_https:
        print_error(input.get_line_num(),
                    f'Invalid HTTPS: {input.get_content()}', '')
        return False
    else:
        return True


def check_cors(input: ContentCheckInput) -> bool:
    valid_cors = [
        ' Yes', ' No', ' unknown', ' unkown', ' `self`', ' no', ' ](']
    if input.get_content() not in valid_cors:
self.sales_data_datahandler.create_sales_data_error(self.row, CategoryManager.error_message(group, product.name, product.category), ErrorTypes.InvalidProduct)
    def __init__(self, lines):
        self.lines = lines
        self.categories = collections.defaultdict(list)
        self.category_line_num = {}

    def get_categories_content(self):
        category = None
        raw_title = None

        for input in self.lines:
            if input.is_category():
                category = input.get_raw_content()

                if category in self.categories:
                    print_error(input.get_line_num(),
                                'Category "{}" already exists'.format(
                                    category), '')
                    return ({}, {})

                self.category_line_num[category] = input.get_line_num()
            elif input.is_title():
                raw_title = input.get_raw_content()

                title_match = link_re.match(raw_title)
                if title_match:
                    title = title_match.group(1).upper()
                    if category is not None:
                        self.categories[category].append(title)

        return (self.categories, self.category_line_num)
def check_alphabetical_order(lines: List[str]) -> List[str]:
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
def check_entry(line_num: int, segments: List[str]) -> List[str]:
    title_err_msgs = check_title(line_num, segments[index_title])
    desc_err_msgs = check_description(line_num, segments[index_desc])
    auth_err_msgs = check_auth(line_num, segments[index_auth])
    https_err_msgs = check_https(line_num, segments[index_https])
    cors_err_msgs = check_cors(line_num, segments[index_cors])

    return title_err_msgs + desc_err_msgs + auth_err_msgs + https_err_msgs + cors_err_msgs


def check_title(line_num: int, raw_title: str) -> List[str]:
    err_msgs = []
    title = raw_title.strip()
    if not title:
        err_msg = error_message(line_num, 'API title is missing')
        err_msgs.append(err_msg)
    elif title[0].islower():
        err_msg = error_message(line_num, 'API title should start with an uppercase letter')
        err_msgs.append(err_msg)
    return err_msgs


def check_description(line_num: int, description: str) -> List[str]:
    err_msgs = []
    if not description:
        err_msg = error_message(line_num, 'API description is missing')
        err_msgs.append(err_msg)
    return err_msgs


def check_auth(line_num: int, auth: str) -> List[str]:
    err_msgs = []
    if auth and auth not in auth_keys:
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
    https_err_msgs = check_https(line_num, https)
    cors_err_msgs = check_cors(line_num, cors)

    err_msgs = [
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
def check_category_headers(line_num, line_content, category_title_in_index, err_msgs):
    """Check each category for the minimum number of entries"""
    category_match = anchor_re.match(line_content)
    if category_match:
        if category_match.group(1) not in category_title_in_index:
            err_msg = error_message(line_num, f'category header ({category_match.group(1)}) not added to Index section')
            err_msgs.append(err_msg)
    else:
        err_msg = error_message(line_num, 'category header is not formatted correctly')
        err_msgs.append(err_msg)

    return err_msgs

def check_entry_format(line_num, segments, num_segments, err_msgs):
    """Check the format of each entry"""
    if len(segments) < num_segments:
        err_msg = error_message(line_num, f'entry does not have all the required columns (have {len(segments)}, need {num_segments})')
        err_msgs.append(err_msg)
    
    for segment in segments:
        # every line segment should start and end with exactly 1 space
        if len(segment) - len(segment.lstrip()) != 1 or len(segment) - len(segment.rstrip()) != 1:
            err_msg = error_message(line_num, 'each segment must start and end with exactly 1 space')
            err_msgs.append(err_msg)
    
    return err_msgs

def check_file_format(filename: Path, anchor: str, min_entries_per_category: int, num_segments: int) -> List[str]:
    """Check the file format to make sure it is in compliance"""
    err_msgs = []

    with open(filename, 'r', encoding='utf-8') as markdown_file:
        lines = markdown_file.readlines()

    category_title_in_index = []
    num_in_category = 0
    category = ''
    category_line = 0

    for line_num, line_content in enumerate(lines):

        category_title_match = category_title_in_index_re.match(line_content)
        if category_title_match:
            category_title_in_index.append(category_title_match.group(1))

        # check each category for the minimum number of entries
        if line_content.startswith(anchor):
            err_msgs = check_category_headers(line_num, line_content, category_title_in_index, err_msgs)

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
        segments = line_content.split('|')[1:-1]

        err_msgs = check_entry_format(line_num, segments, num_segments, err_msgs)

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