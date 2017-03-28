# Return parser functions for generic elements
from iati import models
import iati_codelists.models as codelist_models
from iati.parser.exceptions import RequiredFieldError
import functools


def provider_org(self, parent_model, provider_model, fk_name):
    """
    parent_model: the model to which the provider_org will be applied
    provider_model: The provider_org model
    fk_name: the name of the foreign key back to the parent_model
    """

    def func(element):
        ref = element.attrib.get('ref', '')
        org_type = self.get_or_none(codelist_models.OrganisationType, code=element.attrib.get('type'))
        provider_activity_id = element.attrib.get('provider-activity-id', None)
        if provider_activity_id:
            provider_activity_id = provider_activity_id.strip()
        provider_activity = self.get_or_none(models.Activity, iati_identifier=provider_activity_id)

        normalized_ref = self._normalize(ref)
        organisation = self.get_or_none(models.Organisation, organisation_identifier=ref)

        setattr(provider_model, fk_name, parent_model)
        provider_model.ref = ref
        provider_model.type = org_type
        provider_model.normalized_ref = normalized_ref
        provider_model.organisation = organisation
        provider_model.provider_activity_ref = provider_activity_id
        provider_model.provider_activity = provider_activity

        self.register_model(type(provider_model).__name__, provider_model)

        return element

    return func

def receiver_org(self, parent_model, receiver_model, fk_name):
    """
    parent_model: the model to which the receiver_org will be applied
    receiver_model: The receiver_org model
    fk_name: the name of the foreign key back to the parent_model
    """

    def func(element):
        ref = element.attrib.get('ref', '')
        org_type = self.get_or_none(codelist_models.OrganisationType, code=element.attrib.get('type'))
        receiver_activity_id = element.attrib.get('receiver-activity-id', None)
        if receiver_activity_id:
            receiver_activity_id = receiver_activity_id.strip()
        receiver_activity = self.get_or_none(models.Activity, iati_identifier=receiver_activity_id)

        normalized_ref = self._normalize(ref)
        organisation = self.get_or_none(models.Organisation, organisation_identifier=ref)

        setattr(receiver_model, fk_name, parent_model)
        receiver_model.ref = ref
        receiver_model.type = org_type
        receiver_model.normalized_ref = normalized_ref
        receiver_model.organisation = organisation
        receiver_model.receiver_activity_ref = receiver_activity_id
        receiver_model.receiver_activity = receiver_activity

        self.register_model(type(receiver_model).__name__, receiver_model)

        return element

    return func

def activity_field(self, model, activity_model):
    def func(element):

        model.activity = activity_model
        self.register_model(model)

        return element

    return func

def codelist_field(self, model, codelist_model):
    def func(element):
        code = element.attrib.get('code')
        code_model = self.get_or_none(codelist_model, code=code)

        if not code_model:
            raise RequiredFieldError(
                model,
                "code", 
                "Unspecified or invalid.")

        model.code = code_model

        return element

    return func

def compose(*functions):
    return functools.reduce(lambda f, g: lambda x: f(g(x)), functions, lambda x: x)

def parent(parent_model, fk):
    """
    set parent model fk on model
    """
    def func(model):
        setattr(model, fk, parent_model)
        return model

    return func

def code(self, codelist_model):
    def func(model, element):
        code = element.attrib.get('code')
        code_model = self.get_or_none(codelist_model, code=code)

        if not code_model: 
            raise RequiredFieldError(
                model,
                "code",
                element)

        model.code = code_model

        return model

    return func

