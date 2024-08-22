import json

import pysolr
import pytest

from direct_indexing.direct_indexing import (
    clear_indices, clear_indices_for_core, drop_removed_data, run, run_dataset_metadata, run_publisher_metadata
)

SOLR = 'pysolr.Solr'


# Test group: test_run
def test_run(mocker):
    # INTEGRATION TEST
    mock_clear = mocker.patch('direct_indexing.direct_indexing.clear_indices')
    mock_index_publisher = mocker.patch('direct_indexing.direct_indexing.index_publisher_metadata')
    mock_index_datasets = mocker.patch('direct_indexing.direct_indexing.index_datasets_and_dataset_metadata')

    run()
    mock_clear.assert_called_once()
    mock_index_publisher.assert_called_once()
    mock_index_datasets.assert_called_once()


# Test group: test_clear_indices
def test_clear_indices_clears_all_indices(mocker):
    # UNIT TEST
    solr_instance_mock = mocker.MagicMock()
    mocker.patch(SOLR, return_value=solr_instance_mock)

    result = clear_indices()
    # Check that the Solr delete method was called
    solr_instance_mock.delete.assert_called_with(q='*:*')
    # Check that `delete` was called 7 times (once for each core)
    assert solr_instance_mock.delete.call_count == 7
    # Check that the output is "success"
    assert result == 'Success'


def test_clear_indices_raises_error(mocker):
    # UNIT TEST
    mocker.patch(SOLR, side_effect=pysolr.SolrError)
    with pytest.raises(pysolr.SolrError):
        clear_indices()


def test_clear_indices_for_core_clears_all_indices(mocker):
    # UNIT TEST
    solr_instance_mock = mocker.MagicMock()
    mocker.patch(SOLR, return_value=solr_instance_mock)

    result = clear_indices_for_core("dataset")
    # Check that the Solr delete method was called
    solr_instance_mock.delete.assert_called_with(q='*:*')
    # Check that `delete` was called once
    assert solr_instance_mock.delete.call_count == 1
    # Check that the output is "success"
    assert result == 'Success'


def test_clear_indices_for_core_raises_error(mocker):
    # UNIT TEST
    mocker.patch(SOLR, side_effect=pysolr.SolrError)
    with pytest.raises(pysolr.SolrError):
        clear_indices_for_core("dataset")


def test_run_publisher_metadata(mocker):
    meta = 'direct_indexing.direct_indexing.index_publisher_metadata'
    mock_index_publisher = mocker.patch(meta, return_value='Success')
    result = run_publisher_metadata()
    assert result == 'Success'
    mock_index_publisher.assert_called_once()

    mocker.patch(meta, return_value='There is an ERROR in result')
    with pytest.raises(ValueError):
        run_publisher_metadata()


def test_run_dataset_metadata(mocker):
    mock = mocker.patch('direct_indexing.direct_indexing.index_datasets_and_dataset_metadata', return_value='Success')
    res = run_dataset_metadata(False, False)
    assert res == 'Success'
    mock.assert_called_once()


def test_drop_removed_data(mocker, tmp_path, requests_mock, fixture_solr_response, fixture_dataset_metadata):
    # Mock settings.SOLR_DATASET to https://test.com
    mocker.patch('direct_indexing.direct_indexing.settings.SOLR_DATASET', 'https://test.com')
    test_url = 'https://test.com/select?fl=name%2Cid%2Ciati_cloud_indexed%2Ciati_cloud_custom&indent=true&q.op=OR&q=*%3A*&rows=10000000'  # NOQA: E501

    # mock settings.BASE_DIR to be tmp_path
    mocker.patch('direct_indexing.direct_indexing.settings.BASE_DIR', tmp_path)
    paths = ['direct_indexing', 'data_sources', 'datasets']
    path = tmp_path / '/'.join(paths)
    path.mkdir(parents=True, exist_ok=True)
    # create 'dataset_metadata.json' with fixture_dataset_metadata
    with open(path / 'dataset_metadata.json', 'w') as f:
        json.dump(fixture_dataset_metadata, f)

    # Mock pysolr.Solr
    solr_instance_mock = mocker.MagicMock()
    mock_solr = mocker.patch(SOLR, return_value=solr_instance_mock)
    # mock solr.search to return a list with 2 elements
    solr_instance_mock.search.return_value = [{}]

    requests_mock.get(test_url, json={'response': {'docs': []}})
    drop_removed_data()
    assert solr_instance_mock.delete.call_count == 0
    # Run drop_removed_data
    requests_mock.get(test_url, json=fixture_solr_response)
    drop_removed_data()

    # assert mock_solr was called 5 times, once for each core including datasets
    assert mock_solr.call_count == 5

    # assert solr's search and delete function is called a total of 10 times
    # 2 times for each of the 5 cores, where 2 times represents drop1 and drop2
    assert solr_instance_mock.search.call_count == 10
    assert solr_instance_mock.delete.call_count == 8


@pytest.fixture
def fixture_solr_response():
    return {
        'response': {
            'docs': [
                {
                    'id': '0001',
                    'name': 'test',
                    'iati_cloud_indexed': True,
                },
                {
                    'id': '0003',
                    'name': 'drop1',
                    'iati_cloud_indexed': True,
                },
                {
                    'id': '0004',
                    'name': 'drop2',
                    'iati_cloud_indexed': True,
                }
            ]
        }
    }


@pytest.fixture
def fixture_dataset_metadata():
    return [
        {
            'id': '0001',
            'name': 'test',
        },
        {
            'id': '0002',
            'name': 'new',
        }
    ]
