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
    # custom_search_path = "custom_values"
    initialized = False
    arch_site_proxy = None
    site_visit_proxy = None
    hria_discontinued_proxy = None

    # def __init__(self):
    #     pass

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
            # site_visits = CustomSearchValue.arch_site_proxy.get_related_resources(
            #     resourceinstance, GraphSlugs.SITE_VISIT
            # )
            # site_visit_nodes=[sva.]
            # CustomSearchValue.site_visit_proxy.get_value_from_node()
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
                    (
                        f"""adif_{hdda.SITE_ENTERED_BY}:{CustomSearchValue.hria_discontinued_proxy.get_value_from_node(
                        hdda.SITE_ENTERED_BY,
                        hria_discontinued[0].resourceinstanceid,
                    )}"""
                    )
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
            # print(custom_values)
            # sample_ids = CustomSearchValue.collection_event_proxy.get_sample_ids(
            #     resourceinstance
            # )
            #
            # custom_values |= set(
            #     CustomSearchValue.fossil_sample_proxy.get_scientific_names_from_samples(
            #         sample_ids
            #     )
            # )
            # custom_values |= set(
            #     CustomSearchValue.fossil_sample_proxy.get_common_names_from_samples(
            #         sample_ids
            #     )
            # )
            #
            # custom_value_aliases = [
            #     (fsa.MINIMUM_TIME, fsa.MINIMUM_TIME_UNCERTAIN),
            #     (fsa.MAXIMUM_TIME, fsa.MAXIMUM_TIME_UNCERTAIN),
            #     (fsa.GEOLOGICAL_GROUP, fsa.GEOLOGICAL_GROUP_UNCERTAIN),
            #     (fsa.GEOLOGICAL_FORMATION, fsa.GEOLOGICAL_FORMATION_UNCERTAIN),
            #     (fsa.GEOLOGICAL_MEMBER, fsa.GEOLOGICAL_MEMBER_UNCERTAIN),
            #     (fsa.FOSSIL_ABUNDANCE, None),
            #     (fsa.FOSSIL_SIZE_CATEGORY, None),
            #     (fsa.FOSSIL_SAMPLE_SIGNIFICANT, None),
            #     (fsa.STORAGE_REFERENCE, None),
            # ]
            # for alias in custom_value_aliases:
            #     custom_values |= set(
            #         CustomSearchValue.fossil_sample_proxy.get_values_from_samples(
            #             samples=sample_ids,
            #             node_alias=alias[0],
            #             uncertainty_alias=alias[1],
            #             flatten=True,
            #         )
            #     )

        # print("Adding custom values: %s" % custom_values)
        if CustomSearchValue.custom_search_path not in document:
            document[CustomSearchValue.custom_search_path] = []

        for custom_value in custom_values:
            if custom_value:
                document[CustomSearchValue.custom_search_path].append(
                    {"custom_value": custom_value}
                )

        # print("Document: %s" % document)

    @staticmethod
    def create_nested_custom_filter(term, original_element):
        if "nested" not in original_element:
            return original_element
        # print("Original element: %s" % original_element)
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
        # print("Search query before: %s" % search_query)
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
        # print("Search query after: %s" % search_query)

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
