import type { AliasedNodeData } from '@/arches_component_lab/types.ts';

import type {
    ReferenceSelectValue,
    ReferenceSelectNodeValue,
    ReferenceSelectDetails,
} from '@/arches_controlled_lists/datatypes/reference-select/types.js';

export interface TileReference {
    resourceinstance_id: string;
    tileid: string;
    nodegroupid: string;
    data: object;
}

export interface DetailsData {
    resourceinstance_id: string;
    displayname: string;
    graph_slug: string;
}

export interface NumberValue extends AliasedNodeData {
    display_value: string;
    node_value: number | null;
    details: never[];
}

export interface BooleanValue extends AliasedNodeData {
    display_value: string;
    node_value: boolean | null;
    details: never[];
}

export interface GeoJSONFeatureCollectionValue extends AliasedNodeData {
    display_value: string;
    node_value: {
        type: 'FeatureCollection';
        features: unknown[];
    } | null;
    details: never[];
}

export type NullableReferenceSelectValue =
    | ReferenceSelectValue
    | (Omit<ReferenceSelectValue, 'node_value'> & {
          node_value: ReferenceSelectNodeValue[] | null;
          details: ReferenceSelectDetails[] | [];
      });

export interface BcapURLs {
    add_resource: (graphid: string) => string;

    'api-map-data': string;
    api_bulk_disambiguated_resource_instance: string;
    api_bulk_resource_report: string;
    api_card: string;
    api_card_x_node_x_widget: (
        graph_slug: string,
        node_alias: string,
    ) => string;
    api_card_x_node_x_widget_list_from_nodegroup: (
        graph_slug: string,
        nodegroup_alias: string,
    ) => string;
    api_concepts_tree: (graph_slug: string, node_alias: string) => string;
    api_get_frontend_i18n_data: string;
    api_get_nodegroup_tree: string;
    api_instance_permissions: string;
    api_languages_with_request_language: string;
    api_login: string;
    api_logout: string;
    api_node_value: string;
    api_nodegroup: (nodegroupid: string) => string;
    api_nodes: (nodeid: string) => string;
    api_plugins: string;
    api_relatable_resources: (graph_slug: string, node_alias: string) => string;
    api_resource_instance_lifecycle_state: (resourceid: string) => string;
    api_resource_instance_lifecycle_states: string;
    api_resource_report: (resourceid: string) => string;
    api_resources: (resourceid: string) => string;
    api_search_component_data: string;
    api_tile: (
        graph_slug: string,
        nodegroup_alias: string,
        tile_id: string,
    ) => string;
    api_tile_blank: (graph_slug: string, nodegroup_alias: string) => string;
    api_tile_list_create: (
        graph_slug: string,
        nodegroup_alias: string,
        resource_instance_id: string,
    ) => string;
    api_tiles: (tileid: string) => string;
    api_user: string;
    api_user_incomplete_workflows: string;

    apply_functions: string;
    auth: string;
    buffer: string;
    card: string;
    change_password: string;
    clear_user_permission_cache: string;
    clone_graph: (graphid: string) => string;
    concept: string;
    concept_make_collection: string;
    concept_manage_parents: string;
    concept_search: string;
    concept_tree: string;
    concept_value: string;
    config: string;
    confirm_delete: string;

    controlled_list: (listid: string) => string;
    controlled_list_add: string;
    controlled_list_item: (itemid: string) => string;
    controlled_list_item_add: string;
    controlled_list_item_image: (imageid: string) => string;
    controlled_list_item_image_add: string;
    controlled_list_item_image_metadata: (metadataid: string) => string;
    controlled_list_item_image_metadata_add: string;
    controlled_list_item_value: (valueid: string) => string;
    controlled_list_item_value_add: string;
    controlled_list_options: string;
    controlled_lists: string;

    delete_graph: (graphid: string) => string;
    delete_instances: (graphid: string) => string;
    delete_provisional_tile: string;
    delete_published_graph: string;
    dismiss_notifications: string;
    download_files: string;
    draft_graph_api: (graphid: string) => string;
    dropdown: string;
    edit_history: string;
    etl_manager: string;
    export_concept: string;
    export_concept_collections: string;
    export_graph: (graphid: string) => string;
    export_mapping_file: (graphid: string) => string;
    export_results: string;

    feature_popup_content: string;
    from_sparql_endpoint: string;
    function_manager: (graphid: string) => string;
    geojson: string;
    get_api_resource_edit_log: (resourceId: string) => string;
    get_concept_collections: string;
    get_domain_connections: (graphid: string) => string;
    get_dsl: string;
    get_export_file: string;
    get_notification_types: string;
    get_notifications: string;
    get_pref_label: string;
    get_resource_edit_log: (graphid: string) => string;
    get_user_names: string;

    graph: string;
    graph_designer: (graphid: string) => string;
    graph_is_active_api: (graphid: string) => string;
    graph_nodes: (graphid: string) => string;
    graph_settings: (graphid: string) => string;
    graphs_api: string;

    help_template: string;
    home: string;
    icons: string;
    iiifannotationnodes: string;
    iiifannotations: string;
    iiifmanifest: string;
    languages: string;
    manifest_manager: string;
    media: string;

    model_history: (graphid: string) => string;
    mvt: (nodeid: string) => string;

    node: string;
    node_layer: string;
    nodegroup: string;
    ontology_properties: string;
    paged_dropdown: string;
    permission_data: string;
    permission_manager_data: string;
    plugin: (pluginid: string) => string;
    publish_graph: (graphid: string) => string;

    rdm: string;
    reindex: string;
    relatable_resources: string;
    related_resource_candidates: string;
    related_resources: string;
    remove_functions: string;
    reorder_cards: string;
    reorder_nodes: string;
    reorder_tiles: string;
    resource: string;
    resource_cards: string;
    resource_copy: string;
    resource_data: string;
    resource_descriptors: string;
    resource_edit_log: string;
    resource_editor: string;
    resource_permission_data: string;
    resource_report: string;
    resource_tiles: string;

    restore_state_from_serialized_graph: (graphid: string) => string;
    revert_graph: (graphid: string) => string;

    root: string;
    search_home: string;
    search_results: string;
    search_sparql_endpoint: string;
    search_terms: string;
    signup: string;
    thumbnail: (resourceid: string) => string;
    tile: string;
    tile_history: string;
    time_wheel_config: string;
    transaction_reverse: (transactionid: string) => string;
    transform_edtf_for_tile: string;
    two_factor_authentication_reset: string;
    update_notification_types: string;
    update_published_graph: string;
    update_published_graphs: (graphid: string) => string;

    uploadedfiles: string;
    url_subpath: string;
    validatejson: string;
    workflow_history: string;
}
