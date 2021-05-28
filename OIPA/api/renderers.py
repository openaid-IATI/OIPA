#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import ast
import io
from collections import OrderedDict

import unicodecsv as csv
import xlsxwriter
from django.conf import settings
from django.utils import six
from lxml import etree
from lxml.builder import E
from rest_framework.renderers import BaseRenderer
from rest_framework.utils.serializer_helpers import ReturnDict, ReturnList
from rest_framework_csv.renderers import CSVRenderer
from six import BytesIO

from api.iati.elements import ElementReference
from api.iati.references import (
    ActivityDateReference, ActivityReference, ActivityScopeReference,
    ActivityStatusReference, BudgetReference, CapitalSpendReference,
    CollaborationTypeReference, ConditionsReference, ContactInfoReference,
    CountryBudgetItemsReference, CrsAddReference, DefaultAidTypeReference,
    DefaultCurrencyOrgReference, DefaultFinanceTypeReference,
    DefaultFlowTypeReference, DefaultTiedStatusReference, DescriptionReference,
    DocumentLinkOrgReference, DocumentLinkReference, FssReference,
    HumanitarianScopeReference, LastUpdatedDatetimeOrgReference,
    LegacyDataReference, LocationReference, NameOrgReference,
    OrganisationReference, OtherIdentifierReference, ParticipatingOrgReference,
    PlannedDisbursementReference, PolicyMarkerReference,
    RecipientCountryBudgetOrgReference, RecipientCountryReference,
    RecipientOrgBudgetOrgReference, RecipientRegionBudgetOrgReference,
    RecipientRegionReference, RelatedActivityReference,
    ReportingOrgOrgReference, ReportingOrgReference, ResultReference,
    SectorReference, TagReference, TitleReference, TotalBudgetOrgReference,
    TotalExpenditureOrgReference, TransactionReference, XmlLangReference
)

# TODO: Make this more generic - 2016-01-21


class XMLRenderer(BaseRenderer):
    """
    Renderer which serializes to XML.
    """

    media_type = 'application/xml'
    format = 'xml'
    charset = 'UTF-8'
    root_tag_name = 'iati-activities'
    item_tag_name = 'iati-activity'
    version = '2.02'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Renders `data` into serialized XML.
        """

        if data is None:
            return ''

        if 'results' in data:
            data = data['results']

        xml = E(self.root_tag_name)
        xml.set('version', self.version)

        if hasattr(settings, 'EXPORT_COMMENT'):
            xml.append(etree.Comment(getattr(settings, 'EXPORT_COMMENT')))

        self._to_xml(xml, data, parent_name=self.item_tag_name)

        return etree.tostring(xml, encoding=self.charset, pretty_print=True)

    def _to_xml(self, xml, data, parent_name=None):
        if isinstance(data, (list, tuple)):
            for item in data:
                self._to_xml(etree.SubElement(
                    xml, parent_name.replace('_', '-')), item)

        elif isinstance(data, dict):
            attributes = []

            if hasattr(data, 'xml_meta'):
                attributes = list(set(data.xml_meta.get(
                    'attributes', list())) & set(data.keys()))

                for attr in attributes:

                    renamed_attr = attr.replace(
                        'xml_lang',
                        '{http://www.w3.org/XML/1998/namespace}lang'
                    ).replace('_', '-')

                    value = data[attr]
                    if value is not None:
                        xml.set(
                            renamed_attr,
                            six.text_type(value).lower() if isinstance(
                                value, bool
                            ) else six.text_type(value))

            for key, value in six.iteritems(data):

                if key in attributes:
                    continue

                if key == 'text':
                    self._to_xml(xml, value)
                elif isinstance(value, list):
                    self._to_xml(xml, value, parent_name=key)
                else:
                    # TODO remove this ugly hack by adjusting the
                    # resultindicatorperiod actual / target models. 30-08-16
                    # currently actuals are stored on the
                    # resultindicatorperiod, hence we need to remove empty
                    # actuals here.
                    if key in ['actual', 'target']:
                        if list(value.items())[0][0] != 'value':
                            continue

                    self._to_xml(etree.SubElement(
                        xml, key.replace('_', '-')), value)

        elif data is None:
            pass

        else:
            xml.text = six.text_type(data)
            pass


# TODO: test this, see: #958
class PaginatedCSVRenderer(CSVRenderer):
    results_field = 'results'
    header = []

    def __init__(self, *args, **kwargs):
        super(PaginatedCSVRenderer, self).__init__(*args, **kwargs)
        self.writer_opts = {
            'quoting': csv.QUOTE_ALL,
            'quotechar': '"',
            'delimiter': ';'
        }

        self.rows = []
        # self.row = []
        # self.paths = {}
        self.headers = {}
        self.break_down_by = None
        self.exceptional_fields = None
        self.selectable_fields = ()
        self.default_fields = ()

    def render(self, data, *args, **kwargs):
        # TODO: this is probably a bug in DRF, might get fixed later then
        # need to update this - 2017-04-03
        actual_kwargs = args[1].get('kwargs', {})

        # So basically when exporting a list view we need to only
        # parse what we get from the 'results' field of the response
        # otherwise what we see in the file, will not make much sense
        # so we do a check here to determine if the response is a list
        # response or a detail response, by checking if there's a
        # 'pk' or a 'iati_identifier'
        # one of the exceptions is for the 'activity/{id}/transactions'
        # because it returns a list so we have a check for it here as well
        if 'pk' not in actual_kwargs \
            and 'iati_identifier' not in actual_kwargs or \
            'pk' in actual_kwargs and \
                'transactions' in args[1]['request']._request.path and 'activity' in args[1]['request']._request.path:  # NOQA: E501
            data = data.get(self.results_field, [])

        # these lines is just for internal testing purposes
        # to transforms current json object
        # into format suitable for testing majority of cases.
        # data[0]['transaction_types'].append({'transaction_type':'12', 'dsum': 300000.00}) # NOQA: E501
        # data[0]['recipient_countries'].append({'id': 5, 'country': {'url': 'test url', 'code': 'IQ', 'name': 'test name'}, 'percentage': 50}) # NOQA: E501

        # Get the reference view
        view = args[1].get('view', {})

        # Check if it's the instance of view type
        if not isinstance(view, dict):

            # Get a view's class name
            view_class_name = type(view).__name__

            # for exceptional fields we should perform different logic
            # then for other selectable fields
            self.exceptional_fields = view.exceptional_fields
            # Get headers with their paths

            # Break down Activity by defined column in ActivityList class
            self.break_down_by = view.break_down_by

            self.selectable_fields = view.selectable_fields

            if view.fields == ():
                fields = tuple(view.serializer_fields)
            else:
                fields = view.fields

            self.default_fields = list(set(view.fields) - set(self.selectable_fields))  # NOQA: E501

            utils = UtilRenderer()
            utils.exceptional_fields = view.exceptional_fields
            utils.break_down_by = view.break_down_by
            utils.selectable_fields = view.selectable_fields
            utils.default_fields = self.default_fields

            if view_class_name in ['ActivityList', 'ActivityDetail',
                                   'ActivityDetailByIatiIdentifier']:

                activity_data = utils.adjust_transaction_types(data, 'transaction_types')  # NOQA: E501
                data = activity_data['data']
                selectable_headers = activity_data['selectable_headers']
                activity_data.pop('selectable_headers', None)
                self.rows, self.headers = utils.create_rows_headers(data, view.csv_headers, selectable_headers, fields, False)  # NOQA: E501

            elif view_class_name in ['TransactionList', 'TransactionDetail']:

                transactions_data = utils.group_data(data, view, 'iati_identifier', 'transactions')  # NOQA: E501
                selectable_headers = transactions_data['selectable_headers']  # NOQA: E501
                transactions_data.pop('selectable_headers', None)
                self.rows, self.headers = utils.create_rows_headers(list(transactions_data.values()), view.csv_headers, selectable_headers, view.fields, True)  # NOQA: E501

            elif view_class_name in ['LocationList', 'LocationDetail']:

                location_data = utils.group_data(data, view, 'iati_identifier', 'locations')  # NOQA: E501
                selectable_headers = location_data['selectable_headers']
                location_data.pop('selectable_headers', None)
                self.rows, self.headers = utils.create_rows_headers(list(location_data.values()), view.csv_headers, selectable_headers, view.fields, True)  # NOQA: E501

            elif view_class_name in ['BudgetList', 'BudgetDetail']:

                budget_data = utils.group_data(data, view, 'iati_identifier', 'budgets')  # NOQA: E501
                selectable_headers = budget_data['selectable_headers']
                budget_data.pop('selectable_headers', None)
                self.rows, self.headers = utils.create_rows_headers(list(budget_data.values()), view.csv_headers, selectable_headers, view.fields, True)  # NOQA: E501

            elif view_class_name in ['ResultList', 'ResultDetail']:

                result_data = utils.group_data(data, view, 'iati_identifier', 'results')  # NOQA: E501
                selectable_headers = result_data['selectable_headers']
                result_data.pop('selectable_headers', None)
                self.rows, self.headers = utils.create_rows_headers(list(result_data.values()), view.csv_headers, selectable_headers, view.fields, True)  # NOQA: E501

        # writing to the csv file using unicodecsv library
        output = io.BytesIO()
        writer = csv.writer(output, delimiter=';', encoding=settings.DEFAULT_CHARSET)  # NOQA: E501
        writer.writerow(list(self.headers.keys()))
        writer.writerows(self.rows)
        return output.getvalue()
        # this is old render call.
        # return super(PaginatedCSVRenderer, self).render(rows, renderer_context={'header':['aaaa','sssss','ddddd','fffff','gggggg']}, **kwargs) # NOQA: E501


class OrganisationXMLRenderer(XMLRenderer):
    root_tag_name = 'iati-organisations'
    item_tag_name = 'iati-organisation'


class UtilRenderer(object):

    def __init__(self, *args, **kwargs):
        self.rows = []
        self.row = []
        self.paths = {}
        self.headers = {}
        self.break_down_by = None
        self.exceptional_fields = None
        self.selectable_fields = ()
        self.default_fields = ()

    def create_rows_headers(self, data, csv_headers, selectable_headers, fields, add_index):  # NOQA: E501

        available_headers = list(csv_headers.keys()) + list(
            set(selectable_headers) - set(list(csv_headers.keys())))
        headers = {}
        for header in available_headers:
            if header in list(csv_headers.keys()):
                headers[header] = csv_headers[header]['header']
            else:
                headers[header] = header.split('.')[0]
        # Get headers with their paths
        self.headers = self._get_headers(headers, fields, add_index)

        if not isinstance(data, list):
            data = [data]

        # iterate trough all Activities
        for item in data:
            self.paths = {}
            # Get a number of repeated rows caused by breaking down
            # activity with the defined column.
            repeated_rows = len(item[self.break_down_by])
            repeated_rows = 1 if repeated_rows == 0 else repeated_rows
            # recursive function to get all json paths
            # together with the corresponded values
            self.paths = self._go_deeper(item, '', self.paths)

            self._render(repeated_rows)

        return self.rows, self.headers

    def group_data(self, data, view, group_by_field, transform_field):

        if not isinstance(data, list):
            data = [data]

        group_data = {}
        default_fields = list(set(view.fields) - set(view.selectable_fields))
        # iterate trough all Activities
        for item in data:
            # activity with the defined column.
            group_by_value = item[group_by_field]
            tmp_data = {}
            if group_by_value not in group_data:
                group_data[group_by_value] = {}
                group_data[group_by_value][transform_field] = []
                for field in default_fields:
                    group_data[group_by_value][field] = list() if field not in item else item[field]  # NOQA: E501

            for field in list(view.selectable_fields):
                tmp_data[field] = item[field]

            group_data[group_by_value][transform_field].append(tmp_data)

        data_count = [0]
        tmp_data = []
        for item in list(group_data.values()):
            data_count.append(len(item[transform_field]))
            for value in list(item[transform_field]):

                tmp_paths = {}
                tmp_item = {transform_field: value}
                tmp_paths = self._go_deeper(tmp_item, '', tmp_paths)
                tmp_data = tmp_data + list(set(tmp_paths.keys()) - set(tmp_data))  # NOQA: E501

        group_data['selectable_headers'] = tmp_data
        if len(self.exceptional_fields) > 0 and transform_field in self.exceptional_fields[0]:  # NOQA: E501
            self.exceptional_fields[0][transform_field] = list(range(1, max(data_count) + 1))  # NOQA: E501

        return group_data

    def _render(self, repeated_rows):

        # iterate trough activity data and make appropriate row values
        # with the respect to the headers and breaking down column
        for i in range(repeated_rows):
            self.row = []
            for header_key in list(self.headers.keys()):
                header_values = self.headers[header_key]
                value = ''
                for header_value in header_values:
                    # in case that we did not find the value
                    # for the particular json path, set empty string
                    # for the column value.
                    if header_value not in list(self.paths.keys()):
                        continue
                    else:
                        tmp_value = self.paths[header_value]
                        if isinstance(tmp_value, list):
                            tmp_value = list(map(str, tmp_value))
                            index = int(header_key.split('.')[1]) if len(header_key.split('.')) == 2 else -1  # NOQA: E501
                            if self.break_down_by in header_value:
                                value = value + str(tmp_value[i]) + ';'
                            elif index < 0:
                                value = value + str(';'.join(tmp_value)) \
                                        + ';'
                            else:
                                if len(tmp_value) >= index + 1:
                                    value = value + str(tmp_value[index]) + ';'

                        # In case we did find the value for the particular
                        # json path and this property value has not related
                        # to breaking down column.
                        else:
                            value = value + str(tmp_value) + ';'
                self.row.append(value)
            self.rows.append(self.row)

    def _go_deeper(self, node, path, paths):

        if isinstance(node, dict):
            for key, value in node.items():
                current_path = path + key + '.'
                paths = self._go_deeper(value, current_path, paths)

        elif isinstance(node, list):
            for value in node:
                paths = self._go_deeper(value, path, paths)
        else:
            path = path[:-1]
            if path in paths:
                if not isinstance(paths[path], list):
                    paths[path] = [paths[path]]
                paths[path].append(0 if node is None else node)
            else:
                paths[path] = 'null' if node is None else node

        return paths

    def _get_headers(self, available_headers, fields, add_index=True):
        headers = {}
        for field in fields:
            for path, header_name in available_headers.items():
                # field name should be first term in path string
                if field in path.split('.')[0]:
                    if header_name not in headers:
                        headers[header_name] = list()
                    headers[header_name].append(path)

        # adjust headers with the possibility of having exceptional fields
        for exceptional_field in self.exceptional_fields:
            for key, value in exceptional_field.items():
                field_name = key.split('.')[0]
                if field_name in list(headers.keys()):
                    path = headers[field_name]
                    headers.pop(field_name, None)
                    for index, exceptional_header_suffix in enumerate(value):
                        if len(self.selectable_fields) > 0:
                            header_name = field_name + '_' + str(exceptional_header_suffix) + ('.' + str(index) if add_index else '')  # NOQA: E501
                            tmp_path = path if add_index else [field_name + '_' + str(exceptional_header_suffix)]  # NOQA: E501
                            headers[header_name] = tmp_path
        return headers

    def _adjust_item(self, item, csv_headers, item_key):

        for index, transaction in enumerate(item[item_key]):
            tmp_paths = {}
            tmp_value = ''
            tmp_paths = self._go_deeper(transaction, '', tmp_paths)

            for path in list(csv_headers.keys()):
                for tmp_path in tmp_paths:
                    if path == tmp_path:
                        tmp_value = tmp_value + str(tmp_paths[path]) + ';'
                        if csv_headers[path]['header'] is None:
                            item[item_key + '_' + str(index + 1)] = tmp_value
                        else:
                            item[path] = tmp_value

        item.pop(item_key, None)
        return item

    def adjust_transaction_types(self, data, item_key):

        tmp_data = []
        if not isinstance(data, list):
            if item_key in data:
                for transaction in data[item_key]:
                    data[item_key + '_' + str(transaction[
                                                'transaction_type'])] = transaction['dsum']  # NOQA: E501

            for field in self.selectable_fields:
                tmp_paths = {}
                try:
                    tmp_item = {field: data[field]}
                except KeyError:
                    pass
                tmp_paths = self._go_deeper(tmp_item, '', tmp_paths)
                tmp_data = tmp_data + list(set(tmp_paths.keys()) - set(tmp_data))  # NOQA: E501

            if item_key in data:
                data.pop(item_key, None)
                data['selectable_headers'] = tmp_data

        else:
            for item in data:

                if item_key in item:
                    for transaction in item[item_key]:
                        item[item_key + '_' + str(transaction['transaction_type'])] = transaction['dsum']  # NOQA: E501

                for field in self.selectable_fields:
                    tmp_paths = {}
                    try:
                        tmp_item = {field: item[field]}
                    except KeyError:
                        pass
                    tmp_paths = self._go_deeper(tmp_item, '', tmp_paths)
                    tmp_data = tmp_data + list(set(tmp_paths.keys()) - set(tmp_data))  # NOQA: E501

                if item_key in item:
                    item.pop(item_key, None)
                    item['selectable_headers'] = tmp_data

        return {'data': data, 'selectable_headers': tmp_data}


# XXX: file name is always 'download' and it should probably be set per-view
# TODO: test this, see: #958
class XlsRenderer(BaseRenderer):
    media_type = 'application/vnd.ms-excel'
    results_field = 'results'
    render_style = 'xls'
    format = 'xls'

    def __init__(self):
        self.wb = None
        self.ws = None
        self.header_style = None
        self.cell_style = None
        self.column_width = 0
        self.requested_fields = None

        self.rows = []
        self.row = []
        self.paths = {}
        self.headers = {}
        self.break_down_by = None
        self.exceptional_fields = None
        self.selectable_fields = ()
        self.default_fields = ()

        # So we gonna store the columns seperately
        # Index is the column number, value the column name
        self.columns = []

        # Then we gonna store the cells seperately,
        # in a weird dictionary matrix thingy
        self.cells = {}

        # Cause each column might have different widths,
        # and we need to store each columns widths
        # In an array to make checks if a longer values has not entered
        self.col_widths = []

        # Saves the previous column name
        # This is used for aditional column values that might not be found
        # in the first item of the results
        self.prev_col_name = False

    def render(self, data, media_type=None, renderer_context=None):
        try:
            self.requested_fields = ast.literal_eval(
                renderer_context['request'].query_params['export_fields'])
        except KeyError:
            pass

        actual_kwargs = renderer_context.get('kwargs', {})

        # So basically when exporting a list view we need to only
        # parse what we get from the 'results' field of the response
        # otherwise what we see in the file, will not make much sense
        # so we do a check here to determine if the response is a list
        # response or a detail response, by checking if there's a
        # 'pk' or a 'iati_identifier'
        # one of the exceptions is for the 'activity/{id}/transactions'
        # because it returns a list so we have a check for it here as well
        if 'pk' not in actual_kwargs \
                and 'iati_identifier' not in actual_kwargs or\
                'pk' in actual_kwargs and \
                'transactions' in renderer_context['request']._request.path and 'activity' in renderer_context['request']._request.path:  # NOQA: E501
            data = data.get(self.results_field, [])

        # Create an in-memory output file for the new workbook.
        output = io.BytesIO()

        # Even though the final file will be in memory the module uses temp
        # files during assembly for efficiency. To avoid this on servers that
        # don't allow temp files, for example the Google APP Engine, set the
        # 'in_memory' Workbook() constructor option as shown in the docs.
        self.wb = xlsxwriter.Workbook(output)

        self.header_style = self.wb.add_format({
            'bold': True,
        })

        self.ws = self.wb.add_worksheet('Data Sheet')

        bold = self.wb.add_format({'bold': 1})

        # Get the reference view
        view = renderer_context.get('view', {})

        # Check if it's the instance of view type
        if not isinstance(view, dict):

            # Get a view's class name
            view_class_name = type(view).__name__

            # for exceptional fields we should perform different logic
            # then for other selectable fields
            self.exceptional_fields = view.exceptional_fields
            # Break down Activity by defined column in ActivityList class
            self.break_down_by = view.break_down_by

            self.selectable_fields = view.selectable_fields

            # if view.field = (), that means fields = all parameter is
            # passed. So we need to get all the serializer fields.
            if view.fields == ():
                fields = tuple(view.serializer_fields)
            else:
                fields = view.fields

            self.default_fields = list(set(view.fields) - set(self.selectable_fields))  # NOQA: E501

            utils = UtilRenderer()
            utils.exceptional_fields = view.exceptional_fields
            utils.break_down_by = view.break_down_by
            utils.selectable_fields = view.selectable_fields
            utils.default_fields = self.default_fields

            if view_class_name in ['ActivityList', 'ActivityDetail']:

                activity_data = utils.adjust_transaction_types(data, 'transaction_types')  # NOQA: E501
                data = activity_data['data']
                selectable_headers = activity_data['selectable_headers']
                activity_data.pop('selectable_headers', None)
                self.rows, self.headers = utils.create_rows_headers(data, view.csv_headers, selectable_headers, fields, False)  # NOQA: E501

            elif view_class_name in ['TransactionList', 'TransactionDetail']:

                transactions_data = utils.group_data(data, view, 'iati_identifier', 'transactions')  # NOQA: E501
                selectable_headers = transactions_data['selectable_headers']
                transactions_data.pop('selectable_headers', None)
                self.rows, self.headers = utils.create_rows_headers(list(transactions_data.values()), view.csv_headers, selectable_headers, view.fields, True)  # NOQA: E501

            elif view_class_name in ['LocationList', 'LocationDetail']:

                location_data = utils.group_data(data, view, 'iati_identifier', 'locations')  # NOQA: E501
                selectable_headers = location_data['selectable_headers']
                location_data.pop('selectable_headers', None)
                self.rows, self.headers = utils.create_rows_headers(list(location_data.values()), view.csv_headers, selectable_headers, view.fields, True)  # NOQA: E501

            elif view_class_name in ['BudgetList', 'BudgetDetail']:

                budget_data = utils.group_data(data, view, 'iati_identifier', 'budgets')  # NOQA: E501
                selectable_headers = budget_data['selectable_headers']
                budget_data.pop('selectable_headers', None)
                self.rows, self.headers = utils.create_rows_headers(list(budget_data.values()), view.csv_headers, selectable_headers, view.fields, True)  # NOQA: E501

            elif view_class_name in ['ResultList', 'ResultDetail']:

                result_data = utils.group_data(data, view, 'iati_identifier', 'results')  # NOQA: E501
                selectable_headers = result_data['selectable_headers']
                result_data.pop('selectable_headers', None)
                self.rows, self.headers = utils.create_rows_headers(list(result_data.values()), view.csv_headers, selectable_headers, view.fields, True)  # NOQA: E501

        row_index = 0
        column_width = {}

        for index, header in enumerate(self.headers.keys()):
            self.ws.write(row_index, index, header, bold)
            if index not in column_width:
                column_width[index] = len(header)

        for row in self.rows:
            row_index += 1
            for column_index, header in enumerate(self.headers):
                self.ws.write(row_index, column_index, row[column_index])
                if column_width[column_index] < len(row[column_index]):
                    column_width[column_index] = len(row[column_index])

        for index, width in column_width.items():
            # Adjust the column width.
            self.ws.set_column(index, index, width)

        # self._write_to_excel(data)

        # Close the workbook before sending the data.
        self.wb.close()

        # Rewind the buffer.
        output.seek(0)

        return output

    def _write_to_excel(self, data):
        if type(data) is ReturnList or type(data) is list \
                or type(data) is OrderedDict:
            # So if the initial data, is a list, that means that
            # We can create a seperate row for each item.
            #
            # So first we write the columns,
            # cause we need to form the appropriate columns
            # for all the possible values,
            # for each result item
            # this is needed to be done seperatly for results,
            # because some results
            # might have more values than others == more values
            # in their arrays and etc.
            for item in data:
                self._store_columns(item)

            # And here we form the cell matrix according to the saved columns
            # and the row number
            for i, item in enumerate(data):
                # + 1 cause first row is reserved for the header
                row_numb = i + 1
                self._store_cells(item, '', row_numb)
        elif type(data) is ReturnDict or type(data) is dict:
            # Here we do the same as above just without for loops
            # cause if it goes in here, it is most likely detail data
            self._store_columns(data)
            self._store_cells(data)

        self._write_data(data)

    def _store_columns(self, data, col_name=''):
        divider = '.' if col_name != '' else ''
        if type(data) is ReturnList or type(data) is list:
            for i, item in enumerate(data):
                column_name = col_name + divider + str(i)
                self._store_columns(item, column_name)
        elif type(data) is ReturnDict or type(data) is dict \
                or type(data) is OrderedDict:
            for key, value in data.items():
                column_name = col_name + divider + key
                self._store_columns(value, column_name)
        else:
            try:
                # this is here just as a check,
                # to make this try except work as expected
                self.columns.index(col_name)
                self.prev_col_name = col_name
            except ValueError:

                if self.requested_fields:
                    # We check if the formed column
                    # is one of the requested fields
                    try:
                        self.requested_fields[col_name]
                        # if it is we continue with the storing of the column
                    except KeyError:
                        # if it isn't we return the this recursive method
                        # thus skipping the below code,
                        # where the column header is stored
                        return

                if self.prev_col_name:
                    # So this part of the if is mainly
                    # used to store column header names,
                    # that were not available in the previous result items,
                    # into there appropriate place
                    index = self.columns.index(self.prev_col_name) + 1
                    self.columns.insert(index, col_name)
                    self.prev_col_name = col_name
                else:
                    # This is used only to store the column header names
                    # formed from the initial result item
                    self.columns.append(col_name)

    def _store_cells(self, data, col_name='', row_numb=1):
        divider = '.' if col_name != '' else ''
        if type(data) is ReturnList or type(data) is list:
            for i, item in enumerate(data):
                column_name = col_name + divider + str(i)
                self._store_cells(item, column_name, row_numb)
        elif type(data) is ReturnDict or type(data) is dict \
                or type(data) is OrderedDict:
            for key, value in data.items():
                column_name = col_name + divider + key
                self._store_cells(value, column_name, row_numb)
        else:
            # So if we go in here the data is the actual value of the cell
            # and so here we store the actual cell
            # and we give this cell matrix/dictionary appropriate
            # indexes according to the row_number
            # and its appropriate column name
            try:
                self.cells[(row_numb, self.columns.index(col_name))] = data
            except ValueError:
                # so if the index for the columns does not exist it means that
                # it is not a requested field and thus we skip it
                pass

    def _write_data(self, data):
        # write column headers
        for ind, header in enumerate(self.columns):
            if self.requested_fields:
                self.ws.write(0, ind, self.requested_fields[header],
                              self.header_style)
            else:
                self.ws.write(0, ind, header, self.header_style)

        # write cells
        for i in range(len(data)):
            # Cause we already wrote the column headers
            row_numb = i + 1
            for col_numb, header in enumerate(self.columns):
                # so as described in some comments above
                # sometimes some cells
                # will not have some values for some columns
                # so we just pass these cell values and dont write them
                try:
                    cell_value = self.cells[(row_numb, col_numb)]
                    self.ws.write(row_numb, col_numb, cell_value,
                                  self.cell_style)

                    # We set the column width according to the
                    # length of the data/value or the header if its longer
                    width = len(str(cell_value)) if \
                        len(str(cell_value)) > len(header) \
                        else len(header)
                    # And we check here if the previously set
                    # width for the is bigger than this
                    try:
                        if width > self.col_widths[col_numb]:
                            self.col_widths[col_numb] = width
                        width = self.col_widths[col_numb]
                    except IndexError:
                        self.col_widths.append(width)

                    self.ws.set_column(col_numb, col_numb, width)

                except KeyError:
                    pass


class IATIXMLRenderer(BaseRenderer):
    """
    Renderer which serializes to XML.
    """

    media_type = 'application/xml'
    format = 'xml'
    charset = 'UTF-8'
    root_tag_name = 'iati-activities'
    item_tag_name = 'iati-activity'
    version = '2.03'
    default_references = {
        'iati_identifier': None,
    }

    element_references = {
        'title': TitleReference,
        'description': DescriptionReference,
        'activity_date': ActivityDateReference,
        'reporting_org': ReportingOrgReference,
        'participating_org': ParticipatingOrgReference,
        'contact_info': ContactInfoReference,
        'activity_scope': ActivityScopeReference,
        'transaction': TransactionReference,
        'sector': SectorReference,
        'budget': BudgetReference,
        'other_identifier': OtherIdentifierReference,
        'activity_status': ActivityStatusReference,
        'recipient_country': RecipientCountryReference,
        'recipient_region': RecipientRegionReference,
        'location': LocationReference,
        'policy_marker': PolicyMarkerReference,
        'collaboration_type': CollaborationTypeReference,
        'default_flow_type': DefaultFlowTypeReference,
        'default_finance_type': DefaultFinanceTypeReference,
        'default_tied_status': DefaultTiedStatusReference,
        'planned_disbursement': PlannedDisbursementReference,
        'capital_spend': CapitalSpendReference,
        'document_link': DocumentLinkReference,
        'legacy_data': LegacyDataReference,
        'crs_add': CrsAddReference,
        'result': ResultReference,
        'fss': FssReference,
        'humanitarian_scope': HumanitarianScopeReference,
        'related_activity': RelatedActivityReference,
        'conditions': ConditionsReference,
        'country_budget_items': CountryBudgetItemsReference,
        'tag': TagReference,
        'default_aid_type': DefaultAidTypeReference,
    }

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Renders `data` into serialized XML.
        """
        view = renderer_context.get('view')
        view_class_name = view.__class__.__name__

        if not data:
            return ''
        elif view_class_name in ['ActivityList', 'OrganisationList']:
            if 'results' in data:
                data = data['results']
                if data and data[0].get("sectors"):
                    ElementReference.activity_sector = True
            self.xml = E(self.root_tag_name)
            self.xml.set('version', self.version)

            if hasattr(settings, 'EXPORT_COMMENT'):
                self.xml.append(
                    etree.Comment(getattr(settings, 'EXPORT_COMMENT')))

            self._to_xml(self.xml, data)

            # the element with namespace must be the last element in the xml.
            for element in self.xml.iter():
                if element.tag.find("https://www.zimmerman.team") != -1:
                    print(element.tag)
                    parent = element.getparent()
                    parent.remove(element)
                    parent.append(element)

            return etree.tostring(
                self.xml,
                encoding=self.charset,
                pretty_print=True
            )

        elif view_class_name in ['ActivityDetail',
                                 'ActivityDetailByIatiIdentifier',
                                 ]:
            self.xml = E(self.root_tag_name)
            self.xml.set('version', self.version)

            if hasattr(settings, 'EXPORT_COMMENT'):
                self.xml.append(
                    etree.Comment(getattr(settings, 'EXPORT_COMMENT')))

            # if requested data is not found, we don't need to create
            # 'iati-activity' element.
            if renderer_context.get('response').status_code == 404:
                self._to_xml(self.xml.find('iati-activity'), data)

            else:
                element = ActivityReference(parent_element=self.xml,
                                            data=data)
                element.create()
                self._to_xml(
                    # there is only one 'activity' element in 'DetailView'.
                    self.xml.find('iati-activity'),
                    data)

            return etree.tostring(
                self.xml,
                encoding=self.charset,
                pretty_print=True
            )
        elif view_class_name in ['OrganisationDetail']:
            self.xml = E(self.root_tag_name)
            self.xml.set('version', self.version)

            if hasattr(settings, 'EXPORT_COMMENT'):
                self.xml.append(
                    etree.Comment(getattr(settings, 'EXPORT_COMMENT')))

            element = OrganisationReference(parent_element=self.xml,
                                            data=data)
            element.create()
            self._to_xml(
                # there is only one 'organisation' element in 'DetailView'.
                self.xml.find('iati-organisation'),
                data)

            return etree.tostring(
                self.xml,
                encoding=self.charset,
                pretty_print=True
            )
        else:
            self.xml = E('message')
            self.xml.text = 'The requested endpoint is not available in xml ' \
                            'format.'

            return etree.tostring(self.xml, encoding=self.charset,
                                  pretty_print=True)

    def _to_xml(self, xml, data, parent_name=None):
        if isinstance(data, (list, tuple)):
            for item in data:
                # Tag references
                if parent_name in self.element_references:
                    element = self.element_references[parent_name](
                        parent_element=xml,
                        data=item
                    )
                    element.create()
                elif parent_name:
                    self._to_xml(etree.SubElement(
                        xml, parent_name.replace('_', '-')), item)
                else:
                    if self.item_tag_name == 'iati-activity':
                        element = ActivityReference(
                            parent_element=self.xml,
                            data=item
                        )
                        element.create()
                    else:
                        element = OrganisationReference(
                            parent_element=self.xml,
                            data=item
                        )
                        element.create()

                    self._to_xml(
                        self.xml.findall(self.item_tag_name)[-1],
                        item
                    )

        elif isinstance(data, dict):
            attributes = []

            if hasattr(data, 'xml_meta'):
                attributes = list(set(data.xml_meta.get(
                    'attributes', list())) & set(data.keys()))

                for attr in attributes:

                    renamed_attr = attr.replace(
                        'xml_lang',
                        '{http://www.w3.org/XML/1998/namespace}lang'
                    ).replace('_', '-')

                    value = data[attr]
                    if value is not None:
                        xml.set(
                            renamed_attr,
                            six.text_type(value).lower() if isinstance(
                                value, bool
                            ) else six.text_type(value))

            for key, value in six.iteritems(data):

                if key in attributes or key not in {**self.element_references, **self.default_references}:  # NOQA: E501
                    # TODO: we have some bugs data here,
                    # I don't know where they come from please check them.
                    # How to produce it:
                    # - run debugging
                    # - stop debug line on below "continue"
                    # - check key and value you should get some OrderDict
                    continue

                if key == 'text':
                    self._to_xml(xml, value)
                elif isinstance(value, list):
                    self._to_xml(xml, value, parent_name=key)
                else:
                    # TODO remove this ugly hack by adjusting the
                    # resultindicatorperiod actual / target models. 30-08-16
                    # currently actuals are stored on the
                    # resultindicatorperiod, hence we need to remove empty
                    # actuals here.
                    if key in ['actual', 'target']:
                        if list(value.items())[0][0] != 'value':
                            continue

                    # Tag references
                    if key in self.element_references:
                        element = self.element_references[key](
                            parent_element=xml,
                            data=value
                        )
                        element.create()
                    else:
                        self._to_xml(etree.SubElement(
                            xml, key.replace('_', '-')), value)

        elif data is None:
            pass

        else:
            xml.text = six.text_type(data)
            pass


class OrganisationIATIXMLRenderer(IATIXMLRenderer):
    """
    Renderer of the XML export for the organisation file
    """
    root_tag_name = 'iati-organisations'
    item_tag_name = 'iati-organisation'
    default_references = {
        'organisation_identifier': None,
    }
    element_references = {
        'default_currency': DefaultCurrencyOrgReference,
        'last_updated_datetime': LastUpdatedDatetimeOrgReference,
        'xml_lang': XmlLangReference,
        'name': NameOrgReference,
        'reporting_org': ReportingOrgOrgReference,
        'total_budgets': TotalBudgetOrgReference,
        'recipient_org_budgets': RecipientOrgBudgetOrgReference,
        'recipient_region_budgets': RecipientRegionBudgetOrgReference,
        'recipient_country_budgets': RecipientCountryBudgetOrgReference,
        'total_expenditures': TotalExpenditureOrgReference,
        'document_link': DocumentLinkOrgReference
    }


class OrganisationIATICSVRenderer(CSVRenderer):

    class OrganisationIdentifierMap:

        @classmethod
        def get(cls, data):
            return data.get('organisation_identifier')

    class NameMap:

        @classmethod
        def get(cls, data):
            narratives = data.get('name').get('narratives')

            if narratives and isinstance(narratives, list):
                data_column = ''
                for narrative in narratives:
                    data_column = data_column + narrative.get('text') + ';'

                return data_column

            # Note: CSV is needed blank space
            # to initial it as blank values
            return ' '

    class ReportingOrgMap:

        @classmethod
        def get(cls, data):
            reporting_org = data.get('reporting_org')

            if reporting_org:
                data_columns = list()
                data_columns.append(reporting_org.get('ref'))
                data_columns.append(reporting_org.get('type').get('code'))
                data_columns.append(reporting_org.get('secondary_reporter'))
                data_columns.append(
                    reporting_org.get('narratives')[0].get('text')
                )

                return data_columns

            return [' ', ' ', ' ', ' ']

    class TotalBudgetsMap:

        @classmethod
        def get(cls, data):
            total_budgets = data.get('total_budgets')
            if total_budgets and isinstance(total_budgets, list):
                data_column = ''
                for total_budget in total_budgets:
                    currency = total_budget.get(
                        'value'
                    ).get('currency').get('code')
                    value = str(total_budget.get('value').get('value'))

                    data_column = data_column + '{currency}{value};'.format(
                        currency=currency, value=value
                    )

                return data_column

            return ' '

    class RecipientOrgBudgetsMap:

        @classmethod
        def get(cls, data):
            recipient_org_budgets = data.get('recipient_org_budgets')
            if recipient_org_budgets and isinstance(
                    recipient_org_budgets, list
            ):
                data_column = ''
                for recipient_org_budget in recipient_org_budgets:
                    data_column = data_column + recipient_org_budget.get(
                        'recipient_org'
                    ).get('ref') + ';'

                return data_column

            return ' '

    class RecipientRegionBudgetsMap:

        @classmethod
        def get(cls, data):
            recipient_region_budgets = data.get('recipient_region_budgets')
            if recipient_region_budgets and isinstance(
                    recipient_region_budgets, list
            ):
                data_column = ''
                for recipient_region_budget in recipient_region_budgets:
                    data_column = data_column + recipient_region_budget.get(
                        'recipient_region'
                    ).get('code') + ';'

                return data_column

            return ' '

    class RecipientCountryBudgetsMap:

        @classmethod
        def get(cls, data):
            recipient_country_budgets = data.get('recipient_country_budgets')
            if recipient_country_budgets and isinstance(
                    recipient_country_budgets, list
            ):
                data_column = ''
                for recipient_country_budget in recipient_country_budgets:
                    data_column = data_column + recipient_country_budget.get(
                        'recipient_country'
                    ).get('code') + ';'

                return data_column

            return ' '

    class TotalExpendituresMap:

        @classmethod
        def get(cls, data):
            total_expenditures = data.get('total_expenditures')
            if total_expenditures and isinstance(total_expenditures, list):
                data_column = ''
                for total_expenditure in total_expenditures:
                    currency = total_expenditure.get(
                        'value'
                    ).get('currency').get('code')
                    value = str(total_expenditure.get('value').get('value'))

                    data_column = data_column + '{currency}{value};'.format(
                        currency=currency, value=value
                    )

                return data_column

            return ' '

    class DefaultCurrencyMap:
        @classmethod
        def get(cls, data):
            default_currency = data.get('default_currency')
            if default_currency:
                currency = default_currency.get('code')
                return currency

            return ' '

    class DocumentLinksMap:

        @classmethod
        def get(cls, data):
            document_links = data.get('document_link')
            if document_links and isinstance(document_links, list):
                data_column = ''
                for document_links in document_links:
                    data_column = data_column + document_links.get('url') + ';'

                return data_column

            return ' '

    results_field = 'results'
    default_headers = [
        'orgasanition_identifier',
        'name'
    ]
    headers_name = {
        'orgasanition_identifier': 'organisation-identifier',
        'name': 'name/0/narratives',
        'reporting_org': [
            'reporting-org/@ref',
            'reporting-org/@type',
            'reporting-org/@secondary-reporter',
            'reporting-org/narratives',
        ],
        'total_budgets': '0/total_budget/value',
        'recipient_org_budgets': '0/recipient-org-budget/recipient-org/@ref',
        'recipient_region_budgets': '0/recipient-region-budget/recipient-region/@code',  # NOQA: E501
        'recipient_country_budgets': '0/recipient-country-budget/recipient-country/@code',  # NOQA: E501
        'total_expenditures': '0/total-expenditure/value',
        'document_links': '0/document_link/@url',
        'default_currency': 'default-currency/@code'
    }
    data_map = {
        'orgasanition_identifier': OrganisationIdentifierMap,
        'name': NameMap,
        'reporting_org': ReportingOrgMap,
        'total_budgets': TotalBudgetsMap,
        'recipient_org_budgets': RecipientOrgBudgetsMap,
        'recipient_region_budgets': RecipientRegionBudgetsMap,
        'recipient_country_budgets': RecipientCountryBudgetsMap,
        'total_expenditures': TotalExpendituresMap,
        'document_links': DocumentLinksMap,
        'default_currency': DefaultCurrencyMap,
    }
    fields = ''

    def __init__(self, *args, **kwargs):
        super(OrganisationIATICSVRenderer, self).__init__(*args, **kwargs)

    def render(self, data, *args, **kwargs):
        actual_kwargs = args[1].get('kwargs', {})

        # this is a list view
        if 'pk' not in actual_kwargs:
            data = data.get(self.results_field, [])

            self.fields = args[1].get('request').GET.get('fields', '')
            if self.fields == 'all':
                self.fields = 'reporting_org,total_budgets,recipient_org_budgets,recipient_country_budgets,total_expenditures,document_links,default_currency'  # NOQA:  E501
        else:
            self.fields = 'reporting_org,total_budgets,recipient_org_budgets,recipient_country_budgets,total_expenditures,document_links,default_currency'  # NOQA:  E501

        return self.process(data, *args, **kwargs)

    def process(self, data, media_type=None, renderer_context=None,
                writer_opts=None):
        """
        Renders serialized *data* into CSV. For a dictionary:
        """
        if not renderer_context:
            renderer_context = dict()

        if data is None:
            return ''

        if not isinstance(data, list):
            data = [data]

        headers = []
        headers_column = []
        for header in self.default_headers:
            headers.append(self.headers_name.get(header))
            headers_column.append(header)

        for field in self.fields.split(','):
            header = self.headers_name.get(field)

            if header:
                headers_column.append(field)

                if isinstance(header, list):
                    headers = headers + header
                else:
                    headers.append(header)

        writer_opts = renderer_context.get(
            'writer_opts', writer_opts or self.writer_opts or {}
        )
        encoding = renderer_context.get('encoding', settings.DEFAULT_CHARSET)

        csv_buffer = BytesIO()
        csv_writer = csv.writer(csv_buffer, encoding=encoding, **writer_opts)
        csv_writer.writerow(headers)

        for row in data:
            data_columns = []

            for header in headers_column:
                item = self.data_map.get(header)().get(row)

                if isinstance(item, list):
                    data_columns = data_columns + item
                elif item:
                    data_columns.append(item)

            csv_writer.writerow(data_columns)

        return csv_buffer.getvalue()


class OrganisationIATIXSLXRenderer(OrganisationIATICSVRenderer):
    media_type = 'application/vnd.ms-excel'
    results_field = 'results'
    render_style = 'xls'
    format = 'xls'

    def process(self, data, media_type=None, renderer_context=None,
                writer_opts=None):
        """
        Renders serialized *data* into XSLX.
        """
        if data is None:
            return ''

        if not isinstance(data, list):
            data = [data]

        # Setup headers
        headers = []
        headers_column = []
        for header in self.default_headers:
            headers.append(self.headers_name.get(header))
            headers_column.append(header)

        for field in self.fields.split(','):
            header = self.headers_name.get(field)

            if header:
                headers_column.append(field)

                if isinstance(header, list):
                    headers = headers + header
                else:
                    headers.append(header)

        # Setup IO
        xlsx_buffer = BytesIO()
        workbook = xlsxwriter.Workbook(xlsx_buffer)
        worksheet = workbook.add_worksheet()

        # Render Header
        row = 0
        col = 0
        bold = workbook.add_format({'bold': 1})
        column_width = dict()
        for header in headers:
            worksheet.write(row, col, header, bold)
            column_width[col] = len(header)
            col += 1

        # Render data contents
        row = 1
        for data_row in data:
            data_columns = []

            for header in headers_column:
                item = self.data_map.get(header)().get(data_row)

                if isinstance(item, list):
                    data_columns = data_columns + item
                elif item:
                    data_columns.append(item)

            col = 0
            for data_column in data_columns:
                worksheet.write(row, col, data_column)

                if column_width[col] < len(data_column):
                    column_width[col] = len(data_column)

                col += 1

            row += 1

        for index, width in column_width.items():
            # Adjust the column width.
            worksheet.set_column(index, index, width)

        workbook.close()

        return xlsx_buffer.getvalue()
