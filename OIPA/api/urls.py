from django.conf.urls import url
from django.conf.urls import include
from api import views

urlpatterns = [
    url(r'^$', views.welcome, name='api-root'),
    url(r'^health-check/', views.health_check, name='api-health-check'), 
    url(r'^activities/', include('api.activity.urls', namespace='activities')),
    url(r'^documents/', include('api.documents.urls', namespace='documents')),
    url(r'^codelists/', include('api.codelist.urls', namespace='codelists')),
    url(r'^budgets/', include('api.budget.urls', namespace='budgets')),
    url(r'^export/', include('api.export.urls', namespace='export')),
    url(r'^regions/', include('api.region.urls', namespace='regions')),
    url(r'^countries/', include('api.country.urls', namespace='countries')),
    url(r'^cities/', include('api.city.urls', namespace='cities')),
    url(r'^locations/', include('api.location.urls', namespace='locations')),
    url(r'^organisations/', include('api.organisation.urls', namespace='organisations')),
    url(r'^sectors/', include('api.sector.urls', namespace='sectors')),
    url(r'^transactions/', include('api.transaction.urls', namespace='transactions')),
    url(r'^results/', include('api.result.urls', namespace='results')),
    url(r'^datasets/', include('api.dataset.urls', namespace='datasets')),
    url(r'^publishers/', include('api.publisher.urls', namespace='publishers')),

    # TODO: no email confirmation? - 2016-10-18
    url(r'^auth/', include('rest_auth.urls')),
    url(r'^auth/registration/', include('rest_auth.registration.urls')),
]

