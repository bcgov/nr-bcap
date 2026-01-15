import $ from "jquery";
import _ from "underscore";
import arches from "arches";
import BaseFilter from "views/components/search/base-filter";
import ko from "knockout";
import koMapping from "knockout-mapping";
import crossModelAdvancedSearchTemplate from "templates/views/components/search/cross-model-advanced-search.htm";

console.log("cross-model-advanced-search.js: FILE LOADED");

let component_name = "cross-model-advanced-search";

console.log("cross-model-advanced-search.js: component_name =", component_name);

let view_model = BaseFilter.extend({
    initialize: function(options) {
        console.log("cross-model-advanced-search.js: initialize() CALLED");
        console.log("cross-model-advanced-search.js: options =", options);

        let self = this;

        options.name = "Cross-Model Advanced Search Filter";
        BaseFilter.prototype.initialize.call(this, options);

        this.cards = [];
        this.card_name_dict = {};
        this.datatype_lookup = {};
        this.facet_filter_text = ko.observable("");
        this.filter = {
            facets: ko.observableArray()
        };
        this.graph_lookup = {};
        this.searchable_graphs = ko.observableArray();
        this.tag_id = "Cross-Model Advanced Search";
        this.translate_to_parent = ko.observable(false);
        this.urls = arches.urls;
        this.widget_lookup = {};

        this.remove_facet = function(facet) {
            self.filter.facets.remove(facet);
        };

        console.log("cross-model-advanced-search.js: about to make AJAX call to", arches.urls.api_search_component_data + component_name);

        $.ajax({
            context: this,
            type: "GET",
            url: arches.urls.api_search_component_data + component_name
        }).done(function(response) {
            console.log("cross-model-advanced-search.js: AJAX done, response =", response);

            this.cards = response.cards || [];

            _.each(response.datatypes || [], function(datatype) {
                this.datatype_lookup[datatype.datatype] = datatype;
            }, this);

            _.each(response.cardwidgets || [], function(widget) {
                this.widget_lookup[widget.node_id] = widget;
            }, this);

            _.each(response.cards || [], function(card) {
                self.card_name_dict[card.nodegroup_id] = card.name;

                card.nodes = _.filter(response.nodes || [], function(node) {
                    return node.nodegroup_id === card.nodegroup_id;
                });

                card.add_facet = function() {
                    _.each(card.nodes, function(node) {
                        if (
                            self.card_name_dict[node.nodegroup_id] &&
                            node.nodeid === node.nodegroup_id
                        ) {
                            node.label = self.card_name_dict[node.nodegroup_id];
                        } else if (
                            node.nodeid !== node.nodegroup_id &&
                            self.widget_lookup[node.nodeid]
                        ) {
                            let widget = self.widget_lookup[node.nodeid];
                            node.label = widget.label;
                        } else {
                            node.label = node.name;
                        }
                    });

                    self.new_facet(card);
                };
            }, this);

            let graphs = (response.graphs || []).sort(function(a, b) {
                let name_a = (ko.unwrap(a.name) || "").toLowerCase();
                let name_b = (ko.unwrap(b.name) || "").toLowerCase();
                return name_a > name_b ? 1 : -1;
            });

            _.each(graphs, function(graph) {
                if (
                    graph.isresource &&
                    graph.is_active &&
                    graph.source_identifier_id === null
                ) {
                    let graph_cards = _.filter(response.cards || [], function(card) {
                        return card.graph_id === graph.graphid && card.nodes && card.nodes.length > 0;
                    });

                    graph_cards.sort(function(a, b) {
                        return (a.name || "").toLowerCase() > (b.name || "").toLowerCase() ? 1 : -1;
                    });

                    if (graph_cards.length > 0) {
                        _.each(graph_cards, function(card) {
                            card.get_graph = function() {
                                return graph;
                            };
                        });

                        graph.collapsed = ko.observable(true);
                        graph.cards = ko.computed(function() {
                            let filter_text = (self.facet_filter_text() || "").toLowerCase();
                            if (filter_text) {
                                graph.collapsed(false);
                                return _.filter(graph_cards, function(card) {
                                    let card_name = (card.name || "").toLowerCase();
                                    return card_name.indexOf(filter_text) > -1;
                                });
                            }
                            return graph_cards;
                        });

                        this.searchable_graphs.push(graph);
                        this.graph_lookup[graph.graphid] = graph;
                    }
                }
            }, this);

            console.log("cross-model-advanced-search.js: searchable_graphs =", this.searchable_graphs());

            this.restore_state();

            let filter_updated = ko.computed(function() {
                return JSON.stringify(ko.toJS(this.filter.facets())) + this.translate_to_parent();
            }, this);

            filter_updated.subscribe(function() {
                this.update_query();
            }, this);

            console.log("cross-model-advanced-search.js: about to call searchFilterVms");
            this.searchFilterVms[component_name](this);
            console.log("cross-model-advanced-search.js: searchFilterVms called");

            options.loading(false);
            console.log("cross-model-advanced-search.js: initialize COMPLETE");
        }).fail(function(jqXHR, textStatus, errorThrown) {
            console.error("cross-model-advanced-search.js: AJAX FAILED");
            console.error("cross-model-advanced-search.js: textStatus =", textStatus);
            console.error("cross-model-advanced-search.js: errorThrown =", errorThrown);
            console.error("cross-model-advanced-search.js: jqXHR =", jqXHR);
        });
    },

    clear: function() {
        console.log("cross-model-advanced-search.js: clear() called");
        this.filter.facets.removeAll();
        this.translate_to_parent(false);
    },

    new_facet: function(card) {
        console.log("cross-model-advanced-search.js: new_facet() called, card =", card);
        let self = this;
        let graph = card.get_graph();

        let facet = {
            card: card,
            graph_id: graph.graphid,
            graph_name: ko.unwrap(graph.name) || "Unknown",
            value: {
                graph_id: graph.graphid,
                op: ko.observable("and")
            }
        };

        _.each(card.nodes || [], function(node) {
            facet.value[node.nodeid] = ko.observable({});
        });

        this.filter.facets.push(facet);
    },

    restore_state: function() {
        console.log("cross-model-advanced-search.js: restore_state() called");
        let self = this;
        let query = this.query();

        if (component_name in query) {
            let facets = [];
            try {
                facets = JSON.parse(query[component_name]);
            } catch (e) {
                console.error("cross-model-advanced-search.js: restore_state parse error", e);
                return;
            }

            if (facets.length > 0) {
                this.getFilterByType("term-filter-type").addTag(
                    this.tag_id,
                    this.name,
                    ko.observable(false)
                );

                let has_translate = _.some(facets, function(f) {
                    return f.translate_to_parent === true;
                });
                this.translate_to_parent(has_translate);
            }

            _.each(facets, function(facet) {
                let node_ids = _.filter(Object.keys(facet), function(key) {
                    return key !== "op" && key !== "graph_id" && key !== "translate_to_parent";
                });

                let card = _.find(this.cards, function(card) {
                    let card_node_ids = _.map(card.nodes || [], function(node) {
                        return node.nodeid;
                    });
                    return _.contains(card_node_ids, node_ids[0]);
                }, this);

                if (card) {
                    let graph = card.get_graph();

                    (card.nodes || []).forEach(function(node) {
                        facet[node.nodeid] = ko.observable(facet[node.nodeid] || {});
                        node.label = (self.widget_lookup[node.nodeid] || {}).label || node.name;
                    });

                    facet.op = ko.observable(facet.op || "and");

                    this.filter.facets.push({
                        card: card,
                        graph_id: graph.graphid,
                        graph_name: ko.unwrap(graph.name) || "Unknown",
                        value: facet
                    });
                }
            }, this);
        }
    },

    update_query: function() {
        console.log("cross-model-advanced-search.js: update_query() called");
        let self = this;
        let query_obj = this.query();
        let filters_applied = this.filter.facets().length > 0;

        if (filters_applied) {
            let advanced = [];

            _.each(this.filter.facets(), function(facet) {
                let value = koMapping.toJS(facet.value);
                value.graph_id = facet.graph_id;
                value.translate_to_parent = self.translate_to_parent();
                advanced.push(value);
            });

            query_obj[component_name] = JSON.stringify(advanced);

            if (this.getFilterByType("term-filter-type").hasTag(this.tag_id) === false) {
                this.getFilterByType("term-filter-type").addTag(
                    this.tag_id,
                    this.name,
                    ko.observable(false)
                );
            }
        } else {
            delete query_obj[component_name];
            this.getFilterByType("term-filter-type").removeTag(this.tag_id);
        }

        this.query(query_obj);
    }
});

console.log("cross-model-advanced-search.js: about to register component");

ko.components.register(component_name, {
    template: crossModelAdvancedSearchTemplate,
    viewModel: view_model
});

console.log("cross-model-advanced-search.js: component registered");
