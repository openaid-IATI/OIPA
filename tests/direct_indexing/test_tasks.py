import pysolr
import pytest

from direct_indexing.tasks import (
    clear_all_cores, clear_cores_with_name, fcdo_replace_partial_url, revoke_all_tasks, start, subtask_dataset_metadata,
    subtask_publisher_metadata
)


def test_clear_all_cores(mocker):
    # mock direct_indexing.clear_indices
    mock_clear = mocker.patch('direct_indexing.direct_indexing.clear_indices')
    clear_all_cores()
    mock_clear.assert_called_once()


def test_clear_cores_with_name(mocker):
    # mock direct_indexing.clear_indices_for_core
    mock_clear = mocker.patch('direct_indexing.direct_indexing.clear_indices_for_core')
    clear_cores_with_name()
    mock_clear.assert_called_once()


def test_start(mocker):
    # Mock subtask delays
    mock_subtask_publisher_metadata = mocker.patch('direct_indexing.tasks.subtask_publisher_metadata.delay')
    mock_subtask_dataset_metadata = mocker.patch('direct_indexing.tasks.subtask_dataset_metadata.delay')

    # mock datadump_success
    mock_datadump = mocker.patch('direct_indexing.tasks.datadump_success', return_value=False)
    with pytest.raises(ValueError):
        start()
    mock_subtask_publisher_metadata.assert_not_called()

    # mock clear_indices
    mock_datadump.return_value = True
    mocker.patch('direct_indexing.direct_indexing.clear_indices', side_effect=pysolr.SolrError)
    assert start(False) == "Error clearing the direct indexing cores, check your Solr instance."
    mock_subtask_dataset_metadata.assert_not_called()

    res = start(True)
    mock_subtask_publisher_metadata.assert_called_once()
    mock_subtask_dataset_metadata.assert_called_once()
    assert res == "Both the publisher and dataset metadata indexing have begun."


def test_subtask_publisher_metadata(mocker):
    # mock direct_indexing.run_publisher_metadata
    mock_run = mocker.patch('direct_indexing.direct_indexing.run_publisher_metadata', return_value='Success')
    res = subtask_publisher_metadata()
    assert res == 'Success'
    mock_run.assert_called_once()


def test_subtask_dataset_metadata(mocker):
    # mock direct_indexing.run_dataset_metadata
    mock_run = mocker.patch('direct_indexing.direct_indexing.run_dataset_metadata', return_value='Success')
    res = subtask_dataset_metadata(False)
    assert res == 'Success'
    mock_run.assert_called_once()


def test_fcdo_replace_partial_url(mocker, tmp_path, fixture_dataset_metadata):
    testcom = 'https://test.com'
    mock_url = mocker.patch('direct_indexing.tasks.urllib.request.URLopener.retrieve')
    mock_os_remove = mocker.patch('direct_indexing.tasks.os.remove')
    mock_json_dump = mocker.patch('direct_indexing.tasks.json.dump')
    mock_run = mocker.patch('direct_indexing.tasks.direct_indexing.run_dataset_metadata')
    mock_retrieve = mocker.patch('direct_indexing.tasks.retrieve')
    mock_retrieve.return_value = fixture_dataset_metadata.copy()
    mocker.patch('direct_indexing.tasks.settings.DATASET_PARENT_PATH', tmp_path)

    # if a file does not exist, we expect fcdo_replace_partial_url to return 'this file does not exist {...}'
    assert 'this file does not exist' in fcdo_replace_partial_url(testcom, testcom)
    # Make the files for the matching datasets
    path1 = tmp_path / 'iati-data-main/data/test_org/test5.xml'
    path2 = tmp_path / 'iati-data-main/data/test_org/test6.xml'
    path1.parent.mkdir(parents=True)
    path2.parent.mkdir(parents=True, exist_ok=True)
    path1.touch()
    path2.touch()

    mock_retrieve.return_value = fixture_dataset_metadata.copy()
    fcdo_replace_partial_url(testcom, 'https://test_update.com')
    mock_url.assert_called_once()
    assert mock_os_remove.call_count == 1
    mock_json_dump.assert_called_once()
    mock_run.assert_called_once()


def test_revoke_all_tasks(mocker):
    # Assert app.control.purge was called
    mock_purge = mocker.patch('direct_indexing.tasks.app.control.purge')
    revoke_all_tasks()
    mock_purge.assert_called_once()


@pytest.fixture
def fixture_dataset_metadata():
    return [
        {},  # one empty dataset
        {  # one without resources
            'name': 'test1',
            'organization': {},
        },
        {  # one with no name
            'resources': [],
            'organization': {},
        },
        {  # one with no organization
            'resources': [],
            'name': 'test2',
        },
        {  # one with no url in resources
            'resources': [{}],
            'name': 'test3',
            'organization': {},
        },
        {  # one with no hash in resources
            'resources': [{'url': 'https://test.com/1'}],
            'name': 'test3',
            'organization': {},
        },
        {  # one with a mismatching url in resources
            'resources': [{'url': 'https://mismatch.com/1', 'hash': 'test321'}],
            'name': 'test4',
            'organization': {'name': 'test_org'},
        },
        {  # one with a matching url in resources
            'resources': [{'url': 'https://test.com/1', 'hash': 'test123'}],
            'name': 'test5',
            'organization': {
                'name': 'test_org',
            },
        }
    ]
