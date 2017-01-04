import json
from iati_synchroniser.models import Publisher, Dataset
import urllib2
import datetime


DATASET_URL = 'https://iatiregistry.org/api/action/package_search?rows=200&{options}'
PUBLISHER_URL = 'https://iatiregistry.org/api/action/organization_list?all_fields=true&include_extras=true&limit=200&{options}'

class DatasetSyncer():

    # def __init__(self):
    #     """
    #     Prefetch data, to minify amount of DB queries
    #     """
    #     source_url_tuples = Dataset.objects.values_list('id')
    #     self.source_urls = [url[0] for url in source_url_tuples]

    #     publisher_id_tuples = Publisher.objects.values_list('id')
    #     self.publisher_ids = [pub_id[0] for pub_id in publisher_id_tuples]


    def get_data(self, url):
        req = urllib2.Request(url)
        opener = urllib2.build_opener()
        f = opener.open(req)
        json_objects = json.load(f)
        return json_objects

    def get_val_in_list_of_dicts(self, key, dicts):
        return next((item for item in dicts if item.get("key") and item["key"] == key), None)

    def synchronize_with_iati_api(self):
        """
        First update all publishers. 
        Then all datasets.
        """

        # parse publishers
        offset = 0

        while True:
            # get data
            options = 'offset={}'.format(offset)
            offset += 200
            page_url = PUBLISHER_URL.format(options=options)
            results = self.get_data(page_url)

            for publisher in results['result']:
                self.update_or_create_publisher(publisher)
            # check if done
            if len(results['result']) == 0:
                break

        # parse datasets
        offset = 0

        while True:
            # get data
            options = 'start={}'.format(offset)
            offset += 200
            page_url = DATASET_URL.format(options=options)
            results = self.get_data(page_url)
            # update dataset
            for dataset in results['result']['results']:
                self.update_or_create_dataset(dataset)
            # check if done
            if len(results['result']['results']) == 0:
                break

        # remove deprecated publishers / datasets
        self.remove_deprecated()

    def update_or_create_publisher(self, publisher):
        """
        
        """
        obj, created = Publisher.objects.update_or_create(
            id=publisher['id'],
            defaults={
                'publisher_iati_id': publisher['publisher_iati_id'],
                'name': publisher['name'], 
                'display_name': publisher['display_name']
            }
        )

        return obj

    def update_or_create_dataset(self, dataset):
        """
        
        """
        filetype_name = self.get_val_in_list_of_dicts('filetype', dataset['extras'])
        
        if  filetype_name and filetype_name.get('value') == 'organisation':
            filetype = 2
        else:
            filetype = 1
        
        iati_version = self.get_val_in_list_of_dicts('iati_version', dataset['extras'])
        if iati_version:
            iati_version = iati_version.get('value')
        else:
            iati_version = ''

        # trololo edge cases
        if not len(dataset['resources']) or not dataset['organization']:
            return
        obj, created = Dataset.objects.update_or_create(
            id=dataset['id'],
            defaults={
                'name': dataset['name'],
                'title': dataset['title'][0:254],
                'filetype': filetype,
                'publisher_id': dataset['organization']['id'],
                'source_url': dataset['resources'][0]['url'],
                'iati_version': iati_version,
                'last_found_in_registry': datetime.datetime.now(),
                'added_manually': False
            }
        )

    def remove_deprecated(self):
        """
        remove old publishers and datasets that used an id between 1-5000 
        instead of the IATI Registry UUID (thats way over string length 5, pretty hacky code here tbh but its a one time solution)
        """
        for p in Publisher.objects.all():
            if len(p.id) < 5:
                p.delete()

        for d in Dataset.objects.all():
            if len(p.id) < 5:
                p.delete()

