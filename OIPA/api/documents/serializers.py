from rest_framework import serializers

from api.codelist.serializers import CodelistSerializer, NarrativeContainerSerializer
from api.generics.serializers import DynamicFieldsModelSerializer
from iati import models as iati_models


class DocumentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = iati_models.DocumentCategory
        fields = ('code', 'name')


class DocumentLinkSerializer(serializers.ModelSerializer):

    class DocumentDateSerializer(serializers.Serializer):
        iso_date = serializers.DateField()

    format = CodelistSerializer(source='file_format')
    categories = DocumentCategorySerializer(many=True)
    title = NarrativeContainerSerializer(source="documentlinktitle")
    document_date = DocumentDateSerializer(source="*")

    class Meta:
        model = iati_models.DocumentLink
        fields = (
            'url',
            'format',
            'categories',
            'title',
            'document_date',
        )


class DocumentSerializer(DynamicFieldsModelSerializer):
    document_link = DocumentLinkSerializer()
    id = serializers.HiddenField(default=None)

    class Meta:
        model = iati_models.Document
        fields = (
            'id',
            'document_name',
            'long_url',
            'document_link')
