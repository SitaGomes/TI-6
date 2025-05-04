from unittest.mock import patch, MagicMock
import pytest
import requests
from scripts.validate.links import (
    find_links_in_text,
    find_links_in_file,
    check_duplicate_links,
    check_if_link_is_working,
    check_if_list_of_links_are_working,
    start_duplicate_links_checker,
    start_links_working_checker,
    main,
    get_host_from_link,
    has_cloudflare_protection
)

# Sample text with links
TEXT_WITH_LINKS = """
This is a sample text with some links:
https://www.example.com
http://example.com
https://example.org
www.example.net
example.com/path
https://www.example.com/path?query=1#anchor
example.com?query=1#anchor
"""

# Sample text without links
TEXT_WITHOUT_LINKS = """
This is a sample text without any links.
No valid URLs to find here.
"""

# Sample readme content
README_CONTENT = """
# Public APIs

A collective list of free APIs for use in software and web development.

## Index
- [Animals](#animals)
- [Anime](#anime)
- [Anti-Malware](#anti-malware)
- [Art & Design](#art--design)
- [Authentication & Authorization](#authentication--authorization)

## Animals
- [Cataas](https://cataas.com/) - Cat as a service (cats pictures and gifs)
- [Dog API](https://dog.ceo/dog-api/) - Random dog images
"""


@pytest.fixture
def sample_file(tmp_path):
    file_path = tmp_path / "sample.md"
    file_path.write_text(README_CONTENT, encoding="utf-8")
    return str(file_path)


# Test find_links_in_text
def test_find_links_in_text_with_links():
    expected_links = [
        "https://www.example.com",
        "http://example.com",
        "https://example.org",
        "www.example.net",
        "example.com/path",
        "https://www.example.com/path?query=1#anchor",
        "example.com?query=1#anchor"
    ]
    assert find_links_in_text(TEXT_WITH_LINKS) == expected_links


def test_find_links_in_text_without_links():
    assert find_links_in_text(TEXT_WITHOUT_LINKS) == []


# Test find_links_in_file
def test_find_links_in_file(sample_file):
    expected_links = [
        "https://cataas.com/",
        "https://dog.ceo/dog-api/"
    ]
    assert find_links_in_file(sample_file) == expected_links


# Test check_duplicate_links
def test_check_duplicate_links_no_duplicates():
    links = ["https://example.com", "https://test.com"]
    has_duplicate, duplicates = check_duplicate_links(links)
    assert has_duplicate is False
    assert duplicates == []


def test_check_duplicate_links_with_duplicates():
    links = ["https://example.com", "https://example.com", "https://test.com"]
    has_duplicate, duplicates = check_duplicate_links(links)
    assert has_duplicate is True
    assert duplicates == ["https://example.com"]


def test_check_duplicate_links_with_normalized_duplicates():
    links = ["https://example.com", "https://example.com/", "https://test.com"]
    has_duplicate, duplicates = check_duplicate_links(links)
    assert has_duplicate is True
    assert duplicates == ["https://example.com"]


# Test check_if_link_is_working
@patch("requests.get")
def test_check_if_link_is_working_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    has_error, error_message = check_if_link_is_working("https://example.com")
    assert has_error is False
    assert error_message == ""


@patch("requests.get")
def test_check_if_link_is_working_4xx(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.headers = {"Server": ""}
    mock_resp.text = ""
    mock_get.return_value = mock_resp

    has_error, error_message = check_if_link_is_working("https://example.com")
    assert has_error is True
    assert error_message == "ERR:CLT: 404 : https://example.com"


@patch("requests.get")
def test_check_if_link_is_working_ssl_error(mock_get):
    mock_get.side_effect = requests.exceptions.SSLError("SSL Error")

    has_error, error_message = check_if_link_is_working("https://example.com")
    assert has_error is True
    assert error_message == "ERR:SSL: SSL Error : https://example.com"


@patch("requests.get")
def test_check_if_link_is_working_connection_error(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError("Connection Error")

    has_error, error_message = check_if_link_is_working("https://example.com")
    assert has_error is True
    assert error_message == "ERR:CNT: Connection Error : https://example.com"


@patch("requests.get")
def test_check_if_link_is_working_cloudflare_protection(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.headers = {"Server": "cloudflare"}
    mock_resp.text = "Please Wait... | Cloudflare"
    mock_get.return_value = mock_resp

    has_error, error_message = check_if_link_is_working("https://example.com")
    assert has_error is False
    assert error_message == ""


@patch("requests.get")
def test_check_if_link_is_working_timeout_error(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectTimeout("Timeout Error")

    has_error, error_message = check_if_link_is_working("https://example.com")
    assert has_error is True
    assert error_message == "ERR:TMO: https://example.com"


@patch("requests.get")
def test_check_if_link_is_working_too_many_redirects(mock_get):
    mock_get.side_effect = requests.exceptions.TooManyRedirects("Too Many Redirects")

    has_error, error_message = check_if_link_is_working("https://example.com")
    assert has_error is True
    assert error_message == "ERR:TMR: Too Many Redirects : https://example.com"


@patch("requests.get")
def test_check_if_link_is_working_request_exception(mock_get):
    mock_get.side_effect = requests.exceptions.RequestException("Request Exception")

    has_error, error_message = check_if_link_is_working("https://example.com")
    assert has_error is True
    assert error_message == "ERR:UKN: Request Exception : https://example.com"


# Test check_if_list_of_links_are_working
@patch("scripts.validate.links.check_if_link_is_working")
def test_check_if_list_of_links_are_working(mock_check_link):
    mock_check_link.side_effect = [
        (False, ""),
        (True, "ERR:CLT: 404 : https://example.com"),
        (False, ""),
    ]

    links = ["https://example.com", "https://test.com", "https://sample.com"]
    errors = check_if_list_of_links_are_working(links)
    assert errors == ["ERR:CLT: 404 : https://example.com"]


# Test start_duplicate_links_checker
def test_start_duplicate_links_checker_no_duplicates(capsys):
    links = ["https://example.com", "https://test.com"]
    with pytest.raises(SystemExit) as e:
        start_duplicate_links_checker(links)
    assert e.value.code == 0
    captured = capsys.readouterr()
    assert "No duplicate links." in captured.out


def test_start_duplicate_links_checker_with_duplicates(capsys):
    links = ["https://example.com", "https://example.com", "https://test.com"]
    with pytest.raises(SystemExit) as e:
        start_duplicate_links_checker(links)
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "Found duplicate links:" in captured.out
    assert "https://example.com" in captured.out


# Test start_links_working_checker
@patch("scripts.validate.links.check_if_list_of_links_are_working")
def test_start_links_working_checker_no_errors(mock_check_links, capsys):
    mock_check_links.return_value = []
    links = ["https://example.com", "https://test.com"]
    with pytest.raises(SystemExit) as e:
        start_links_working_checker(links)
    assert e.value.code == 0
    captured = capsys.readouterr()
    assert "Checking if 2 links are working..." in captured.out


@patch("scripts.validate.links.check_if_list_of_links_are_working")
def test_start_links_working_checker_with_errors(mock_check_links, capsys):
    mock_check_links.return_value = ["ERR:CLT: 404 : https://example.com"]
    links = ["https://example.com", "https://test.com"]
    with pytest.raises(SystemExit) as e:
        start_links_working_checker(links)
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "Apparently 1 links are not working properly. See in:" in captured.out
    assert "ERR:CLT: 404 : https://example.com" in captured.out


# Test main
@patch("scripts.validate.links.find_links_in_file")
@patch("scripts.validate.links.start_duplicate_links_checker")
@patch("scripts.validate.links.start_links_working_checker")
def test_main_with_only_duplicate_links_checker(mock_start_links, mock_start_duplicate, mock_find_links, sample_file):
    mock_find_links.return_value = ["https://example.com", "https://test.com"]
    main(sample_file, True)
    mock_start_duplicate.assert_called_once_with(["https://example.com", "https://test.com"])
    mock_start_links.assert_not_called()


@patch("scripts.validate.links.find_links_in_file")
@patch("scripts.validate.links.start_duplicate_links_checker")
@patch("scripts.validate.links.start_links_working_checker")
def test_main_with_full_check(mock_start_links, mock_start_duplicate, mock_find_links, sample_file):
    mock_find_links.return_value = ["https://example.com", "https://test.com"]
    main(sample_file, False)
    mock_start_duplicate.assert_called_once_with(["https://example.com", "https://test.com"])
    mock_start_links.assert_called_once_with(["https://example.com", "https://test.com"])


# Test get_host_from_link
def test_get_host_from_link():
    assert get_host_from_link("https://example.com/path?query=1#anchor") == "example.com"
    assert get_host_from_link("http://example.com/path?query=1#anchor") == "example.com"
    assert get_host_from_link("https://www.example.com/path?query=1#anchor") == "www.example.com"
    assert get_host_from_link("example.com/path?query=1#anchor") == "example.com"
    assert get_host_from_link("example.com?query=1#anchor") == "example.com"
    assert get_host_from_link("example.com#anchor") == "example.com"


# Test has_cloudflare_protection
def test_has_cloudflare_protection_true():
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.headers = {"Server": "cloudflare"}
    mock_resp.text = "Please Wait... | Cloudflare"
    assert has_cloudflare_protection(mock_resp) is True


def test_has_cloudflare_protection_false():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Server": "nginx"}
    mock_resp.text = "Hello, World!"
    assert has_cloudflare_protection(mock_resp) is False