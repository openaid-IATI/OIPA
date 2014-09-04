# Tastypie specific
from tastypie.resources import ModelResource
from tastypie.serializers import Serializer

# cache specific
from api.cache import NoTransformCache
from iati.models import AidType
from cache.validator import Validator

# Direct sql specific
import ujson
from django.db import connection
from django.http import HttpResponse
import xmlrpclib


# Helpers
from api.v3.resources.csv_serializer import CsvSerializer
from api.v3.resources.csv_helper import CsvHelper
from api.v3.resources.custom_call_helper import CustomCallHelper


class ActivityFilterOptionsResource(ModelResource):

    class Meta:
        #aid_type is used as dummy
        queryset = AidType.objects.all()
        resource_name = 'activity-filter-options'
        include_resource_uri = True
        cache = NoTransformCache()
        allowed_methods = ['get']


    def get_list(self, request, **kwargs):

        # check if call is cached using validator.is_cached
        # check if call contains flush, if it does the call comes from the cache updater and shouldn't return cached results
        validator = Validator()
        cururl = request.META['PATH_INFO'] + "?" + request.META['QUERY_STRING']

        if not 'flush' in cururl and validator.is_cached(cururl):
            return HttpResponse(validator.get_cached_call(cururl), mimetype='application/json')


        helper = CustomCallHelper()
        cursor = connection.cursor()
        organisations = request.GET.get("reporting_organisation__in", None)
        include_donors = request.GET.get("include_donor", None)
        include_start_year_actual = request.GET.get("include_start_year_actual", None)
        include_start_year_planned = request.GET.get("include_start_year_planned", None)
        if organisations:
            q_organisations = 'WHERE a.reporting_organisation_id = "' + organisations + '"'
        else:
            q_organisations = ""

        cursor.execute('SELECT c.code, c.name, count(c.code) as total_amount '
                       'FROM geodata_country c '
                       'LEFT JOIN iati_activityrecipientcountry rc on c.code = rc.country_id '
                       'LEFT JOIN iati_activity a on rc.activity_id = a.id %s '
                       'GROUP BY c.code' % (q_organisations))
        results1 = helper.get_fields(cursor=cursor)
        cursor.execute('SELECT s.code, s.name, count(s.code) as total_amount '
                       'FROM iati_sector s '
                       'LEFT JOIN iati_activitysector as ias on s.code = ias.sector_id '
                       'LEFT JOIN iati_activity a on ias.activity_id = a.id '
                       '%s '
                       'GROUP BY s.code' % (q_organisations))
        results2 = helper.get_fields(cursor=cursor)
        if q_organisations:
            q_organisations = q_organisations.replace("WHERE", "AND")
        cursor.execute('SELECT r.code, r.name, count(r.code) as total_amount '
                       'FROM geodata_region r '
                       'LEFT JOIN iati_activityrecipientregion rr on r.code = rr.region_id '
                       'LEFT JOIN iati_activity a on rr.activity_id = a.id '
                       'WHERE r.region_vocabulary_id = 1 '
                       '%s '
                       'GROUP BY r.code' % (q_organisations))
        results3 = helper.get_fields(cursor=cursor)

        options = {}
        options['countries'] = {}
        options['regions'] = {}
        options['sectors'] = {}



        for r in results1:

            country_item = {}
            country_item['name'] = r['name']
            country_item['total'] = r['total_amount']
            options['countries'][r['code']] = country_item

        for r in results2:
            sector_item = {}
            sector_item['name'] = r['name']
            sector_item['total'] = r['total_amount']
            options['sectors'][r['code']] = sector_item

        for r in results3:

            region_item = {}
            region_item['name'] = r['name']
            region_item['total'] = r['total_amount']
            options['regions'][r['code']] = region_item

        if include_donors:
            options['donors'] = {}

            cursor.execute('SELECT o.code, o.name, count(o.code) as total_amount '
                       'FROM iati_activity a '
                       'JOIN iati_activityparticipatingorganisation as po on a.id = po.activity_id '
                       'JOIN iati_organisation as o on po.organisation_id = o.code '
                       'WHERE 1 %s '
                       'GROUP BY o.code' % (q_organisations))
            results4 = helper.get_fields(cursor=cursor)

            for r in results4:

                donor_item = {}
                donor_item['name'] = r['name']
                donor_item['total'] = r['total_amount']
                options['donors'][r['code']] = donor_item

        if include_start_year_actual:

            options['start_actual'] = {}
            cursor.execute('SELECT YEAR(a.start_actual) as start_year, count(YEAR(a.start_actual)) as total_amount '
                       'FROM iati_activity a '
                       'WHERE 1 %s '
                       'GROUP BY YEAR(a.start_actual)' % (q_organisations))
            results5 = helper.get_fields(cursor=cursor)

            for r in results5:
                start_actual_item = {}
                start_actual_item['name'] = r['start_year']
                start_actual_item['total'] = r['total_amount']
                options['start_actual'][r['start_year']] = start_actual_item

        if include_start_year_planned:

            options['start_planned_years'] = {}
            cursor.execute('SELECT YEAR(a.start_planned) as start_year, count(YEAR(a.start_planned)) as total_amount '
                       'FROM iati_activity a '
                       'WHERE 1 %s '
                       'GROUP BY YEAR(a.start_planned)' % (q_organisations))
            results5 = helper.get_fields(cursor=cursor)

            for r in results5:
                start_planned_item = {}
                start_planned_item['name'] = r['start_year']
                start_planned_item['total'] = r['total_amount']
                options['start_planned_years'][r['start_year']] = start_planned_item


        if not q_organisations:
            cursor.execute('SELECT a.reporting_organisation_id, o.name, count(a.reporting_organisation_id) as total_amount '
                       'FROM iati_activity a '
                       'INNER JOIN iati_organisation o on a.reporting_organisation_id = o.code '
                       'GROUP BY a.reporting_organisation_id')
            results4 = helper.get_fields(cursor=cursor)

            options['reporting_organisations'] = {}

            for r in results4:

                org_item = {}
                org_item['name'] = r['name']
                org_item['total'] = r['total_amount']
                options['reporting_organisations'][r['reporting_organisation_id']] = org_item

        return HttpResponse(ujson.dumps(options), mimetype='application/json')


class ActivityFilterOptionsUnescoResource(ModelResource):

    class Meta:
        #aid_type is used as dummy
        queryset = AidType.objects.all()
        resource_name = 'activity-filter-options-unesco'
        include_resource_uri = True
        cache = NoTransformCache()
        allowed_methods = ['get']


    def get_list(self, request, **kwargs):

        # check if call is cached using validator.is_cached
        # check if call contains flush, if it does the call comes from the cache updater and shouldn't return cached results
        validator = Validator()
        cururl = request.META['PATH_INFO'] + "?" + request.META['QUERY_STRING']

        if not 'flush' in cururl and validator.is_cached(cururl):
            return HttpResponse(validator.get_cached_call(cururl), mimetype='application/json')


        helper = CustomCallHelper()
        cursor = connection.cursor()
        organisations = request.GET.get("reporting_organisation__in", None)

        countries = request.GET.get("countries__in", None)

        perspective = request.GET.get("perspective", None)
        w_perspective = ''

        if perspective:
            if perspective == 'country':
                q_perspective = ' JOIN iati_activityrecipientcountry as c on a.id = c.activity_id '
            elif perspective == 'region':
                q_perspective = ' JOIN iati_activityrecipientregion as r on a.id = r.activity_id '
            elif perspective == 'global':
                q_perspective = ''
                w_perspective = 'AND a.scope_id = 1 '
            else:
                q_perspective = ''
        else:
            q_perspective = ''


        include_donors = request.GET.get("include_donor", None)
        include_start_year_actual = request.GET.get("include_start_year_actual", None)
        include_start_year_planned = request.GET.get("include_start_year_planned", None)
        if organisations:
            q_organisations = 'AND a.reporting_organisation_id = "' + organisations + '" '
        else:
            q_organisations = ""

        query = ('SELECT c.code, c.name, count(c.code) as total_amount '
                       'FROM geodata_country c '
                       'LEFT JOIN iati_activityrecipientcountry rc on c.code = rc.country_id '
                       'LEFT JOIN iati_activity a on rc.activity_id = a.id '
                       'WHERE 1 %s %s '
                       'GROUP BY c.code' % (q_organisations, w_perspective))
        print query

        #making query for country results
        cursor.execute('SELECT c.code, c.name, count(c.code) as total_amount '
                       'FROM geodata_country c '
                       'LEFT JOIN iati_activityrecipientcountry rc on c.code = rc.country_id '
                       'LEFT JOIN iati_activity a on rc.activity_id = a.id '
                       'WHERE 1 %s %s '
                       'GROUP BY c.code' % (q_organisations, w_perspective))
        results1 = helper.get_fields(cursor=cursor)

        #making query for sector results
        cursor.execute('SELECT s.code, s.name, count(s.code) as total_amount '
                       'FROM iati_sector s '
                       'LEFT JOIN iati_activitysector as ias on s.code = ias.sector_id '
                       'LEFT JOIN iati_activity a on ias.activity_id = a.id '
                       'WHERE 1 %s %s '
                       'GROUP BY s.code' % (q_organisations, w_perspective))
        results2 = helper.get_fields(cursor=cursor)

        #making query for regions
        if q_organisations:
            q_organisations = q_organisations.replace("WHERE", "AND")
        cursor.execute('SELECT r.code, r.name, count(r.code) as total_amount '
                       'FROM geodata_region r '
                       'LEFT JOIN iati_activityrecipientregion rr on r.code = rr.region_id '
                       'LEFT JOIN iati_activity a on rr.activity_id = a.id '
                       'WHERE r.region_vocabulary_id = 1 '
                       '%s %s '
                       'GROUP BY r.code' % (q_organisations, w_perspective))
        results3 = helper.get_fields(cursor=cursor)

        options = {}
        options['countries'] = {}
        options['regions'] = {}
        options['sectors'] = {}


        #country results
        for r in results1:

            country_item = {}
            country_item['name'] = r['name']
            country_item['total'] = r['total_amount']
            options['countries'][r['code']] = country_item
        #sector results
        for r in results2:
            sector_item = {}
            sector_item['name'] = r['name']
            sector_item['total'] = r['total_amount']
            options['sectors'][r['code']] = sector_item
        #region results
        for r in results3:

            region_item = {}
            region_item['name'] = r['name']
            region_item['total'] = r['total_amount']
            options['regions'][r['code']] = region_item
        #donor results
        if include_donors:
            options['donors'] = {}
            if countries:
                q_countries = ' and c.country_id = "' + countries + '"'
            else:
                q_countries = ""

            cursor.execute('SELECT o.code, o.name, count(o.code) as total_amount '
                       'FROM iati_activity a '
                       'JOIN iati_activityparticipatingorganisation as po on a.id = po.activity_id '
                       'JOIN iati_organisation as o on po.organisation_id = o.code '
                       ' %s '
                       'WHERE 1 %s %s %s '
                       'GROUP BY o.code' % (q_perspective, q_organisations, q_countries, w_perspective))
            results4 = helper.get_fields(cursor=cursor)

            for r in results4:

                donor_item = {}
                donor_item['name'] = r['name']
                donor_item['total'] = r['total_amount']
                options['donors'][r['code']] = donor_item

        if include_start_year_actual:

            options['start_actual'] = {}
            cursor.execute('SELECT YEAR(a.start_actual) as start_year, count(YEAR(a.start_actual)) as total_amount '
                       'FROM iati_activity a '
                        ' %s '
                       'WHERE 1 %s %s '
                       'GROUP BY YEAR(a.start_actual)' % (q_perspective, q_organisations, w_perspective))
            results5 = helper.get_fields(cursor=cursor)

            for r in results5:
                start_actual_item = {}
                start_actual_item['name'] = r['start_year']
                start_actual_item['total'] = r['total_amount']
                options['start_actual'][r['start_year']] = start_actual_item

        if include_start_year_planned:

            options['start_planned_years'] = {}
            cursor.execute('SELECT YEAR(a.start_planned) as start_year, count(YEAR(a.start_planned)) as total_amount '
                       'FROM iati_activity a '
                        ' %s '
                       'WHERE 1 %s %s '
                       'GROUP BY YEAR(a.start_planned)' % (q_perspective, q_organisations, w_perspective))
            results5 = helper.get_fields(cursor=cursor)

            for r in results5:
                start_planned_item = {}
                start_planned_item['name'] = r['start_year']
                start_planned_item['total'] = r['total_amount']
                options['start_planned_years'][r['start_year']] = start_planned_item


        if not q_organisations:
            cursor.execute('SELECT a.reporting_organisation_id, o.name, count(a.reporting_organisation_id) as total_amount '
                       'FROM iati_activity a '
                        ' %s '
                       'INNER JOIN iati_organisation o on a.reporting_organisation_id = o.code '
                       'WHERE 1 %s '
                       'GROUP BY a.reporting_organisation_id' % q_perspective, w_perspective)
            results4 = helper.get_fields(cursor=cursor)

            options['reporting_organisations'] = {}

            for r in results4:

                org_item = {}
                org_item['name'] = r['name']
                org_item['total'] = r['total_amount']
                options['reporting_organisations'][r['reporting_organisation_id']] = org_item

        return HttpResponse(ujson.dumps(options), mimetype='application/json')



class CountryGeojsonResource(ModelResource):

    class Meta:
        #aid_type is used as dummy
        queryset = AidType.objects.all()
        resource_name = 'country-geojson'
        include_resource_uri = True
        cache = NoTransformCache()
        allowed_methods = ['get']


    def get_list(self, request, **kwargs):

        # check if call is cached using validator.is_cached
        # check if call contains flush, if it does the call comes from the cache updater and shouldn't return cached results
        validator = Validator()
        cururl = request.META['PATH_INFO'] + "?" + request.META['QUERY_STRING']

        if not 'flush' in cururl and validator.is_cached(cururl):
            return HttpResponse(validator.get_cached_call(cururl), mimetype='application/json')

        helper = CustomCallHelper()
        country_q = helper.get_and_query(request, 'countries__in', 'c.code')
        budget_q_gte = request.GET.get('total_budget__gt', None)
        budget_q_lte = request.GET.get('total_budget__lt', None)
        region_q = helper.get_and_query(request, 'regions__in', 'r.code')
        sector_q = helper.get_and_query(request, 'sectors__in', 's.sector_id')
        organisation_q = helper.get_and_query(request, 'reporting_organisation__in', 'a.reporting_organisation_id')
        budget_q = ''

        if budget_q_gte:
            budget_q += ' a.total_budget > "' + budget_q_gte + '" ) AND ('
        if budget_q_lte:
            budget_q += ' a.total_budget < "' + budget_q_lte + '" ) AND ('


        filter_string = ' AND (' + country_q + organisation_q + region_q + sector_q + budget_q + ')'
        if 'AND ()' in filter_string:
            filter_string = filter_string[:-6]



        if region_q:
            filter_region = 'LEFT JOIN iati_activityrecipientregion rr ON rr.activity_id = a.id LEFT JOIN geodata_region r ON rr.region_id = r.code '
        else:
            filter_region = ''

        if sector_q:
            filter_sector = 'LEFT JOIN iati_activitysector s ON a.id = s.activity_id '
        else:
            filter_sector = ''

        cursor = connection.cursor()
        query = 'SELECT c.code as country_id, c.name as country_name, count(a.id) as total_projects '\
                'FROM iati_activity a '\
                'LEFT JOIN iati_activityrecipientcountry rc ON rc.activity_id = a.id '\
                'LEFT JOIN geodata_country c ON rc.country_id = c.code '\
                '%s %s'\
                'WHERE 1 %s'\
                'GROUP BY c.code' % (filter_region, filter_sector, filter_string)

        print query
        cursor.execute(query)
        print connection.queries

        activity_result = {'type' : 'FeatureCollection', 'features' : []}

        activities = []

        results = helper.get_fields(cursor=cursor)
        for r in results:
            country = {}
            country['type'] = 'Feature'
            country['id'] = r['country_id']

            country['properties'] = {'name' : r['country_name'], 'project_amount' : r['total_projects']}
            country['geometry'] = helper.find_polygon(r['country_id'])

            activities.append(country)

        result = {}

        activity_result['features'] = activities
        return HttpResponse(ujson.dumps(activity_result), mimetype='application/json')



class Adm1RegionGeojsonResource(ModelResource):

    class Meta:
        #aid_type is used as dummy
        queryset = AidType.objects.all()
        resource_name = 'adm1-region-geojson'
        include_resource_uri = True
        cache = NoTransformCache()
        allowed_methods = ['get']


    def get_list(self, request, **kwargs):
        helper = CustomCallHelper()
        country_id = request.GET.get("country_id", None)

        cursor = connection.cursor()

        cursor.execute('SELECT r.adm1_code, r.name, r.polygon, r.geometry_type  '\
                'FROM geodata_adm1region r '\
                'WHERE r.country_id = "%s"' % (country_id))

        activity_result = {'type' : 'FeatureCollection', 'features' : []}

        activities = []

        results = helper.get_fields(cursor=cursor)
        for r in results:
            region = {}
            region['type'] = 'Feature'
            region['geometry'] = {'type' : r['geometry_type'], 'coordinates' : r['polygon']}
            region['properties'] = {'id' : r['adm1_code'], 'name' : r['name']}
            activities.append(region)

        result = {}

        activity_result['features'] = activities
        return HttpResponse(ujson.dumps(activity_result), mimetype='application/json')











class CountryActivitiesResource(ModelResource):

    class Meta:
        #aid_type is used as dummy
        queryset = AidType.objects.all()
        resource_name = 'country-activities'
        include_resource_uri = True
        cache = NoTransformCache()
        serializer = serializer = CsvSerializer()
        allowed_methods = ['get']

    def get_list(self, request, **kwargs):

        # check if call is cached using validator.is_cached
        # check if call contains flush, if it does the call comes from the cache updater and shouldn't return cached results

        helper = CustomCallHelper()
        country_q = helper.get_and_query(request, 'countries__in', 'c.code')
        budget_q_gte = request.GET.get('total_budget__gt', None)
        budget_q_lte = request.GET.get('total_budget__lt', None)
        region_q = helper.get_and_query(request, 'regions__in', 'r.code')
        sector_q = helper.get_and_query(request, 'sectors__in', 's.sector_id')
        donor_q = helper.get_and_query(request, 'participating_organisations__in', 'apo.organisation_id')
        organisation_q = helper.get_and_query(request, 'reporting_organisation__in', 'a.reporting_organisation_id')
        start_actual_q = helper.get_year_and_query(request, 'start_actual__in', 'a.start_actual')
        start_planned_q = helper.get_year_and_query(request, 'start_planned__in', 'a.start_planned')
        budget_q = ''
        limit = request.GET.get("limit", 999)
        offset = request.GET.get("offset", 0)
        order_by = request.GET.get("order_by", "country_name")
        order_asc_desc = request.GET.get("order_asc_desc", "ASC")
        country_query = request.GET.get("country", None)
        project_query = request.GET.get("query", None)
        format = request.GET.get("format", "json")
        include_unesco_empty = request.GET.get("include_unesco_empty", False)


        if budget_q_gte:
            budget_q += ' a.total_budget > "' + budget_q_gte + '" ) AND ('
        if budget_q_lte:
            budget_q += ' a.total_budget < "' + budget_q_lte + '" ) AND ('


        filter_string = ' AND (' + country_q + organisation_q + region_q + sector_q + budget_q + start_planned_q + start_actual_q + donor_q + ')'
        if 'AND ()' in filter_string:
            filter_string = filter_string[:-6]


        filter_region = ''
        if region_q:
            filter_region = 'LEFT JOIN iati_activityrecipientregion rr ON rr.activity_id = a.id LEFT JOIN geodata_region r ON rr.region_id = r.code '

        filter_sector = ''
        if sector_q:
            filter_sector = 'LEFT JOIN iati_activitysector s ON a.id = s.activity_id '

        filter_donor = ''
        if donor_q:
            filter_donor = 'LEFT JOIN iati_activityparticipatingorganisation as apo on a.id = apo.activity_id '
            filter_string += ' AND apo.role_id = "Funding" '

        if country_query:
            filter_string += 'AND c.name LIKE "%%' + country_query + '%%" '

        filter_project_query = ''
        if project_query:
            filter_project_query = 'LEFT JOIN iati_title as t on a.id = t.activity_id '
            filter_string += 'AND t.title LIKE "%%' + project_query + '%%" '

        cursor = connection.cursor()
        query = 'SELECT c.code as country_id, c.name as country_name, AsText(c.center_longlat) as location, count(a.id) as total_projects, sum(a.total_budget) as total_budget '\
                'FROM geodata_country c '\
                'LEFT JOIN iati_activityrecipientcountry rc ON rc.country_id = c.code '\
                'LEFT JOIN iati_activity a ON rc.activity_id = a.id '\
                '%s %s %s %s'\
                'WHERE c.code is not null %s'\
                'GROUP BY c.code ' \
                'ORDER BY %s %s ' \
                'LIMIT %s OFFSET %s' % (filter_region, filter_sector, filter_donor, filter_project_query, filter_string, order_by, order_asc_desc, limit, offset)



        if include_unesco_empty and organisation_q:
            query = query.replace(organisation_q, "")
            query = query.replace(' AND (' + organisation_q[:-6], "")
            query = query.replace(organisation_q[:-6], "")
            query = query.replace("LEFT JOIN iati_activity a ON rc.activity_id = a.id", "LEFT JOIN iati_activity a ON rc.activity_id = a.id AND " + organisation_q[:-8])
            query = query.replace("WHERE ", "WHERE unesco_region_id is not null AND ")
            print query

        cursor.execute(query)

        activities = []

        results = helper.get_fields(cursor=cursor)
        for r in results:
            country = {}
            country['id'] = r['country_id']
            country['name'] = r['country_name']
            country['total_projects'] = r['total_projects']

            loc = r['location']
            if loc:

                loc = loc.replace("POINT(", "")
                loc = loc.replace(")", "")
                loc_array = loc.split(" ")
                longitude = loc_array[0]
                latitude = loc_array[1]
            else:
                longitude = None
                latitude = None

            country['latitude'] = latitude
            country['longitude'] = longitude
            country['total_budget'] = r['total_budget']
            activities.append(country)

        return_json = {}
        return_json["objects"] = activities

        cursor = connection.cursor()
        query = 'SELECT c.code '\
                'FROM geodata_country c '\
                'LEFT JOIN iati_activityrecipientcountry rc ON rc.country_id = c.code '\
                'LEFT JOIN iati_activity a ON rc.activity_id = a.id '\
                '%s %s %s %s'\
                'WHERE c.code is not null %s'\
                'GROUP BY c.code ' % (filter_region, filter_sector, filter_donor, filter_project_query, filter_string)

        if include_unesco_empty and organisation_q:
            query = query.replace(organisation_q, "")
            query = query.replace(' AND (' + organisation_q[:-6], "")
            query = query.replace(organisation_q[:-6], "")
            query = query.replace("LEFT JOIN iati_activity a ON rc.activity_id = a.id", "LEFT JOIN iati_activity a ON rc.activity_id = a.id AND " + organisation_q[:-8])
            query = query.replace("WHERE ", "WHERE unesco_region_id is not null AND ")
            print query

        cursor.execute(query)
        results2 = helper.get_fields(cursor=cursor)


        return_json["meta"] = {"total_count": len(results2)}

        if format == "json":
            return HttpResponse(ujson.dumps(return_json), mimetype='application/json')

        if format == "xml":
            return HttpResponse(xmlrpclib.dumps(return_json), mimetype='application/xml')

        if format == "csv":
            csvh = CsvHelper()
            csv_content = csvh.to_csv(return_json)
            return HttpResponse(csv_content, mimetype='text/csv')



class RegionActivitiesResource(ModelResource):

    class Meta:
        #aid_type is used as dummy
        queryset = AidType.objects.all()
        resource_name = 'region-activities'
        include_resource_uri = True
        cache = NoTransformCache()
        allowed_methods = ['get']


    def get_list(self, request, **kwargs):

        # check if call is cached using validator.is_cached
        # check if call contains flush, if it does the call comes from the cache updater and shouldn't return cached results
        validator = Validator()
        cururl = request.META['PATH_INFO'] + "?" + request.META['QUERY_STRING']

        if not 'flush' in cururl and validator.is_cached(cururl):
            return HttpResponse(validator.get_cached_call(cururl), mimetype='application/json')

        helper = CustomCallHelper()
        # country_q = helper.get_and_query(request, 'countries__in', 'c.code')
        budget_q_gte = request.GET.get('total_budget__gt', None)
        budget_q_lte = request.GET.get('total_budget__lt', None)
        region_q = helper.get_and_query(request, 'regions__in', 'r.code')
        sector_q = helper.get_and_query(request, 'sectors__in', 's.sector_id')
        organisation_q = helper.get_and_query(request, 'reporting_organisation__in', 'a.reporting_organisation_id')
        budget_q = ''
        limit = request.GET.get("limit", 999)
        offset = request.GET.get("offset", 0)
        order_by = request.GET.get("order_by", "region_name")
        order_asc_desc = request.GET.get("order_asc_desc", "ASC")
        start_actual_q = helper.get_year_and_query(request, 'start_actual__in', 'a.start_actual')
        start_planned_q = helper.get_year_and_query(request, 'start_planned__in', 'a.start_planned')
        vocabulary_q = helper.get_and_query(request, "vocabulary__in", "rv.code")
        region_query = request.GET.get("region", None)
        project_query = request.GET.get("query", None)
        donor_q = helper.get_and_query(request, 'participating_organisations__in', 'apo.organisation_id')

        if budget_q_gte:
            budget_q += ' a.total_budget > "' + budget_q_gte + '" ) AND ('
        if budget_q_lte:
            budget_q += ' a.total_budget < "' + budget_q_lte + '" ) AND ('


        filter_string = ' AND (' + organisation_q + region_q + sector_q + budget_q + start_planned_q + start_actual_q + vocabulary_q + donor_q + ')'
        if 'AND ()' in filter_string:
            filter_string = filter_string[:-6]

        filter_sector = ''
        if sector_q:
            filter_sector = 'LEFT JOIN iati_activitysector s ON a.id = s.activity_id '

        filter_vocabulary = ''
        if vocabulary_q:
            filter_vocabulary = "LEFT JOIN iati_regionvocabulary rv ON r.region_vocabulary_id = rv.code "

        if region_query:
            filter_string += 'AND r.name LIKE "%%' + region_query + '%%" '

        filter_project_query = ''
        if project_query:
            filter_project_query = 'LEFT JOIN iati_title as t on a.id = t.activity_id '
            filter_string += 'AND t.title LIKE "%%' + project_query + '%%" '

        filter_donor = ''
        if donor_q:
            filter_donor = 'LEFT JOIN iati_activityparticipatingorganisation as apo on a.id = apo.activity_id '
            filter_string += ' AND apo.role_id = "Funding" '


        cursor = connection.cursor()
        query = 'SELECT r.code as region_id, r.name as region_name, AsText(r.center_longlat) as location, count(a.id) as total_projects, sum(a.total_budget) as total_budget '\
                'FROM iati_activity a '\
                'LEFT JOIN iati_activityrecipientregion rr ON rr.activity_id = a.id '\
                'LEFT JOIN geodata_region r ON rr.region_id = r.code '\
                '%s %s %s %s'\
                'WHERE r.code is not null %s'\
                'GROUP BY r.code ' \
                'ORDER BY %s %s ' \
                'LIMIT %s OFFSET %s' % (filter_sector, filter_vocabulary, filter_project_query, filter_donor, filter_string, order_by, order_asc_desc, limit, offset)
        print query
        cursor.execute(query)

        activities = []

        results = helper.get_fields(cursor=cursor)
        for r in results:
            region = {}
            region['id'] = r['region_id']
            region['name'] = r['region_name']
            region['total_projects'] = r['total_projects']

            loc = r['location']
            if loc:

                loc = loc.replace("POINT(", "")
                loc = loc.replace(")", "")
                loc_array = loc.split(" ")
                longitude = loc_array[0]
                latitude = loc_array[1]
            else:
                longitude = None
                latitude = None

            region['latitude'] = latitude
            region['longitude'] = longitude
            region['total_budget'] = r['total_budget']
            activities.append(region)

        return_json = {}
        return_json["objects"] = activities

        cursor = connection.cursor()
        query = 'SELECT r.code as region_id, r.name as region_name, AsText(r.center_longlat) as location, count(a.id) as total_projects, sum(a.total_budget) as total_budget '\
                'FROM iati_activity a '\
                'LEFT JOIN iati_activityrecipientregion rr ON rr.activity_id = a.id '\
                'LEFT JOIN geodata_region r ON rr.region_id = r.code '\
                '%s %s %s %s'\
                'WHERE r.code is not null %s'\
                'GROUP BY r.code ' % (filter_sector, filter_vocabulary, filter_project_query, filter_donor, filter_string)

        cursor.execute(query)
        results2 = helper.get_fields(cursor=cursor)

        return_json["meta"] = {"total_count": len(results2)}

        return HttpResponse(ujson.dumps(return_json), mimetype='application/json')





class GlobalActivitiesResource(ModelResource):

    class Meta:
        #aid_type is used as dummy
        queryset = AidType.objects.all()
        resource_name = 'global-activities'
        include_resource_uri = True
        cache = NoTransformCache()
        allowed_methods = ['get']


    def get_list(self, request, **kwargs):

        # check if call is cached using validator.is_cached
        # check if call contains flush, if it does the call comes from the cache updater and shouldn't return cached results
        validator = Validator()
        cururl = request.META['PATH_INFO'] + "?" + request.META['QUERY_STRING']

        if not 'flush' in cururl and validator.is_cached(cururl):
            return HttpResponse(validator.get_cached_call(cururl), mimetype='application/json')

        helper = CustomCallHelper()
        # country_q = helper.get_and_query(request, 'countries__in', 'c.code')
        budget_q_gte = request.GET.get('total_budget__gt', None)
        budget_q_lte = request.GET.get('total_budget__lt', None)
        region_q = helper.get_and_query(request, 'regions__in', 'r.code')
        sector_q = helper.get_and_query(request, 'sectors__in', 's.sector_id')
        organisation_q = helper.get_and_query(request, 'reporting_organisation__in', 'a.reporting_organisation_id')
        budget_q = ''
        limit = request.GET.get("limit", 999)
        offset = request.GET.get("offset", 0)
        order_by = request.GET.get("order_by", None)
        order_asc_desc = request.GET.get("order_asc_desc", "ASC")
        start_actual_q = helper.get_year_and_query(request, 'start_actual__in', 'a.start_actual')
        start_planned_q = helper.get_year_and_query(request, 'start_planned__in', 'a.start_planned')
        vocabulary_q = helper.get_and_query(request, "vocabulary__in", "rv.code")
        region_query = request.GET.get("region", None)
        project_query = request.GET.get("query", None)
        donor_q = helper.get_and_query(request, 'participating_organisations__in', 'apo.organisation_id')

        if budget_q_gte:
            budget_q += ' a.total_budget > "' + budget_q_gte + '" ) AND ('
        if budget_q_lte:
            budget_q += ' a.total_budget < "' + budget_q_lte + '" ) AND ('


        filter_string = ' AND (' + organisation_q + region_q + sector_q + budget_q + start_planned_q + start_actual_q + vocabulary_q + donor_q + ')'
        if 'AND ()' in filter_string:
            filter_string = filter_string[:-6]

        filter_sector = ''
        if sector_q:
            filter_sector = 'LEFT JOIN iati_activitysector s ON a.id = s.activity_id '

        filter_vocabulary = ''
        if vocabulary_q:
            filter_vocabulary = "LEFT JOIN iati_regionvocabulary rv ON r.region_vocabulary_id = rv.code "

        filter_region = ''
        if region_q:
            filter_region = 'LEFT JOIN iati_activityrecipientregion rr ON rr.activity_id = a.id LEFT JOIN geodata_region r ON rr.region_id = r.code '


        filter_project_query = ''
        if project_query:
            filter_project_query = 'LEFT JOIN iati_title as t on a.id = t.activity_id '
            filter_string += 'AND t.title LIKE "%%' + project_query + '%%" '

        filter_donor = ''
        if donor_q:
            filter_donor = 'LEFT JOIN iati_activityparticipatingorganisation as apo on a.id = apo.activity_id '
            filter_string += ' AND apo.role_id = "Funding" '


        cursor = connection.cursor()
        query = 'SELECT count(a.id) as total_projects, sum(a.total_budget) as total_budget '\
                'FROM iati_activity a '\
                '%s %s %s %s %s '\
                'WHERE a.scope_id = 1 %s'\
                'GROUP BY a.scope_id ' % (filter_sector, filter_vocabulary, filter_project_query, filter_donor, filter_region, filter_string)
        print query
        cursor.execute(query)

        activities = []

        results = helper.get_fields(cursor=cursor)
        for r in results:
            region = {}
            region['total_projects'] = r['total_projects']
            region['total_budget'] = r['total_budget']
            activities.append(region)

        return_json = {}
        return_json["objects"] = activities

        cursor = connection.cursor()
        query = 'SELECT count(a.id) as total_projects, sum(a.total_budget) as total_budget '\
                'FROM iati_activity a '\
                '%s %s %s %s %s '\
                'WHERE a.scope_id = 1 %s'\
                'GROUP BY a.scope_id ' % (filter_sector, filter_vocabulary, filter_project_query, filter_donor, filter_region, filter_string)

        cursor.execute(query)
        results2 = helper.get_fields(cursor=cursor)

        return_json["meta"] = {"total_count": len(results2)}

        return HttpResponse(ujson.dumps(return_json), mimetype='application/json')




class SectorActivitiesResource(ModelResource):

    class Meta:
        #aid_type is used as dummy
        queryset = AidType.objects.all()
        resource_name = 'sector-activities'
        include_resource_uri = True
        cache = NoTransformCache()
        allowed_methods = ['get']


    def get_list(self, request, **kwargs):

        helper = CustomCallHelper()
        country_q = helper.get_and_query(request, 'countries__in', 'c.code')
        budget_q_gte = request.GET.get('total_budget__gt', None)
        budget_q_lte = request.GET.get('total_budget__lt', None)
        region_q = helper.get_and_query(request, 'regions__in', 'r.code')
        sector_q = helper.get_and_query(request, 'sectors__in', 's.code')
        organisation_q = helper.get_and_query(request, 'reporting_organisation__in', 'a.reporting_organisation_id')
        budget_q = ''
        limit = request.GET.get("limit", 999)
        offset = request.GET.get("offset", 0)
        order_by = request.GET.get("order_by", "sector_name")
        order_asc_desc = request.GET.get("order_asc_desc", "ASC")
        query = request.GET.get("query", None)

        if budget_q_gte:
            budget_q += ' a.total_budget > "' + budget_q_gte + '" ) AND ('
        if budget_q_lte:
            budget_q += ' a.total_budget < "' + budget_q_lte + '" ) AND ('


        filter_string = ' AND (' + country_q + organisation_q + region_q + sector_q + budget_q + ')'
        if 'AND ()' in filter_string:
            filter_string = filter_string[:-6]


        filter_country = ''
        if country_q:
            filter_country = 'LEFT JOIN iati_activityrecipientcountry rc ON rc.activity_id = a.id LEFT JOIN geodata_country c ON rc.region_id = c.code '

        if region_q:
            filter_region = 'LEFT JOIN iati_activityrecipientregion rr ON rr.activity_id = a.id LEFT JOIN geodata_region r ON rr.region_id = r.code '
        else:
            filter_region = ''

        if query:
            filter_string += 'AND s.name LIKE "%%' + query + '%%" '

        cursor = connection.cursor()
        query = 'SELECT s.code as sector_id, s.name as sector_name, count(a.id) as total_projects, sum(a.total_budget) as total_budget '\
                'FROM iati_activity a '\
                'LEFT JOIN iati_activitysector acts ON acts.activity_id = a.id '\
                'LEFT JOIN iati_sector s ON s.code = acts.sector_id '\
                '%s %s '\
                'WHERE s.code is not null %s'\
                'GROUP BY s.code ' \
                'ORDER BY %s %s ' \
                'LIMIT %s OFFSET %s' % (filter_country, filter_region, filter_string, order_by, order_asc_desc, limit, offset)

        cursor.execute(query)

        activities = []

        results = helper.get_fields(cursor=cursor)
        for r in results:
            sector = {}
            sector['id'] = r['sector_id']
            sector['name'] = r['sector_name']
            sector['total_projects'] = r['total_projects']
            sector['total_budget'] = r['total_budget']
            activities.append(sector)

        return_json = {}
        return_json["objects"] = activities

        cursor = connection.cursor()
        query = 'SELECT s.code as sector_id '\
                'FROM iati_activity a '\
                'LEFT JOIN iati_activitysector acts ON acts.activity_id = a.id '\
                'LEFT JOIN iati_sector s ON s.code = acts.sector_id '\
                '%s %s '\
                'WHERE s.code is not null %s'\
                'GROUP BY s.code ' % (filter_country, filter_region, filter_string)

        cursor.execute(query)

        results2 = helper.get_fields(cursor=cursor)
        return_json["meta"] = {"total_count": len(results2)}

        return HttpResponse(ujson.dumps(return_json), mimetype='application/json')







class DonorActivitiesResource(ModelResource):

    class Meta:
        #aid_type is used as dummy
        queryset = AidType.objects.all()
        resource_name = 'donor-activities'
        include_resource_uri = True
        cache = NoTransformCache()
        allowed_methods = ['get']

    def get_list(self, request, **kwargs):

        # check if call is cached using validator.is_cached
        # check if call contains flush, if it does the call comes from the cache updater and shouldn't return cached results

        helper = CustomCallHelper()
        country_q = helper.get_and_query(request, 'countries__in', 'c.code')
        budget_q_gte = request.GET.get('total_budget__gt', None)
        budget_q_lte = request.GET.get('total_budget__lt', None)
        region_q = helper.get_and_query(request, 'regions__in', 'r.code')
        sector_q = helper.get_and_query(request, 'sectors__in', 's.sector_id')
        donor_q = helper.get_and_query(request, 'donors__in', 'apo.organisation_id')
        organisation_q = helper.get_and_query(request, 'reporting_organisation__in', 'a.reporting_organisation_id')
        start_actual_q = helper.get_year_and_query(request, 'start_actual__in', 'a.start_actual')
        start_planned_q = helper.get_year_and_query(request, 'start_planned__in', 'a.start_planned')
        budget_q = ''
        limit = request.GET.get("limit", 999)
        offset = request.GET.get("offset", 0)
        order_by = request.GET.get("order_by", "apo.name")
        order_asc_desc = request.GET.get("order_asc_desc", "ASC")
        query = request.GET.get("query", None)

        if budget_q_gte:
            budget_q += ' a.total_budget > "' + budget_q_gte + '" ) AND ('
        if budget_q_lte:
            budget_q += ' a.total_budget < "' + budget_q_lte + '" ) AND ('

        filter_string = ' AND (' + country_q + organisation_q + region_q + sector_q + budget_q + start_planned_q + start_actual_q + donor_q + ')'
        if 'AND ()' in filter_string:
            filter_string = filter_string[:-6]

        filter_string += ' AND apo.role_id = "Funding" '

        if query:
            filter_string += 'AND apo.name LIKE "%%' + query + '%%" '

        cursor = connection.cursor()
        query = 'SELECT apo.organisation_id as organisation_id, apo.name as organisation_name, count(a.id) as total_projects, sum(a.total_budget) as total_budget '\
                'FROM iati_activity a '\
                'LEFT JOIN iati_activityparticipatingorganisation as apo on a.id = apo.activity_id '\
                'WHERE apo.name is not null %s'\
                'GROUP BY apo.name ' \
                'ORDER BY %s %s ' \
                'LIMIT %s OFFSET %s' % (filter_string, order_by, order_asc_desc, limit, offset)
        cursor.execute(query)

        activities = []

        results = helper.get_fields(cursor=cursor)
        for r in results:
            donor = {}
            donor['id'] = r['organisation_id']
            donor['name'] = r['organisation_name']
            donor['total_projects'] = r['total_projects']
            donor['total_budget'] = r['total_budget']
            activities.append(donor)

        return_json = {}
        return_json["objects"] = activities



        query = 'SELECT apo.organisation_id as organisation_id '\
                'FROM iati_activity a '\
                'LEFT JOIN iati_activityparticipatingorganisation as apo on a.id = apo.activity_id '\
                'WHERE apo.name is not null %s'\
                'GROUP BY apo.name ' % (filter_string)

        cursor.execute(query)
        results2 = helper.get_fields(cursor=cursor)

        return_json["meta"] = {"total_count": len(results2)}


        return HttpResponse(ujson.dumps(return_json), mimetype='application/json')





