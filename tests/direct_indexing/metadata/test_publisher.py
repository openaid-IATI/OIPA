import pytest

from direct_indexing.metadata.publisher import _preprocess_publisher_metadata, index_publisher_metadata

TEST_VAL_1 = "01.01.2019"
TEST_VAL_2 = "01-01-2022T10:00:00.000000"
TEST_VAL_3 = "01.01.2019T10:00:00.000000"
TEST_VAL_4 = "test"
TEST_VAL_1_NEW = "2019-01-01T00:00:00.000000"


def test_index_publisher_metadata(mocker):
    # mock the retrieve function
    mocker.patch('direct_indexing.metadata.publisher.retrieve', return_value='test')
    mocker.patch('direct_indexing.metadata.publisher._preprocess_publisher_metadata', return_value='test')
    mocker.patch('direct_indexing.metadata.publisher.index', return_value='test')
    # assert index_publisher_metadata returns True
    assert index_publisher_metadata() == "test"


def test__preprocess_publisher_metadata(publisher_metadata_sample):
    processed = _preprocess_publisher_metadata(publisher_metadata_sample)
    # Assert a date with periods is converted
    assert processed[0]['publisher_first_publish_date'] == TEST_VAL_1_NEW
    # Assert a date with dashes is not converted
    assert processed[1]['publisher_first_publish_date'] == TEST_VAL_2
    # Assert a date with periods and time is stripped from the time and updated to date with dashes
    assert processed[2]['publisher_first_publish_date'] == TEST_VAL_1_NEW
    # Assert other fields are not changed
    assert processed[0]['other'] == TEST_VAL_4


@pytest.fixture
def publisher_metadata_sample():
    return [
        {
            "publisher_first_publish_date": TEST_VAL_1,
            "other": TEST_VAL_4
        },
        {
            "publisher_first_publish_date": TEST_VAL_2,
            "other": TEST_VAL_4
        },
        {
            "publisher_first_publish_date": TEST_VAL_3,
            "other": TEST_VAL_4
        }
    ]
