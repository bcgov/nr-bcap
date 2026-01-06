define([
    'arches',
    'knockout',
    'templates/views/components/search/translate-to-resource-type-filter.htm',
], function (arches, ko, translateToResourceTypeFilterTemplate) {
    let component_name = 'translate-to-resource-type-filter';

    let TranslateToResourceTypeFilter = function (params) {
        let self = this;

        self.name = 'Translate to Resource Type';
        self.available_resource_types = ko.observableArray([]);
        self.is_loading_types = ko.observable(true);
        self.is_translating = ko.observable(false);
        self.selected_resource_type = ko.observable(null);
        self.translation_error = ko.observable(null);
        self.translation_result = ko.observable(null);

        self.get_csrf_token = function () {
            let cookie_value = null;
            if (document.cookie && document.cookie !== '') {
                let cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    let cookie = cookies[i].trim();
                    if (cookie.substring(0, 10) === 'csrftoken=') {
                        cookie_value = decodeURIComponent(cookie.substring(10));
                        break;
                    }
                }
            }
            return cookie_value;
        };

        self.load_resource_types = function () {
            self.is_loading_types(true);

            fetch(arches.urls.root + 'api/translatable-resource-types', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            })
                .then(function (response) {
                    return response.json();
                })
                .then(function (data) {
                    self.is_loading_types(false);

                    if (data.status === 'success' && data.resource_types) {
                        self.available_resource_types(data.resource_types);

                        if (data.resource_types.length > 0) {
                            self.selected_resource_type(
                                data.resource_types[0].graphid,
                            );
                        }
                    }
                })
                .catch(function (error) {
                    self.is_loading_types(false);
                    console.error('Error loading resource types:', error);
                });
        };

        self.translate_to_resource_type = function () {
            if (!self.selected_resource_type()) {
                self.translation_error('Please select a resource type.');
                return;
            }

            self.is_translating(true);
            self.translation_error(null);
            self.translation_result(null);

            let search_params = new URLSearchParams(window.location.search);
            search_params.set('target_graph_id', self.selected_resource_type());

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
                        self.translation_result({
                            total: data.total_translated,
                            original: data.original_count,
                            target_name: data.target_resource_type_name,
                        });

                        self.apply_resource_filter(data.resource_ids);
                    } else {
                        self.translation_error(
                            'No related resources found for the selected type.',
                        );
                    }
                })
                .catch(function (error) {
                    self.is_translating(false);
                    self.translation_error(
                        'An error occurred during translation.',
                    );
                    console.error('Translation error:', error);
                });
        };

        self.apply_resource_filter = function (resource_ids) {
            let ids_json = JSON.stringify(resource_ids);

            let new_params = new URLSearchParams();
            new_params.set('ids', ids_json);

            let new_url =
                window.location.pathname + '?' + new_params.toString();
            window.location.href = new_url;
        };

        self.clear = function () {
            self.translation_error(null);
            self.translation_result(null);
        };

        self.load_resource_types();
    };

    return ko.components.register(component_name, {
        viewModel: TranslateToResourceTypeFilter,
        template: translateToResourceTypeFilterTemplate,
    });
});
