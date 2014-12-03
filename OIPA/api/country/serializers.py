from rest_framework import serializers
import geodata


class CountryDetailSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='country-detail')

    activity_set = serializers.RelatedField(many=True, read_only=True)
    activityrecipientcountry_set = serializers.RelatedField(
        many=True, read_only=True)
    adm1region_set = serializers.RelatedField(many=True, read_only=True)
    city_set = serializers.RelatedField(many=True, read_only=True)
    indicatordata_set = serializers.RelatedField(many=True, read_only=True)
    location_set = serializers.RelatedField(many=True, read_only=True)
    unescoindicatordata_set = serializers.RelatedField(
        many=True, read_only=True)

    class Meta:
        model = geodata.models.Country
        fields = (
            'url',
            'code',
            'numerical_code_un',
            'name',
            'alt_name',
            'language',
            'capital_city',
            'region',
            'un_region',
            'unesco_region',
            'dac_country_code',
            'iso3',
            'alpha3',
            'fips10',
            'center_longlat',
            'polygon',
            'data_source',

            # Reverse linked data
            'activity_set',
            'adm1region_set',
            'city_set',
            'indicatordata_set',
            'location_set',
            'unescoindicatordata_set',
            'activityrecipientcountry_set',
        )


class CountryListSerializer(CountryDetailSerializer):
    class Meta:
        model = geodata.models.Country
