import pysolr
import pytest

from direct_indexing.tasks import (
    clear_all_cores, clear_cores_with_name, fcdo_replace_partial_url, index_custom_dataset, remove_custom_dataset,
    revoke_all_tasks, start, subtask_dataset_metadata, subtask_publisher_metadata
)

CLEAR_INDICES = 'direct_indexing.direct_indexing.clear_indices'


def test_clear_all_cores(mocker):
    # mock direct_indexing.clear_indices
    mock_clear = mocker.patch(CLEAR_INDICES)
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
    mock_drop = mocker.patch('direct_indexing.direct_indexing.drop_removed_data')

    # mock datadump_success
    # mock_datadump = mocker.patch('direct_indexing.tasks.datadump_success', return_value=False)
    # with pytest.raises(ValueError):
    #     start()
    # mock_subtask_publisher_metadata.assert_not_called()

    # mock clear_indices
    # mock_datadump.return_value = True
    mocker.patch(CLEAR_INDICES, side_effect=pysolr.SolrError)
    assert start(False) == "Error clearing the direct indexing cores, check your Solr instance."
    mock_subtask_dataset_metadata.assert_not_called()
    mock_drop.assert_not_called()

    res = start(True)
    mock_subtask_publisher_metadata.assert_called_once()
    mock_subtask_dataset_metadata.assert_called_once()
    assert res == "Both the publisher and dataset metadata indexing have begun."

    # Test if drop is true, direct_indexing.drop_removed_data() is called once
    mocker.patch(CLEAR_INDICES, side_effect=None)
    start(False, drop=True)
    mock_drop.assert_called_once()


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


def test_index_custom_dataset(mocker):
    mock_meta = mocker.patch('direct_indexing.tasks.util.create_dataset_metadata')
    mock_copy = mocker.patch('direct_indexing.tasks.util.copy_custom')
    mock_subtask = mocker.patch('direct_indexing.tasks.subtask_process_dataset.delay')

    mock_meta.return_value = {}
    mock_copy.return_value = None
    res = index_custom_dataset('url', 'title', 'name', 'org')
    assert res == 'Success'
    mock_subtask.assert_called_once()
    mock_meta.assert_called_once()

    mock_copy.return_value = 'Error'
    with pytest.raises(ValueError):
        index_custom_dataset('url', 'title', 'name', 'org')

    mock_meta.return_value = 'Error'
    with pytest.raises(ValueError):
        index_custom_dataset('url', 'title', 'name', 'org')


def test_remove_custom_dataset(mocker):
    mock_remove = mocker.patch('direct_indexing.tasks.util.remove_custom')
    mock_remove.return_value = 'Success'
    assert remove_custom_dataset("a", "b", "c") == 'Success'
    mock_remove.assert_called_once()


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
