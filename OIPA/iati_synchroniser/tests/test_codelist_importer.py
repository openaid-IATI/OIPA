import unittest

from django.test import TestCase
from lxml.etree import Element
from mock import MagicMock

from geodata.models import Country
from iati_codelists.factory.codelist_factory import AidTypeCategoryFactory, AidTypeFactory
from iati_codelists.models import AidType, AidTypeCategory
from iati_synchroniser.codelist_importer import CodeListImporter


class CodelistImporterTestCase(TestCase):

    """
        Test code list importer functionality
    """

    def setUp(self):
        # XXX: previously, django's 'flush' management command was called to
        # flush the database, but it breaks tests ('no table blah blah exists')
        # and etc., so let's just manually remove objects which were created
        # during previous fixtures.
        # TODO: get rid of fixtures and use factory-boy everywhere.
        Country.objects.all().delete()
        AidType.objects.all().delete()
        AidTypeCategory.objects.all().delete()

    def test_add_aid_type_category_item(self):
        """
        Test adding an AidTypeCategory code list item
        """

        code_text = 'A'
        name_text = 'Budget support'
        description_text = 'For contributions under this category...'

        # use factory to create AidTypeCategory, check if set on model
        aidTypeCategory = AidTypeCategoryFactory.create(
            code=code_text, name=name_text, description=description_text)

        element = Element('AidType-category')
        code = Element('code')
        code.text = code_text

        name = Element('name')
        narrative = Element('narrative')
        narrative.text = name_text
        name.append(narrative)

        description = Element('description')
        narrative = Element('narrative')
        narrative.text = description_text
        description.append(narrative)

        element.extend([code, name, description])

        importer = CodeListImporter()
        importer.add_code_list_item(element, 'AidType-category')

        self.assertEqual(1, AidTypeCategory.objects.count(),
                         "New AidTypeCategory should be added into database")

        self.assertEqual(aidTypeCategory, AidTypeCategory.objects.all()[0],
                         "New AidTypeCategory should match input")

    def test_add_aid_type_item(self):
        """
        Test adding an AidType code list item
        """

        # category should already be in the db
        aidTypeCategory = AidTypeCategoryFactory.create(code='A')

        element = Element('aidType')
        code = Element('code')
        code.text = 'A01'

        name = Element('name')
        narrative = Element('narrative')
        narrative.text = 'General budget support'
        name.append(narrative)

        language = Element('language')
        language.text = 'en'

        category = Element('category')
        category.text = 'A'

        description = Element('description')
        narrative = Element('narrative')
        narrative.text = 'test description'
        description.append(narrative)

        element.extend([code, name, language, category, description])

        importer = CodeListImporter()
        importer.add_code_list_item(element, 'aidType')

        self.assertEqual(1, AidType.objects.count(),
                         "New AidType should be added into database")

        self.assertEqual(aidTypeCategory, AidType.objects.all()[0].category,
                         "New AidType should be added into database")

    def test_add_missing_items(self):

        importer = CodeListImporter()
        importer.add_missing_items()

        self.assertEqual(4, Country.objects.count())

    def test_add_to_model_if_field_exists(self):

        aid_type_item = AidTypeFactory.create(code='A')

        fake_description = 'added_through_add_to_model_if_field_exists'

        importer = CodeListImporter()

        aid_type_item = importer.add_to_model_if_field_exists(
            AidType,
            aid_type_item,
            'description',
            'added_through_add_to_model_if_field_exists')

        # case; should be added
        self.assertEqual(fake_description, aid_type_item.description)

        aid_type_item2 = importer.add_to_model_if_field_exists(
            AidType,
            aid_type_item,
            'non_existing_field_for_this_model',
            'added_through_add_to_model_if_field_exists')

        # case; should not be added
        with self.assertRaises(AttributeError):
            aid_type_item.non_existing_field_for_this_model

        # and the function should still return the item
        self.assertEqual(aid_type_item, aid_type_item2)

    @unittest.skip("Not implemented")
    def test_loop_through_codelists(self):
        return False

    @unittest.skip("Not implemented")
    def test_get_codelist_data(self):
        return False

    def test_synchronise_with_codelists(self):

        importer = CodeListImporter()
        importer.get_codelist_data = MagicMock()
        importer.loop_through_codelists = MagicMock()

        importer.synchronise_with_codelists()

        self.assertEqual(
            len(importer.CODELIST_ITEMS_TO_PARSE),
            importer.get_codelist_data.call_count
        )
        self.assertEqual(len(importer.iati_versions),
                         importer.loop_through_codelists.call_count)

        last_synced_codelist = importer.CODELIST_ITEMS_TO_PARSE[
            len(importer.CODELIST_ITEMS_TO_PARSE) - 1
        ]

        importer.get_codelist_data.assert_called_with(
            name=last_synced_codelist
        )

        importer.loop_through_codelists.assert_called_with('2.03')
