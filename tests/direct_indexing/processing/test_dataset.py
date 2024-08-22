import xml.etree.ElementTree as ET

import pytest

from direct_indexing.processing.dataset import (
    convert_and_save_xml_to_processed_json, dataset_subtypes, fun, index_dataset, index_subtypes, json_filepath
)

TEST_PATH = '/test/path/test.json'
TEST_JSON = 'test.json'
INDEX_SUCCESS = 'Successfully indexed'


def test_fun(mocker):
    validation_status = 'dataset.extras.validation_status'
    # mock cu.currencies
    mock_currencies = mocker.patch('direct_indexing.processing.dataset.cu.Currencies')
    # mock cu.codelist
    mock_codelist = mocker.patch('direct_indexing.processing.dataset.codelists.Codelists')
    # mock clean_dataset_metadata
    mock_clean = mocker.patch('direct_indexing.processing.dataset.clean_dataset_metadata')
    # mock get_dataset_filepath
    mock_filepath = mocker.patch('direct_indexing.processing.dataset.get_dataset_filepath')
    # mock get_dataset_version_validity
    mock_validity = mocker.patch('direct_indexing.processing.dataset.get_dataset_version_validity', return_value='Valid')  # NOQA: 501
    # mock get_dataset_filetype
    mock_filetype = mocker.patch('direct_indexing.processing.dataset.get_dataset_filetype')
    # mock custom_fields.get_custom_metadata
    mock_metadata = mocker.patch('direct_indexing.processing.dataset.custom_fields.get_custom_metadata')
    # mock index_dataset
    mock_index_ds = mocker.patch('direct_indexing.processing.dataset.index_dataset', return_value=(True, INDEX_SUCCESS, True))  # NOQA: 501
    # mock index
    mock_index = mocker.patch('direct_indexing.processing.dataset.index', return_value=INDEX_SUCCESS)
    # mock Solr
    mock_solr = mocker.patch('direct_indexing.processing.dataset.Solr')
    mock_metadata.return_value = {validation_status: 'Critical'}

    fun({}, False)
    # First test if all initial functions are called
    mock_currencies.assert_called_once()
    mock_codelist.assert_called_once()
    mock_clean.assert_called_once()
    mock_filepath.assert_called_once()
    mock_validity.assert_called_once()
    mock_filetype.assert_called_once()
    mock_metadata.assert_called_once()
    # assert mock_solr was not called
    mock_solr.assert_not_called()
    # assert mock index_dataset was not called
    mock_index_ds.assert_not_called()
    # assert mock index was called
    mock_index.assert_called_once()

    # Test that index_dataset is called if the dataset is considered valid
    mock_metadata.return_value = {validation_status: 'Valid'}
    fun({}, True)
    mock_index_ds.assert_called_once()
    assert mock_solr.call_count == 4


def test_index_dataset(mocker):
    convert_save = 'direct_indexing.processing.dataset.convert_and_save_xml_to_processed_json'
    # mock convert_and_save_xml_to_processed_json, index_to_core
    mock_convert = mocker.patch(convert_save, return_value=(False, False, "No JSON Path found"))  # NOQA: 501
    mock_index = mocker.patch('direct_indexing.processing.dataset.index_to_core', return_value=INDEX_SUCCESS)
    assert index_dataset(None, None, None, None, None) == (False, 'No JSON Path found', False)
    mock_convert.assert_called_once()
    mock_index.assert_not_called()

    mock_convert.return_value = (TEST_PATH, True, "Successfully Indexed")
    assert index_dataset(None, None, None, None, None) == (True, INDEX_SUCCESS, True)
    mock_index.assert_called_once()

    mock_index.return_value = 'Unable to index the processed dataset.'
    assert index_dataset(None, None, None, None, None) == (False, 'Unable to index the processed dataset.', False)

    # Test that if index_dataset raises an exception with error message 'test', it returns a tuple False, 'test'
    mocker.patch(convert_save, side_effect=Exception('test'))  # NOQA: 501
    assert index_dataset(None, None, None, None, None) == (False, 'test', False)


def test_convert_and_save_xml_to_processed_json(mocker, tmp_path, fixture_xml_act, fixture_xml_org):
    # mock recursive_attribute_cleaning, custom_fields.add_all, organisation_custom_fields.add_all, json.dump, dataset_subtypes  # NOQA: 501
    mock_clean = mocker.patch('direct_indexing.processing.dataset.recursive_attribute_cleaning', return_value={})
    mock_add_all = mocker.patch('direct_indexing.processing.dataset.custom_fields.add_all', return_value={})
    mock_add_all_org = mocker.patch('direct_indexing.processing.dataset.organisation_custom_fields.add_all', return_value={})  # NOQA: 501
    mock_json_filepath = mocker.patch('direct_indexing.processing.dataset.json_filepath', return_value=str(tmp_path / TEST_JSON))  # NOQA: 501
    mock_json = mocker.patch('direct_indexing.processing.dataset.json.dump')
    mock_subtypes = mocker.patch('direct_indexing.processing.dataset.dataset_subtypes')
    xml_path = tmp_path / 'test.xml'
    xml_path.write_text("<test>test</test>")

    # Test that if filetype activity, but iati-activities is not in the xml, we return False for data_found
    assert not convert_and_save_xml_to_processed_json(xml_path, 'activity', None, None, None)[0]
    # Test that if filetype activity, and iati-activities is in the xml but no child activity,
    # we return False for data_found
    xml_path.write_text('<iati-activities></iati-activities>')
    assert not convert_and_save_xml_to_processed_json(xml_path, 'activity', None, None, None)[0]
    # Test that if filetype organisation, but iati-organisations is not in the xml, we return False for data_found
    assert not convert_and_save_xml_to_processed_json(xml_path, 'organisation', None, None, None)[0]
    # Test that if filetype organisation, and iati-organisations is in the xml but no child organisation,
    # we return False for data_found
    xml_path.write_text('<iati-organisations></iati-organisations>')
    assert not convert_and_save_xml_to_processed_json(xml_path, 'organisation', None, None, None)[0]

    # mock the value of settings.FCDO_INSTANCE to False
    mocker.patch('direct_indexing.processing.dataset.settings.FCDO_INSTANCE', True)

    # Test that if there is an activity, we call recursive_attribute_cleaning, custom_fields.add_all,
    # json.dump, dataset_subtypes
    xml_path.write_text(fixture_xml_act)
    convert_and_save_xml_to_processed_json(xml_path, 'activity', None, None, None)
    # Assert that recursive_attribute_cleaning is called with the data
    mock_clean.assert_called_once()
    mock_add_all.assert_called_once()
    mock_add_all_org.assert_not_called()
    mock_json_filepath.assert_called_once()
    mock_json.assert_called_once()
    mock_subtypes.assert_not_called()  # not called because FCDO instance is True
    # Test that dataset_subtypes is run if settings.FCDO_INSTANCE is False
    mocker.patch('direct_indexing.processing.dataset.settings.FCDO_INSTANCE', False)
    convert_and_save_xml_to_processed_json(xml_path, 'activity', None, None, None)
    mock_subtypes.assert_called_once()

    # Test that if there is an organisation, we call recursive_attribute_cleaning,
    # organisation_custom_fields.add_all, json.dump, dataset_subtypes
    xml_path.write_text(fixture_xml_org)
    convert_and_save_xml_to_processed_json(xml_path, 'organisation', None, None, None)
    # Assert that recursive_attribute_cleaning is called with the data
    assert mock_clean.call_count == 3  # +2 for the previous tests
    assert mock_add_all.call_count == 2  # not more than 2, because only once for the previous tests
    mock_add_all_org.assert_called_once()
    assert mock_json_filepath.call_count == 3  # +2 for the previous tests
    assert mock_json.call_count == 3  # +2 for the previous tests

    # Assert if json_filepath returns False, the return value is False
    mock_json_filepath.return_value = False
    assert not convert_and_save_xml_to_processed_json(xml_path, 'organisation', None, None, None)[0]

    # Assert if json.dump raises an exception, the return value is None
    mocker.patch('json.dump', side_effect=Exception)
    mock_json_filepath.return_value = str(tmp_path / TEST_JSON)
    assert convert_and_save_xml_to_processed_json(xml_path, 'organisation', None, None, None) == (False, True, "Processed data could not be saved as JSON.")

    # Assert if ET raises a ParseError, the return value is None
    mocker.patch('xml.etree.ElementTree.parse', side_effect=ET.ParseError)
    assert convert_and_save_xml_to_processed_json(None, None, None, None, None) == (None, False, "Unable to read XML file.")


def test_json_filepath(mocker):
    # Assert that given a filepath with any file extension, we return the same filepath with .json appended
    assert json_filepath('/test/path/test.xml') == TEST_PATH
    assert json_filepath('/test/path/test.csv') == TEST_PATH
    assert json_filepath('/test/path') == '/test/path.json'

    # Test that if json_filepath raises an exception, it returns the provided path
    mocker.patch('os.path.splitext', side_effect=Exception)
    assert not json_filepath('/test/path')


def test_dataset_subtypes(mocker):
    # mock activity_subtypes.extract_all_subtypes and index_subtypes
    mock_extract = mocker.patch('direct_indexing.processing.dataset.activity_subtypes.extract_all_subtypes',
                                return_value={})
    mock_index = mocker.patch('direct_indexing.processing.dataset.index_subtypes')

    # Test that if filetype is not activity, we do not call extract_all_subtypes or index_subtypes
    dataset_subtypes('organisation', {}, TEST_JSON)
    mock_extract.assert_not_called()
    mock_index.assert_not_called()

    # Test that we call extract_all_subtypes and index_subtypes if filetype is activity
    dataset_subtypes('activity', {}, TEST_JSON)
    mock_extract.assert_called_once()
    mock_extract.assert_called_with({'transaction': [], 'budget': [], 'result': []}, {})
    mock_index.assert_called_once()


def test_index_subtypes(mocker, tmp_path):
    # mock index_to_core and json.dump
    mock_index = mocker.patch('direct_indexing.processing.dataset.index_to_core')
    mock_json = mocker.patch('direct_indexing.processing.dataset.json.dump')
    mock_open = mocker.patch('builtins.open', mocker.mock_open())

    # Test that we don't call index_to_core or json.dump if there are no subtypes
    json_path = tmp_path / 'activity.json'
    subtypes = {}
    index_subtypes(json_path, subtypes)
    mock_index.assert_not_called()
    mock_json.assert_not_called()

    # Assert that we index the result subtype
    subtypes = {'result': {}}
    index_subtypes(json_path, subtypes)
    mock_index.assert_called_once()
    mock_json.assert_called_once()
    mock_open.assert_called_with(str(tmp_path / 'activity_result.json'), 'w')

    # Test if json.dump raises an exception,logging.error is called once
    mock_json.side_effect = Exception
    mock_log = mocker.patch('direct_indexing.processing.dataset.logging.error')
    index_subtypes(json_path, subtypes)
    mock_log.assert_called_once()


@pytest.fixture
def fixture_xml_act():
    return '<iati-activities><iati-activity><iati-identifier>test-org-1</iati-identifier></iati-activity></iati-activities>'  # NOQA: 501


@pytest.fixture
def fixture_xml_org():
    return '<iati-organisations><iati-organisation><ref>test-org</ref></iati-organisation></iati-organisations>'  # NOQA: 501
