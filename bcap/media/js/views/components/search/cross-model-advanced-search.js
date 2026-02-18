import $ from 'jquery';
import _ from 'underscore';

import arches from 'arches';
import BaseFilter from 'views/components/search/base-filter';
import ko from 'knockout';
import koMapping from 'knockout-mapping';
import crossModelAdvancedSearchTemplate from 'templates/views/components/search/cross-model-advanced-search.htm';

let component_name = 'cross-model-advanced-search';

let view_model = BaseFilter.extend({
    initialize: function (options) {
        let self = this;

        options.name = 'Cross-Model Advanced Search Filter';
        BaseFilter.prototype.initialize.call(this, options);

        this.cards = [];
        this.card_lookup = {};
        this.datatype_lookup = {};
        this.drag_data = ko.observable(null);
        this.drag_over_add_group = ko.observable(null);
        this.drag_over_card = ko.observable(null);
        this.drag_over_group = ko.observable(null);
        this.drag_over_position = ko.observable(null);
        this.facet_filter_text = ko.observable('');
        this.graph_lookup = {};
        this.intersection_targets = ko.observableArray([]);
        this.is_searching = ko.observable(false);
        this.next_group_id = 1;
        this.result_operation = ko.observable('intersect');
        this.searchable_graphs = ko.observableArray();
        this.search_elapsed_time = ko.observable(null);
        this.search_start_time = null;
        this.search_timer_interval = null;
        this.sections = ko.observableArray();
        this.tag_id = 'Cross-Model Advanced Search';
        this.translate_mode = ko.observable('none');
        this.urls = arches.urls;
        this.widget_lookup = {};

        this.result_operation_options = [
            { value: 'intersect', label: 'Intersect' },
            { value: 'union', label: 'Union' },
        ];

        this.translate_mode_options = ko.computed(function () {
            let options = [{ value: 'none', label: 'Show Raw Results' }];

            _.each(self.intersection_targets(), function (target) {
                options.push({
                    value: target.slug,
                    label: target.name,
                });
            });

            return options;
        });

        this.has_filters = ko.computed(function () {
            return _.some(self.sections(), function (section) {
                return section.groups().length > 0;
            });
        });

        this.has_active_filters = ko.computed(function () {
            return _.some(self.sections(), function (section) {
                return _.some(section.groups(), function (group) {
                    return _.some(group.cards(), function (card) {
                        return self._card_has_filter_value(card);
                    });
                });
            });
        });

        this.active_sections = ko.computed(function () {
            return _.filter(self.sections(), function (section) {
                return _.some(section.groups(), function (group) {
                    return group.cards().length > 0;
                });
            });
        });

        this.used_card_ids = ko.computed(function () {
            let ids = [];
            _.each(self.sections(), function (section) {
                _.each(section.groups(), function (group) {
                    _.each(group.cards(), function (card) {
                        ids.push(card.nodegroup_id);
                    });
                });
            });
            return ids;
        });

        this.formatted_elapsed_time = ko.computed(function () {
            let elapsed = self.search_elapsed_time();

            if (elapsed === null) {
                return '';
            }

            if (elapsed < 1000) {
                return elapsed + 'ms';
            }

            return (elapsed / 1000).toFixed(1) + 's';
        });

        this.translate_mode.subscribe(function () {
            self.reset_pagination();
        });

        this.result_operation.subscribe(function () {
            self.reset_pagination();
        });

        $.ajax({
            context: this,
            type: 'GET',
            url: arches.urls.api_search_component_data + component_name,
        }).done(function (response) {
            this.cards = response.cards || [];

            if (response.intersection_targets) {
                this.intersection_targets(response.intersection_targets);
            }

            _.each(
                response.datatypes || [],
                function (datatype) {
                    this.datatype_lookup[datatype.datatype] = datatype;
                },
                this,
            );

            _.each(
                response.cardwidgets || [],
                function (widget) {
                    this.widget_lookup[widget.node_id] = widget;
                },
                this,
            );

            _.each(
                response.cards || [],
                function (card) {
                    card.nodes = _.filter(
                        response.nodes || [],
                        function (node) {
                            return node.nodegroup_id === card.nodegroup_id;
                        },
                    );

                    _.each(card.nodes || [], function (node) {
                        node.label =
                            (self.widget_lookup[node.nodeid] || {}).label ||
                            node.name;
                    });

                    this.card_lookup[card.nodegroup_id] = card;
                },
                this,
            );

            _.each(
                response.graphs || [],
                function (graph) {
                    let graph_cards = _.filter(this.cards, function (card) {
                        if (card.graph_id !== graph.graphid) {
                            return false;
                        }

                        let searchable_nodes = _.filter(
                            card.nodes || [],
                            function (node) {
                                let datatype =
                                    self.datatype_lookup[node.datatype];
                                return (
                                    datatype &&
                                    datatype.configname &&
                                    ko.components.isRegistered(
                                        datatype.configname,
                                    )
                                );
                            },
                        );

                        return searchable_nodes.length > 0;
                    });

                    if (graph_cards.length > 0) {
                        graph_cards = _.sortBy(graph_cards, function (card) {
                            return (card.name || '').toLowerCase();
                        });

                        graph.collapsed = ko.observable(true);
                        graph.cards = ko.observableArray(graph_cards);

                        graph.filtered_cards = ko.computed(function () {
                            let filter_text = (
                                self.facet_filter_text() || ''
                            ).toLowerCase();

                            if (filter_text) {
                                graph.collapsed(false);

                                return _.filter(graph_cards, function (card) {
                                    let card_name = (
                                        card.name || ''
                                    ).toLowerCase();
                                    return card_name.indexOf(filter_text) > -1;
                                });
                            }

                            return graph_cards;
                        });

                        this.searchable_graphs.push(graph);
                        this.graph_lookup[graph.graphid] = graph;

                        this.sections.push({
                            collapsed: ko.observable(false),
                            graph_id: graph.graphid,
                            graph_name: ko.unwrap(graph.name) || 'Unknown',
                            groups: ko.observableArray([]),
                        });
                    }
                },
                this,
            );

            this.restore_state();

            let filter_updated = ko.computed(function () {
                let data = {
                    result_operation: self.result_operation(),
                    sections: ko.toJS(self.sections()),
                    translate_mode: self.translate_mode(),
                };

                return JSON.stringify(data);
            });

            filter_updated.subscribe(function () {
                self.update_query();
            });

            this.searchFilterVms[component_name](this);
            options.loading(false);
        });

        this._setup_search_listener();
    },

    _card_has_filter_value: function (card) {
        let self = this;
        let has_value = false;

        _.each(card.filters, function (filter_obs, node_id) {
            let filter_value = ko.toJS(filter_obs());

            if (self._is_valid_filter_value(filter_value)) {
                has_value = true;
            }
        });

        return has_value;
    },

    _clear_drag_state: function () {
        this.drag_data(null);
        this.drag_over_add_group(null);
        this.drag_over_card(null);
        this.drag_over_group(null);
        this.drag_over_position(null);
    },

    _get_event: function (event) {
        return event.originalEvent || event;
    },

    _is_valid_filter_value: function (filter_value) {
        if (!filter_value) {
            return false;
        }

        if (typeof filter_value !== 'object') {
            return false;
        }

        let val = filter_value.val;

        if (val === undefined || val === null || val === '') {
            return false;
        }

        if (Array.isArray(val) && val.length === 0) {
            return false;
        }

        return true;
    },

    _move_section_to_end: function (section) {
        let dominated_idx = this.sections.indexOf(section);

        if (dominated_idx > -1) {
            this.sections.splice(dominated_idx, 1);
            this.sections.push(section);
        }
    },

    _setup_search_listener: function () {
        let self = this;

        $(document).ajaxSend(function (event, jqxhr, settings) {
            if (
                settings.url &&
                settings.url.indexOf('/search/resources') > -1
            ) {
                if (
                    self.has_active_filters() &&
                    self.translate_mode() !== 'none'
                ) {
                    self._start_search_timer();
                }
            }
        });

        $(document).ajaxComplete(function (event, jqxhr, settings) {
            if (
                settings.url &&
                settings.url.indexOf('/search/resources') > -1
            ) {
                self._stop_search_timer();
            }
        });

        $(document).ajaxError(function (event, jqxhr, settings) {
            if (
                settings.url &&
                settings.url.indexOf('/search/resources') > -1
            ) {
                self._stop_search_timer();
            }
        });
    },

    _start_search_timer: function () {
        let self = this;

        this.is_searching(true);
        this.search_start_time = Date.now();
        this.search_elapsed_time(0);

        if (this.search_timer_interval) {
            clearInterval(this.search_timer_interval);
        }

        this.search_timer_interval = setInterval(function () {
            if (self.search_start_time) {
                self.search_elapsed_time(Date.now() - self.search_start_time);
            }
        }, 100);
    },

    _stop_search_timer: function () {
        this.is_searching(false);

        if (this.search_timer_interval) {
            clearInterval(this.search_timer_interval);
            this.search_timer_interval = null;
        }

        if (this.search_start_time) {
            this.search_elapsed_time(Date.now() - this.search_start_time);
            this.search_start_time = null;
        }
    },

    add_card_to_group: function (section, group, card) {
        let self = this;

        let card_filters = {};

        _.each(card.nodes || [], function (node) {
            card_filters[node.nodeid] = ko.observable({});
        });

        let new_card = {
            card_id: card.cardid,
            card_name: card.name,
            collapsed: ko.observable(false),
            filters: card_filters,
            nodegroup_id: card.nodegroup_id,
            nodes: card.nodes,
        };

        group.cards.push(new_card);
    },

    add_group: function (section) {
        let self = this;
        let was_empty = section.groups().length === 0;

        let new_group = {
            cards: ko.observableArray([]),
            collapsed: ko.observable(false),
            id: self.next_group_id++,
            match: ko.observable('all'),
            operator_after: ko.observable('and'),
        };

        section.groups.push(new_group);

        if (was_empty) {
            self._move_section_to_end(section);
        }

        return new_group;
    },

    clear: function () {
        _.each(this.sections(), function (section) {
            section.groups.removeAll();
        });

        this.result_operation('intersect');
        this.translate_mode('none');
        this.search_elapsed_time(null);
        this.reset_pagination();
    },

    get_drop_indicator_position: function (card) {
        let drag_data = this.drag_data();

        if (!drag_data) {
            return null;
        }

        if (this.drag_over_card() !== card) {
            return null;
        }

        if (drag_data.card === card) {
            return null;
        }

        return this.drag_over_position();
    },

    get_section_for_graph: function (graph_id) {
        return _.find(this.sections(), function (section) {
            return section.graph_id === graph_id;
        });
    },

    get_section_for_group: function (group) {
        return _.find(this.sections(), function (section) {
            return section.groups.indexOf(group) > -1;
        });
    },

    handle_card_drag_over: function (card, group, section, event) {
        let native_event = this._get_event(event);
        native_event.preventDefault();

        let drag_data = this.drag_data();
        if (!drag_data) {
            return true;
        }

        if (drag_data.graph_id !== section.graph_id) {
            return true;
        }

        let target = native_event.currentTarget;
        let rect = target.getBoundingClientRect();
        let midpoint = rect.top + rect.height / 2;
        let position = native_event.clientY < midpoint ? 'before' : 'after';

        this.drag_over_card(card);
        this.drag_over_group(group);
        this.drag_over_position(position);

        return true;
    },

    handle_drag_end: function (card, event) {
        this._clear_drag_state();
        return true;
    },

    handle_add_group_drag_leave: function (section, event) {
        let native_event = this._get_event(event);
        let related_target = native_event.relatedTarget;
        let current_target = native_event.currentTarget;

        if (
            related_target &&
            current_target &&
            current_target.contains(related_target)
        ) {
            return true;
        }

        if (this.drag_over_add_group() === section) {
            this.drag_over_add_group(null);
        }

        return true;
    },

    handle_add_group_drag_over: function (section, event) {
        let native_event = this._get_event(event);
        native_event.preventDefault();

        let drag_data = this.drag_data();

        if (!drag_data) {
            return true;
        }

        if (drag_data.source !== 'sidebar') {
            return true;
        }

        if (drag_data.graph_id !== section.graph_id) {
            return true;
        }

        this.drag_over_add_group(section);
        return true;
    },

    handle_add_group_drop: function (section, event) {
        let native_event = this._get_event(event);
        native_event.preventDefault();

        let drag_data = this.drag_data();

        if (!drag_data) {
            this._clear_drag_state();
            return true;
        }

        if (drag_data.source !== 'sidebar') {
            this._clear_drag_state();
            return true;
        }

        if (drag_data.graph_id !== section.graph_id) {
            this._clear_drag_state();
            return true;
        }

        let new_group = this.add_group(section);
        this.add_card_to_group(section, new_group, drag_data.card_def);

        this._clear_drag_state();
        return true;
    },

    handle_drag_leave: function (group, event) {
        let native_event = this._get_event(event);
        let related_target = native_event.relatedTarget;
        let current_target = native_event.currentTarget;

        if (
            related_target &&
            current_target &&
            current_target.contains(related_target)
        ) {
            return true;
        }

        if (this.drag_over_group() === group) {
            this.drag_over_card(null);
            this.drag_over_group(null);
            this.drag_over_position(null);
        }

        return true;
    },

    handle_drag_over: function (group, section, event) {
        let native_event = this._get_event(event);
        native_event.preventDefault();

        let drag_data = this.drag_data();

        if (!drag_data) {
            return true;
        }

        if (drag_data.graph_id !== section.graph_id) {
            return true;
        }

        this.drag_over_group(group);
        return true;
    },

    handle_drag_start: function (card, group, section, event) {
        let native_event = this._get_event(event);

        this.drag_data({
            card: card,
            graph_id: section.graph_id,
            group: group,
            section: section,
            source: 'main',
        });

        if (native_event.dataTransfer) {
            native_event.dataTransfer.effectAllowed = 'move';
            native_event.dataTransfer.setData(
                'text/plain',
                card.card_id || 'card',
            );
        }

        return true;
    },

    handle_drop: function (target_group, target_section, event) {
        let native_event = this._get_event(event);
        native_event.preventDefault();

        let drag_data = this.drag_data();

        if (!drag_data) {
            this._clear_drag_state();
            return true;
        }

        if (drag_data.graph_id !== target_section.graph_id) {
            this._clear_drag_state();
            return true;
        }

        if (drag_data.source === 'sidebar') {
            let card_def = drag_data.card_def;
            let target_card = this.drag_over_card();
            let position = this.drag_over_position();

            if (target_card) {
                let cards = target_group.cards();
                let target_index = cards.indexOf(target_card);

                if (position === 'after') {
                    target_index += 1;
                }

                let card_filters = {};

                _.each(card_def.nodes || [], function (node) {
                    card_filters[node.nodeid] = ko.observable({});
                });

                let new_card = {
                    card_id: card_def.cardid,
                    card_name: card_def.name,
                    collapsed: ko.observable(false),
                    filters: card_filters,
                    nodegroup_id: card_def.nodegroup_id,
                    nodes: card_def.nodes,
                };

                target_group.cards.splice(target_index, 0, new_card);
            } else {
                this.add_card_to_group(target_section, target_group, card_def);
            }

            this._clear_drag_state();
            return true;
        }

        let source_group = drag_data.group;
        let dragged_card = drag_data.card;
        let target_card = this.drag_over_card();
        let position = this.drag_over_position();

        if (source_group === target_group && target_card) {
            let cards = source_group.cards();
            let source_index = cards.indexOf(dragged_card);
            let target_index = cards.indexOf(target_card);

            if (source_index === target_index) {
                this._clear_drag_state();
                return true;
            }

            source_group.cards.splice(source_index, 1);

            cards = source_group.cards();
            target_index = cards.indexOf(target_card);

            if (position === 'after') {
                target_index += 1;
            }

            source_group.cards.splice(target_index, 0, dragged_card);
        } else if (source_group !== target_group) {
            source_group.cards.remove(dragged_card);

            if (target_card) {
                let cards = target_group.cards();
                let target_index = cards.indexOf(target_card);

                if (position === 'after') {
                    target_index += 1;
                }

                target_group.cards.splice(target_index, 0, dragged_card);
            } else {
                target_group.cards.push(dragged_card);
            }

            if (source_group.cards().length === 0) {
                drag_data.section.groups.remove(source_group);
            }
        }

        this._clear_drag_state();
        return true;
    },

    handle_sidebar_drag_end: function (card, event) {
        this._clear_drag_state();
        return true;
    },

    handle_sidebar_drag_start: function (card_def, graph, event) {
        let native_event = this._get_event(event);

        this.drag_data({
            card: null,
            card_def: card_def,
            graph_id: graph.graphid,
            group: null,
            section: null,
            source: 'sidebar',
        });

        if (native_event.dataTransfer) {
            native_event.dataTransfer.effectAllowed = 'copy';
            native_event.dataTransfer.setData(
                'text/plain',
                card_def.cardid || 'card',
            );
        }

        return true;
    },

    is_card_used: function (card) {
        return this.used_card_ids().indexOf(card.nodegroup_id) > -1;
    },

    is_drop_target: function (group) {
        let drag_data = this.drag_data();

        if (!drag_data) {
            return false;
        }

        let target_section = this.get_section_for_group(group);

        if (!target_section || drag_data.graph_id !== target_section.graph_id) {
            return false;
        }

        if (drag_data.source === 'sidebar') {
            return this.drag_over_group() === group;
        }

        return this.drag_over_group() === group && drag_data.group !== group;
    },

    remove_card_from_group: function (group, card) {
        let self = this;
        group.cards.remove(card);

        if (group.cards().length === 0) {
            let section = _.find(self.sections(), function (s) {
                return s.groups.indexOf(group) > -1;
            });

            if (section) {
                section.groups.remove(group);
            }
        }

        self.reset_pagination();
    },

    remove_group: function (section, group) {
        section.groups.remove(group);
        this.reset_pagination();
    },

    reset_pagination: function () {
        let query_obj = this.query();
        query_obj['paging-filter'] = '1';
        this.query(query_obj);
    },

    restore_state: function () {
        let self = this;
        let query = this.query();

        if (component_name in query) {
            let saved_data;

            try {
                saved_data = JSON.parse(query[component_name]);
            } catch (e) {
                return;
            }

            if (saved_data.result_operation) {
                this.result_operation(saved_data.result_operation);
            }

            if (saved_data.translate_mode) {
                this.translate_mode(saved_data.translate_mode);
            }

            _.each(saved_data.sections || [], function (saved_section) {
                let section = self.get_section_for_graph(
                    saved_section.graph_id,
                );
                if (!section) return;

                _.each(saved_section.groups || [], function (saved_group) {
                    let new_group = {
                        cards: ko.observableArray([]),
                        collapsed: ko.observable(false),
                        id: self.next_group_id++,
                        match: ko.observable(saved_group.match || 'all'),
                        operator_after: ko.observable(
                            saved_group.operator_after || 'and',
                        ),
                    };

                    _.each(saved_group.cards || [], function (saved_card) {
                        let card_def =
                            self.card_lookup[saved_card.nodegroup_id];
                        if (!card_def) return;

                        let card_filters = {};

                        _.each(card_def.nodes || [], function (node) {
                            let saved_value = saved_card.filters
                                ? saved_card.filters[node.nodeid]
                                : {};
                            card_filters[node.nodeid] = ko.observable(
                                saved_value || {},
                            );
                        });

                        new_group.cards.push({
                            card_id: card_def.cardid,
                            card_name: card_def.name,
                            collapsed: ko.observable(false),
                            filters: card_filters,
                            nodegroup_id: card_def.nodegroup_id,
                            nodes: card_def.nodes,
                        });
                    });

                    section.groups.push(new_group);
                });
            });

            if (self.has_active_filters()) {
                this.getFilterByType('term-filter-type').addTag(
                    this.tag_id,
                    this.name,
                    ko.observable(false),
                );
            }
        }
    },

    update_query: function () {
        let self = this;
        let query_obj = this.query();

        if (this.has_active_filters()) {
            let serialized = {
                result_operation: this.result_operation(),
                sections: [],
                translate_mode: this.translate_mode(),
            };

            _.each(this.sections(), function (section) {
                let section_has_active_filters = _.some(
                    section.groups(),
                    function (group) {
                        return _.some(group.cards(), function (card) {
                            return self._card_has_filter_value(card);
                        });
                    },
                );

                if (section_has_active_filters) {
                    let section_data = {
                        graph_id: section.graph_id,
                        groups: [],
                    };

                    _.each(section.groups(), function (group) {
                        let group_has_active_filters = _.some(
                            group.cards(),
                            function (card) {
                                return self._card_has_filter_value(card);
                            },
                        );

                        if (group_has_active_filters) {
                            let group_data = {
                                cards: [],
                                id: group.id,
                                match: group.match(),
                                operator_after: group.operator_after(),
                            };

                            _.each(group.cards(), function (card) {
                                if (!self._card_has_filter_value(card)) {
                                    return;
                                }

                                let card_data = {
                                    filters: {},
                                    nodegroup_id: card.nodegroup_id,
                                };

                                _.each(
                                    card.filters,
                                    function (filter_obs, node_id) {
                                        let filter_value =
                                            ko.toJS(filter_obs());

                                        if (
                                            self._is_valid_filter_value(
                                                filter_value,
                                            )
                                        ) {
                                            card_data.filters[node_id] =
                                                filter_value;
                                        }
                                    },
                                );

                                group_data.cards.push(card_data);
                            });

                            section_data.groups.push(group_data);
                        }
                    });

                    serialized.sections.push(section_data);
                }
            });

            query_obj[component_name] = JSON.stringify(serialized);

            if (
                this.getFilterByType('term-filter-type').hasTag(this.tag_id) ===
                false
            ) {
                this.getFilterByType('term-filter-type').addTag(
                    this.tag_id,
                    this.name,
                    ko.observable(false),
                );
            }

            this.reset_pagination();
        } else {
            delete query_obj[component_name];
            this.getFilterByType('term-filter-type').removeTag(this.tag_id);
        }

        this.query(query_obj);
    },
});

ko.components.register(component_name, {
    template: crossModelAdvancedSearchTemplate,
    viewModel: view_model,
});
