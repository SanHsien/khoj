# Application Packages
from khoj.search_filter.file_filter import FileFilter


# Mock Entry class for testing
class Entry:
    def __init__(self, compiled="", raw="", file=""):
        self.compiled = compiled
        self.raw = raw
        self.file = file


def test_can_filter_no_file_filter():
    # Arrange
    file_filter = FileFilter()
    q_with_no_filter = "head tail"

    # Act
    can_filter = file_filter.can_filter(q_with_no_filter)

    # Assert
    assert can_filter == False


def test_can_filter_non_existent_file():
    # Arrange
    file_filter = FileFilter()
    q_with_filter = 'head file:"nonexistent.org" tail'

    # Act
    can_filter = file_filter.can_filter(q_with_filter)

    # Assert
    assert can_filter == True


def test_can_filter_single_file_include():
    # Arrange
    file_filter = FileFilter()
    q_with_filter = 'head file:"file 1.org" tail'

    # Act
    can_filter = file_filter.can_filter(q_with_filter)

    # Assert
    assert can_filter == True


def test_can_filter_single_file_exclude():
    # Arrange
    file_filter = FileFilter()
    q_with_filter = 'head -file:"1.org" tail'

    # Act
    can_filter = file_filter.can_filter(q_with_filter)

    # Assert
    assert can_filter == True


def test_can_filter_file_with_regex_match():
    # Arrange
    file_filter = FileFilter()
    q_with_filter = 'head file:"*.org" tail'

    # Act
    can_filter = file_filter.can_filter(q_with_filter)

    # Assert
    assert can_filter == True


def test_can_filter_multiple_file_includes():
    # Arrange
    file_filter = FileFilter()
    q_with_filter = 'head tail file:"file 1.org" file:"file2.org"'

    # Act
    can_filter = file_filter.can_filter(q_with_filter)

    # Assert
    assert can_filter == True


def test_get_single_include_file_filter_terms():
    # Arrange
    file_filter = FileFilter()
    q_with_filter_terms = 'head tail file:"/path/to/dir/*.org"'

    # Act
    filter_terms = file_filter.get_filter_terms(q_with_filter_terms)

    # Assert
    assert filter_terms == ["/path/to/dir/*.org"]


def test_get_single_exclude_file_filter_terms():
    # Arrange
    file_filter = FileFilter()
    q_with_filter_terms = 'head tail -file:"file 1.org"'

    # Act
    filter_terms = file_filter.get_filter_terms(q_with_filter_terms)

    # Assert
    assert filter_terms == ["-file 1.org"]


def test_get_single_include_exclude_file_filter_terms():
    # Arrange
    file_filter = FileFilter()
    q_with_filter_terms = 'head tail -file:"file 1.org" file:"/path/to/dir/*.org"'

    # Act
    filter_terms = file_filter.get_filter_terms(q_with_filter_terms)

    # Assert
    assert filter_terms == ["/path/to/dir/*.org", "-file 1.org"]


def test_get_multiple_include_exclude_file_filter_terms():
    # Arrange
    file_filter = FileFilter()
    q_with_filter_terms = (
        'head -file:"file 1.org" file:"file 1.org" file:"/path/to/dir/.*.org" -file:"/path/to/dir/*.org" tail'
    )

    # Act
    filter_terms = file_filter.get_filter_terms(q_with_filter_terms)

    # Assert
    assert filter_terms == ["file 1.org", "/path/to/dir/.*.org", "-file 1.org", "-/path/to/dir/*.org"]


def test_defilter_strips_both_include_and_exclude_file_filters():
    # An exclude filter used to survive defilter() and reach the search text, so
    # `-file:"a.org"` was searched for verbatim -- the filter syntax itself
    # became query terms. WordFilter.defilter already removed both required and
    # blocked terms; this makes FileFilter match.

    # Arrange
    file_filter = FileFilter()

    # Act / Assert
    assert file_filter.defilter("head tail") == "head tail"
    assert file_filter.defilter('head file:"a.org" tail') == "head tail"
    assert file_filter.defilter('head -file:"file 1.org" tail') == "head tail"
    assert file_filter.defilter('head file:"a.org" -file:"b.org" tail') == "head tail"


def arrange_content():
    entries = [
        Entry(compiled="", raw="First Entry", file="file 1.org"),
        Entry(compiled="", raw="Second Entry", file="file2.org"),
        Entry(compiled="", raw="Third Entry", file="file 1.org"),
        Entry(compiled="", raw="Fourth Entry", file="file2.org"),
    ]

    return entries
