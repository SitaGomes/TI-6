import pytest
from io import StringIO
from unittest.mock import patch

# Mocked file content for testing
MOCK_FILE_CONTENT = """\
# APIs

### Animals
| [Cats](http://thecatapi.com) | Pictures of cats from Tumblr, Instagram and YouTube | `apiKey` | Yes | Unknown |
| [Dogs](http://thedogapi.com) | Pictures of dogs from Tumblr, Instagram and Pixel | `apiKey` | Yes | Unknown |
| [Birds](http://thebirdapi.com) | Pictures of birds from Tumblr, Instagram and Facebook | `apiKey` | Yes | Unknown |

### Anime
| [AnimeChan](https://github.com/RocktimSaikia/anime-chan) | Anime quotes (over 10k+) | No | Yes | Unknown |
| [MangaDex](https://api.mangadex.org/docs.html) | Manga Database and Community | `apiKey` | Yes | Unknown |

"""


@pytest.fixture
def mock_file():
    with patch("builtins.open", return_value=StringIO(MOCK_FILE_CONTENT)):
        yield


def test_error_message():
    assert error_message(0, "Test message") == "(L001) Test message"
    assert error_message(10, "Another test") == "(L011) Another test"


def test_get_categories_content():
    lines = MOCK_FILE_CONTENT.splitlines()
    categories, category_line_num = get_categories_content(lines)
    
    assert "Animals" in categories
    assert "Anime" in categories
    assert len(categories["Animals"]) == 3
    assert categories["Animals"][0] == "CATS"
    assert category_line_num["Animals"] == 2
    assert category_line_num["Anime"] == 7


def test_check_alphabetical_order():
    lines = MOCK_FILE_CONTENT.splitlines()
    err_msgs = check_alphabetical_order(lines)
    
    assert len(err_msgs) == 0
    
    # Change the order to make it non-alphabetical
    lines[3], lines[4] = lines[4], lines[3]
    err_msgs = check_alphabetical_order(lines)
    
    assert len(err_msgs) == 1
    assert err_msgs[0] == "(L003) Animals category is not alphabetical order"


def test_check_title():
    assert check_title(0, "[Good Title](http://example.com)") == []
    assert check_title(0, "Bad Title") == ["(L001) Title syntax should be \"[TITLE](LINK)\""]
    assert check_title(0, "[Bad API](http://example.com)") == ["(L001) Title should not end with \"... API\". Every entry is an API here!"]


def test_check_description():
    assert check_description(0, "Good description") == []
    assert check_description(0, "bad description") == ["(L001) first character of description is not capitalized"]
    assert check_description(0, "Bad description.") == ["(L001) description should not end with ."]
    assert check_description(0, "A" * 101) == [f"(L001) description should not exceed {max_description_length} characters (currently 101)"]


def test_check_auth():
    assert check_auth(0, "`apiKey`") == []
    assert check_auth(0, "No") == []
    assert check_auth(0, "apiKey") == ["(L001) auth value is not enclosed with `backticks`"]
    assert check_auth(0, "`invalid`") == ["(L001) `invalid` is not a valid Auth option"]


def test_check_https():
    assert check_https(0, "Yes") == []
    assert check_https(0, "No") == []
    assert check_https(0, "Maybe") == ["(L001) Maybe is not a valid HTTPS option"]


def test_check_cors():
    assert check_cors(0, "Yes") == []
    assert check_cors(0, "No") == []
    assert check_cors(0, "Unknown") == []
    assert check_cors(0, "Maybe") == ["(L001) Maybe is not a valid CORS option"]


def test_check_entry():
    segments = ["[Cats](http://thecatapi.com)", "Pictures of cats", "`apiKey`", "Yes", "Unknown"]
    assert check_entry(0, segments) == []
    
    segments = ["Cats", "Pictures of cats", "`apiKey`", "Yes", "Unknown"]
    assert check_entry(0, segments) == [
        "(L001) Title syntax should be \"[TITLE](LINK)\"",
        "(L001) Title should not end with \"... API\". Every entry is an API here!"
    ]
    
    segments = ["[Cats](http://thecatapi.com)", "pictures of cats", "`apiKey`", "Yes", "Unknown"]
    assert check_entry(0, segments) == [
        "(L001) first character of description is not capitalized"
    ]


def test_check_file_format(mock_file):
    lines = MOCK_FILE_CONTENT.splitlines()
    err_msgs = check_file_format(lines)
    
    assert len(err_msgs) == 0
    
    # Add an invalid entry with bad title
    lines.insert(4, "| Bad Title | Pictures of cats | `apiKey` | Yes | Unknown |")
    err_msgs = check_file_format(lines)
    
    assert len(err_msgs) == 1
    assert err_msgs[0] == "(L004) Title syntax should be \"[TITLE](LINK)\""
    
    # Add a new category not in index
    lines.insert(7, "### New Category")
    lines.insert(8, "| [New API](http://newapi.com) | New entry | `apiKey` | Yes | Unknown |")
    err_msgs = check_file_format(lines)
    
    assert len(err_msgs) == 2
    assert err_msgs[1] == "(L007) category header (New Category) not added to Index section"
    
    # Remove an index entry to simulate missing index
    lines[0] = "# APIs"
    lines[1] = "### Blah"
    lines[2] = "| [Blah](http://blah.com) | Blah entry | `apiKey` | Yes | Unknown |"
    err_msgs = check_file_format(lines)
    
    assert len(err_msgs) == 3
    assert err_msgs[2] == "(L006) Animals category does not have the minimum 3 entries (only has 1)"


def test_main(capsys, mock_file):
    with patch("sys.argv", ["script_name", "mock_file.md"]):
        main("mock_file.md")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""
    
    # Modify the mock file to include errors
    with patch("builtins.open", return_value=StringIO("| Bad Title | Pictures of cats | `apiKey` | Yes | Unknown |")):
        with patch("sys.argv", ["script_name", "mock_file.md"]):
            with pytest.raises(SystemExit) as e:
                main("mock_file.md")
                assert e.value.code == 1
            captured = capsys.readouterr()
            assert captured.out == ""
            assert captured.err != ""


if __name__ == "__main__":
    pytest.main()