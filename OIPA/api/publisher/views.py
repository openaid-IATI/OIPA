from ckanapi import RemoteCKAN
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import authentication, exceptions, filters, pagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_extensions.cache.mixins import CacheResponseMixin

from api.cache import QueryParamsKeyConstructor
from api.generics.views import DynamicDetailView, DynamicListView
from api.permissions.serializers import OrganisationUserSerializer
from api.publisher import serializers
from api.publisher.filters import PublisherFilter
from api.publisher.permissions import OrganisationAdminGroupPermissions
from common.util import get_or_none
from iati.permissions.models import OrganisationAdminGroup, OrganisationGroup, OrganisationUser
from iati_organisation.models import Organisation
from iati_synchroniser.models import Publisher


class PublisherPagination(pagination.PageNumberPagination):
    max_page_size = 10000
    page_size = 10
    page_size_query_param = 'page_size'


class PublisherList(CacheResponseMixin, DynamicListView):
    """
    Returns a list of IATI Publishers stored in OIPA.

    ## Request parameters

    - `id` (*optional*): Publisher id to search for.
    - `publisher_iati_id` (*optional*): Publisher IATI id to search for.
    - `display_name` (*optional*): Publisher IATI Registry display name to
       search for.
    - `name` (*optional*): Publisher IATI Registry name to search for.

    ## Result details

    Each result item contains short information about the publisher including
    the URI
    to publisher details.

    URI is constructed as follows: `/api/publishers/{publisher_iati_id}`

    """
    queryset = Publisher.objects.all().order_by('id')
    serializer_class = serializers.PublisherSerializer
    filter_class = PublisherFilter
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter,)
    pagination_class = PublisherPagination

    ordering_fields = (
        'id',
        'iati_id',
        'publisher_iati_id',
        'display_name',
        'name',
        'note_count')

    fields = (
        'url',
        'id',
        'iati_id',
        'publisher_iati_id',
        'display_name',
        'name',
        'activities')

    list_cache_key_func = QueryParamsKeyConstructor()


class PublisherDetail(CacheResponseMixin, DynamicDetailView):
    """
    Returns detailed information about a publisher.

    ## URI Format

    ```
    /api/publishers/{publisher_iati_id}
    ```

    ### URI Parameters

    - `publisher_iati_id`: ID of the desired publisher

    """
    queryset = Publisher.objects.all()
    serializer_class = serializers.PublisherSerializer


class OrganisationAdminGroupView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (OrganisationAdminGroupPermissions, )

    def get(self, request, publisher_id):
        users = OrganisationAdminGroup.objects.get(
            publisher_id=publisher_id).organisationuser_set.all()

        # print(users)

        serializer = OrganisationUserSerializer(
            users,
            many=True,
            context={
                'request': request,
            },
            fields=('username', 'email'),
        )

        return Response(serializer.data)

    def post(self, request, publisher_id):
        admin_group = OrganisationAdminGroup.objects.get(
            publisher_id=publisher_id)

        user_id = request.data.get('user_id', None)
        user = get_or_none(OrganisationUser, pk=user_id)

        if not user:
            return Response(status=401)

        admin_group.organisationuser_set.add(user)

        return Response()


class OrganisationAdminGroupDetailView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (OrganisationAdminGroupPermissions, )

    def delete(self, request, publisher_id, id):
        admin_group = OrganisationAdminGroup.objects.get(
            publisher_id=publisher_id)

        user_id = id
        user = get_or_none(OrganisationUser, pk=user_id)

        if not user:
            return Response(status=401)

        # TODO: user can remove himself from admin group? - 2016-10-24
        # if user.id == request.user.id:
        #     return Response(status=401)

        if user.id == admin_group.owner.id:
            return Response(status=401)

        admin_group.organisationuser_set.remove(user)

        return Response()


class OrganisationGroupView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (OrganisationAdminGroupPermissions, )

    def get(self, request, publisher_id):
        users = OrganisationGroup.objects.get(
            publisher_id=publisher_id).organisationuser_set.all()

        serializer = OrganisationUserSerializer(
            users,
            many=True,
            context={
                'request': request,
            },
            fields=('username', 'email')
        )

        return Response(serializer.data)

    def post(self, request, publisher_id):
        group = OrganisationGroup.objects.get(publisher_id=publisher_id)

        user_id = request.data.get('user_id', None)
        user = get_or_none(OrganisationUser, pk=user_id)

        if not user:
            return Response(status=401)

        group.organisationuser_set.add(user)

        return Response()


class OrganisationGroupDetailView(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    permission_classes = (OrganisationAdminGroupPermissions, )

    def delete(self, request, publisher_id, id):
        publisher = Publisher.objects.get(pk=publisher_id)
        group = OrganisationGroup.objects.get(publisher_id=publisher_id)

        user_id = id
        user = get_or_none(OrganisationUser, pk=user_id)

        if not user:
            return Response(status=401)

        # TODO: user can remove himself from  group? - 2016-10-24
        # if user.id == request.user.id:
        #     return Response(status=401)

        # The user to remove is an admin
        if user.organisation_admin_groups.filter(publisher=publisher).exists():
            # if
            # user.groups.filter(organisationadmingroup__publisher=publisher).exists():
            return Response(status=401)

        group.organisationuser_set.remove(user)

        return Response()


class OrganisationVerifyApiKey(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    # permission_classes = (OrganisationAdminGroupPermissions, )
    serializer_class = OrganisationUserSerializer

    def post(self, request):

        # TODO: If verifying for the first time, OrganisationGroup and
        # OrganisationAdminGroup don't exist yet. - 2016-10-25

        # publisher = Publisher.objects.get(pk=publisher_id)
        # group = OrganisationAdminGroup.objects.get(publisher_id=publisher_id)

        user = request.user.organisationuser
        api_key = request.data.get('apiKey')
        user_id = request.data.get('userId')

        if not api_key or not user_id:
            raise exceptions.ParseError(
                detail="apiKey or userId not specified")

        client = RemoteCKAN(settings.CKAN_URL, apikey=api_key)

        try:
            client.call_action('user_show', {
                "id": user_id,
                "include_datasets": True,
            })
        except BaseException:
            raise exceptions.APIException(
                detail="user with id {} not found".format(user_id))

        # print('got user')
        # print(result)

        try:
            orgList = client.call_action('organization_list_for_user', {})
        except BaseException:
            raise exceptions.APIException(
                detail="Can't get organisation list for user".format(user_id))

        if not len(orgList):
            raise exceptions.APIException(
                detail="This user has no organisations yet".format(user_id))

        primary_org_id = orgList[0]['id']

        try:
            primary_org = client.call_action(
                'organization_show', {"id": primary_org_id})
        except BaseException:
            raise exceptions.APIException(
                detail="Can't call organization_show for organization with id\
                        {}".format(primary_org_id))
            return Response(status=401)

        # print('got primary_org')
        # print(primary_org)

        if not primary_org:
            raise exceptions.APIException(
                detail="Can't call organization_show for organization with id\
                        {}".format(primary_org_id))

        primary_org_iati_id = primary_org.get('publisher_iati_id')
        publisher_org = get_or_none(Organisation,
                                    organisation_identifier=primary_org_iati_id
                                    )

        if not publisher_org:
            raise exceptions.APIException(
                detail="publisher_iati_id of {} not found in Organisation\
                        standard, correct this in the IATI registry".format(
                            primary_org_iati_id
                        )
                    )

        # TODO: add organisation foreign key - 2016-10-25
        publisher = Publisher.objects.update_or_create(
            iati_id=primary_org_id,
            publisher_iati_id=primary_org_iati_id,
            defaults={
                "name": primary_org.get('name'),
                "display_name": primary_org.get('display_name'),
                "organisation": publisher_org,
            }
        )

        organisation_group = OrganisationGroup.objects.get_or_create(
            publisher=publisher[0],
            defaults={
                "name": "{} Organisation Group".format(primary_org.get('name'))
            }
        )
        organisation_group[0].organisationuser_set.add(user)

        if publisher[1]:  # has been created
            organisation_admin_group = OrganisationAdminGroup.objects.\
                    get_or_create(
                        publisher=publisher[0],
                        defaults={
                            "owner": user,
                            "name": "{} Organisation Admin Group".format(
                                primary_org.get('name')
                            ),
                        }
                    )
        else:  # already exists
            organisation_admin_group = OrganisationAdminGroup.objects.\
                    get_or_create(
                        publisher=publisher[0],
                        defaults={
                            "name": "{} Organisation Admin Group".format(
                                primary_org.get('name')
                            ),
                        }
                    )
        organisation_admin_group[0].organisationuser_set.add(user)

        user.iati_api_key = api_key
        user.iati_user_id = user_id
        user.save()

        serializer = OrganisationUserSerializer(
            user,
            context={
                'request': request,
            }
        )

        return Response(serializer.data)


class OrganisationRemoveApiKey(APIView):
    authentication_classes = (authentication.TokenAuthentication,)
    # permission_classes = (OrganisationAdminGroupPermissions, )

    def post(self, request):
        user = request.user.organisationuser

        user.organisation_admin_groups.clear()
        user.organisation_groups.clear()

        OrganisationAdminGroup.objects.filter(
            user__organisationuser=user).delete()

        user.iati_api_key = None
        user.save()

        return Response("{}")
