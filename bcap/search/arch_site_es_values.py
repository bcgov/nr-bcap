from arches.app.search.elasticsearch_dsl_builder import (
    Bool,
    Match,
    Nested,
)
from bcap.util.bcap_aliases import GraphSlugs

from bcap.util.aliases.site_visit import SiteVisitAliases as sva
from bcap.util.aliases.hria_discontinued_data import HriaDiscontinuedDataAliases as hdda
from bcap.util.business_data_proxy import (
    ArchaeologicalSiteDataProxy,
    SiteVisitDataProxy,
    HriaDiscontinuedDataProxy,
)
from arches.app.search.es_mapping_modifier import EsMappingModifier


class CustomSearchValue(EsMappingModifier):
    initialized = False
    arch_site_proxy = None
    site_visit_proxy = None
    hria_discontinued_proxy = None

    @staticmethod
    def initialize():
        if not CustomSearchValue.initialized:
            CustomSearchValue.arch_site_proxy = ArchaeologicalSiteDataProxy()
            CustomSearchValue.site_visit_proxy = SiteVisitDataProxy()
            CustomSearchValue.hria_discontinued_proxy = HriaDiscontinuedDataProxy()
            CustomSearchValue.initialized = True

    @staticmethod
    def add_search_terms(resourceinstance, document, terms):
        CustomSearchValue.initialize()
        custom_values = set(())

        if resourceinstance.graph.slug == GraphSlugs.ARCHAEOLOGICAL_SITE:
            hria_discontinued = CustomSearchValue.arch_site_proxy.get_related_resources(
                resourceinstance, GraphSlugs.HRIA_DISCONTINUED_DATA
            )

            if len(
                hria_discontinued
            ) > 0 and CustomSearchValue.hria_discontinued_proxy.get_value_from_node(
                hdda.UNREVIEWED_ADIF_RECORD,
                hria_discontinued[0].resourceinstanceid,
                use_boolean_label=False,
            ):
                custom_values |= {"adif"}
                custom_values |= {
                    f"""adif_{hdda.SITE_ENTERED_BY}:{CustomSearchValue.hria_discontinued_proxy.get_value_from_node(
                        hdda.SITE_ENTERED_BY,
                        hria_discontinued[0].resourceinstanceid,
                    )}"""
                }

            site_visits = CustomSearchValue.arch_site_proxy.get_related_resources(
                resourceinstance, GraphSlugs.SITE_VISIT
            )
            site_visit_attributes = [
                sva.ASSOCIATED_PERMIT,
                sva.CULTURAL_MATERIAL_TYPE,
                sva.SITE_FORM_AUTHORS,
                sva.ARCHAEOLOGICAL_CULTURE,
                sva.BIOGEOGRAPHY_TYPE,
                sva.TEAM_MEMBER,
                sva.MEMBER_ROLES,
            ]

            for site_visit in site_visits:
                for attribute in site_visit_attributes:
                    value = CustomSearchValue.site_visit_proxy.get_value_from_node(
                        attribute, site_visit.resourceinstanceid
                    )
                    if value and type(value) is list:
                        custom_values |= set([f"{attribute}:{val}" for val in value])
                    elif value:
                        custom_values |= {f"{attribute}:{value}"}

        if CustomSearchValue.custom_search_path not in document:
            document[CustomSearchValue.custom_search_path] = []

        for custom_value in custom_values:
            if custom_value:
                document[CustomSearchValue.custom_search_path].append(
                    {"custom_value": custom_value}
                )

    @staticmethod
    def create_nested_custom_filter(term, original_element):
        if "nested" not in original_element:
            return original_element
        document_key = CustomSearchValue.custom_search_path
        custom_filter = Bool()
        custom_filter.should(
            Match(
                field="%s.custom_value" % document_key,
                query=term["value"],
                type="phrase_prefix",
            )
        )
        custom_filter.should(
            Match(
                field="%s.custom_value.folded" % document_key,
                query=term["value"],
                type="phrase_prefix",
            )
        )
        nested_custom_filter = Nested(path=document_key, query=custom_filter)
        new_must_element = Bool()
        new_must_element.should(original_element)
        new_must_element.should(nested_custom_filter)
        new_must_element.dsl["bool"]["minimum_should_match"] = 1
        return new_must_element

    @staticmethod
    def add_search_filter(
        search_query, term, permitted_nodegroups, include_provisional
    ):
        original_must_filter = search_query.dsl["bool"]["must"]
        search_query.dsl["bool"]["must"] = []
        for must_element in original_must_filter:
            search_query.must(
                CustomSearchValue.create_nested_custom_filter(term, must_element)
            )

        original_must_filter = search_query.dsl["bool"]["must_not"]
        search_query.dsl["bool"]["must_not"] = []
        for must_element in original_must_filter:
            search_query.must_not(
                CustomSearchValue.create_nested_custom_filter(term, must_element)
            )

    @staticmethod
    def get_mapping_definition():
        return {
            "type": "nested",
            "properties": {
                "custom_value": {
                    "type": "text",
                    "fields": {
                        "raw": {"type": "keyword", "ignore_above": 256},
                        "folded": {"type": "text", "analyzer": "folding"},
                    },
                }
            },
        }
