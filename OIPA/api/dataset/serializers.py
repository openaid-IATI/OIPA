import urllib.parse

from django.urls import reverse
from rest_framework import serializers
from rest_framework.serializers import (
    HiddenField, HyperlinkedIdentityField, HyperlinkedRelatedField, ModelSerializer, SerializerMethodField
)

from api.generics.serializers import DynamicFieldsModelSerializer
from iati.models import Activity
from iati_synchroniser.models import Dataset, DatasetFailedPickup, DatasetNote, Publisher


class DatasetNoteSerializer(ModelSerializer):
    class Meta:
        model = DatasetNote
        fields = (
            'model',
            'iati_identifier',
            'exception_type',
            'model',
            'field',
            'message',
            'line_number',
            'variable')


class SimplePublisherSerializer(ModelSerializer):
    id = HiddenField(default=None)
    url = HyperlinkedIdentityField(view_name='publishers:publisher-detail')

    class Meta:
        model = Publisher
        fields = (
            'id',
            'url',
            'publisher_iati_id',
            'display_name',
            'name')


class SimpleDatasetSerializer(DynamicFieldsModelSerializer):
    id = HiddenField(default=None)
    url = HyperlinkedIdentityField(view_name='datasets:dataset-detail')
    publisher = HyperlinkedRelatedField(
        view_name='publishers:publisher-detail',
        read_only=True)
    type = SerializerMethodField()

    class Meta:
        model = Dataset
        fields = (
            'id',
            'iati_id',
            'type',
            'url',
            'name',
            'title',
            'filetype',
            'publisher',
            'source_url',
            'iati_version',
            'added_manually',
        )

    def get_type(self, obj):
        return obj.get_filetype_display()


class DatasetSerializer(DynamicFieldsModelSerializer):

    id = HiddenField(default=None)
    url = HyperlinkedIdentityField(view_name='datasets:dataset-detail')
    publisher = SimplePublisherSerializer()
    filetype = SerializerMethodField()
    activities = SerializerMethodField()
    activity_count = SerializerMethodField()
    notes = HyperlinkedIdentityField(
        view_name='datasets:dataset-notes',)

    DatasetNoteSerializer(many=True, source="datasetnote_set")

    internal_url = SerializerMethodField()
    sha1 = serializers.CharField(source='sync_sha1')

    class Meta:
        model = Dataset
        fields = (
            'id',
            'iati_id',
            'url',
            'name',
            'title',
            'filetype',
            'publisher',
            'source_url',
            'activities',
            'activity_count',
            # 'activities_count_in_xml',
            # 'activities_count_in_database',
            'date_created',
            'date_updated',
            'last_found_in_registry',
            'iati_version',
            'sha1',
            'note_count',
            'notes',
            'added_manually',
            'is_parsed',
            'export_in_progress',
            'parse_in_progress',
            'internal_url',
            'validation_status'
        )

    def get_filetype(self, obj):
        return obj.get_filetype_display()

    def get_activities(self, obj):
        request = self.context.get('request')
        url = request.build_absolute_uri(reverse('activities:activity-list'))
        try:
            request_format = self.context.get('request').query_params.get(
                'format')
        except AttributeError:
            request_format = ''
        return url + '?dataset=' + str(obj.id) + '&format={request_format}'.\
            format(request_format=request_format)

    def get_activity_count(self, obj):
        return Activity.objects.filter(dataset=obj.id).count()

    def get_internal_url(self, obj):
        request = self.context.get('request')

        # Get internal url from the XML file in the local static folder
        internal_url = obj.get_internal_url()
        url = None
        if internal_url:
            internal_url = urllib.parse.quote(internal_url)
            complete_internal_url = request.build_absolute_uri(internal_url)
            if complete_internal_url is not None:
                url = complete_internal_url.replace('http:', 'https:')
            return url

        return None


class DatasetFailedPickupSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = DatasetFailedPickup
        fields = (
            'publisher_name',
            'publisher_identifier',
            'dataset_filename',
            'dataset_url',
            'is_http_error',
            'status_code',
            'error_detail',
            'timestamp'
        )
