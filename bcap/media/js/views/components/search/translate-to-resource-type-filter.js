import arches from 'arches';
import ko from 'knockout';
import BaseFilter from 'views/components/search/base-filter';
import translateToResourceTypeFilterTemplate from 'templates/views/components/search/translate-to-resource-type-filter.htm';

var componentName = 'translate-to-resource-type-filter';

var viewModel = BaseFilter.extend({
    initialize: async function (options) {
        options.name = 'Translate to Resource Type Filter';
        BaseFilter.prototype.initialize.call(this, options);

        this.available_resource_types = ko.observableArray([]);
        this.is_loading_types = ko.observable(true);
        this.is_translating = ko.observable(false);
        this.original_filters = null;
        this.is_original_filters_stale = false;
        this.translation_error = ko.observable(null);
        this.translation_tag = ko.observable(null);
        this.is_query_set = false;
        this.is_updating_tag = false;

        var self = this;

        this.query.subscribe(function (new_query) {
            var has_ids = !!new_query['ids'];

            if (!self.is_query_set) {
                if (has_ids) {
                    self.is_original_filters_stale = true;
                } else {
                    self.original_filters = null;
                    self.is_original_filters_stale = false;
                    self.translation_error(null);
                    if (self.translation_tag()) {
                        self.is_updating_tag = true;
                        self.getFilterByType('term-filter-type').removeTag(
                            self.translation_tag(),
                        );
                        self.is_updating_tag = false;
                        self.translation_tag(null);
                    }
                    window.translation_source_mapping = {};
                    window.get_translation_source = null;
                }
            }
            self.is_query_set = false;
        }, this);

        var response = await fetch(
            arches.urls.root + 'api/translatable-resource-types',
            {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
            },
        );

        if (response.ok) {
            var data = await response.json();
            self.is_loading_types(false);
            if (data.status === 'success' && data.resource_types) {
                self.available_resource_types(data.resource_types);
            }
        } else {
            self.is_loading_types(false);
            console.error('Failed to fetch resource types');
        }

        this.searchFilterVms[componentName](this);
    },

    get_csrf_token: function () {
        var cookie_value = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, 10) === 'csrftoken=') {
                    cookie_value = decodeURIComponent(cookie.substring(10));
                    break;
                }
            }
        }
        return cookie_value;
    },

    capture_filters_from_query: function (query) {
        var excluded_keys = [
            'paging-filter',
            'ids',
            'tiles',
            'csrfmiddlewaretoken',
        ];
        var filters = {};

        for (var key in query) {
            if (
                query.hasOwnProperty(key) &&
                excluded_keys.indexOf(key) === -1
            ) {
                filters[key] = query[key];
            }
        }

        return filters;
    },

    translate_to_resource_type_by_id: function (graph_id) {
        var self = this;

        if (!graph_id) {
            self.translation_error('Please select a resource type.');
            return;
        }

        self.is_translating(true);
        self.translation_error(null);

        var current_query = self.query();
        var filters_to_use;

        if (self.original_filters !== null && !self.is_original_filters_stale) {
            filters_to_use = self.original_filters;
        } else {
            filters_to_use = self.capture_filters_from_query(current_query);
        }

        var search_params = new URLSearchParams();
        search_params.set('paging-filter', '1');
        search_params.set('target_graph_id', graph_id);

        for (var key in filters_to_use) {
            if (filters_to_use.hasOwnProperty(key) && filters_to_use[key]) {
                search_params.set(key, filters_to_use[key]);
            }
        }

        fetch(arches.urls.root + 'api/translate-to-resource-type', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': self.get_csrf_token(),
            },
            body: search_params.toString(),
        })
            .then(function (response) {
                return response.json();
            })
            .then(function (data) {
                self.is_translating(false);

                if (data.status === 'error') {
                    self.translation_error(data.message);
                    return;
                }

                if (data.resource_ids && data.resource_ids.length > 0) {
                    self.original_filters = filters_to_use;
                    self.is_original_filters_stale = false;
                    self.apply_resource_filter(
                        data.resource_ids,
                        data.source_mapping,
                        data.source_resource_type_name,
                        data.target_resource_type_name,
                    );
                } else {
                    self.translation_error(
                        'No related resources found for the selected type.',
                    );
                }
            })
            .catch(function (error) {
                self.is_translating(false);
                self.translation_error('An error occurred during translation.');
                console.error('Translation error:', error);
            });
    },

    apply_resource_filter: function (
        resource_ids,
        source_mapping,
        source_name,
        target_name,
    ) {
        var self = this;

        if (self.translation_tag()) {
            self.is_updating_tag = true;
            self.getFilterByType('term-filter-type').removeTag(
                self.translation_tag(),
            );
            self.is_updating_tag = false;
        }

        var tag_text = source_name + ' \u2192 ' + target_name;
        self.translation_tag(tag_text);
        self.getFilterByType('term-filter-type').addTag(
            tag_text,
            self.name,
            ko.observable(false),
        );

        var queryObj = {};
        queryObj['paging-filter'] = '1';
        queryObj['ids'] = JSON.stringify(resource_ids);

        window.translation_source_mapping = source_mapping || {};
        window.get_translation_source = function (resourceinstanceid) {
            var sources = window.translation_source_mapping[resourceinstanceid];
            if (sources && sources.length > 0) {
                return sources;
            }
            return null;
        };

        self.is_query_set = true;
        self.query(queryObj);
    },

    clear: function () {
        var self = this;

        if (self.is_updating_tag) {
            return;
        }

        if (self.translation_tag()) {
            self.is_updating_tag = true;
            self.getFilterByType('term-filter-type').removeTag(
                self.translation_tag(),
            );
            self.is_updating_tag = false;
            self.translation_tag(null);
        }

        window.translation_source_mapping = {};
        window.get_translation_source = null;
        self.translation_error(null);

        var queryObj = {};
        queryObj['paging-filter'] = '1';

        if (self.original_filters && !self.is_original_filters_stale) {
            for (var key in self.original_filters) {
                if (
                    self.original_filters.hasOwnProperty(key) &&
                    self.original_filters[key]
                ) {
                    queryObj[key] = self.original_filters[key];
                }
            }
        }

        self.original_filters = null;
        self.is_original_filters_stale = false;
        self.is_query_set = true;
        self.query(queryObj);
    },
});

export default ko.components.register(componentName, {
    viewModel: viewModel,
    template: translateToResourceTypeFilterTemplate,
});
