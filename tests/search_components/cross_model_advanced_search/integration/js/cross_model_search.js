window.__cm = {
    _container() {
        return document.querySelector('.cross-model-container');
    },

    _vm() {
        let container = this._container();
        return container ? ko.dataFor(container) : null;
    },

    _active_card() {
        let vm = this._vm();
        if (!vm) return null;

        let section = vm.sections().find((s) => s.groups().length > 0);
        if (!section) return null;

        let group = section.groups()[0];
        if (!group || group.cards().length === 0) return null;

        return group.cards()[0];
    },

    _filter_elements() {
        return document.querySelectorAll(
            '#cross-model-advanced-search-type-tabpanel .cross-model-filter',
        );
    },

    _find_default_op(node_id) {
        let card = this._active_card();
        if (!card) return '~';

        let node = card.nodes.find((n) => n.nodeid === node_id);
        if (!node) return '~';

        for (let f of this._filter_elements()) {
            let lbl = f.querySelector('.cross-model-filter-label');

            if (lbl && lbl.textContent.trim() === node.label) {
                let sel = f.querySelector('select');

                if (sel && sel.options.length > 0) {
                    return sel.options[0].value;
                }

                break;
            }
        }

        return '~';
    },

    click_card(name) {
        let cards = document.querySelectorAll(
            '.cross-model-card-option:not(.used)',
        );

        for (let c of cards) {
            let span = c.querySelector('span[data-bind="text: name"]');

            if (span && span.textContent.trim() === name) {
                c.click();
                return true;
            }
        }

        return false;
    },

    click_graph(name) {
        let headers = document.querySelectorAll('.cross-model-graph-name');

        for (let h of headers) {
            if (h.textContent.trim() === name) {
                h.closest('.cross-model-graph-header').click();
                return true;
            }
        }

        return false;
    },

    deactivate_filter(node_id) {
        let card = this._active_card();
        if (!card) return;

        let prev = ko.toJS(card.filters[node_id]()) || {};

        if ('op' in prev) {
            prev.op = this._find_default_op(node_id);
        }

        prev.val = '';
        card.filters[node_id](prev);
    },

    dismiss_overlay() {
        let el = this._container();

        if (el && window.ko) {
            let vm = ko.dataFor(el);

            if (vm && ko.isObservable(vm.loading)) {
                vm.loading(false);
            }
        }
    },

    get_testable_fields(qualifiers) {
        let card = this._active_card();
        if (!card) return [];

        let results = [];

        for (let f of this._filter_elements()) {
            let label_el = f.querySelector('.cross-model-filter-label');
            let sel = f.querySelector('select');
            if (!label_el || !sel) continue;

            let available = [];

            for (let o of sel.options) {
                if (qualifiers.includes(o.value)) {
                    available.push(o.value);
                }
            }

            if (available.length === 0) continue;

            let label = label_el.textContent.trim();
            let node = card.nodes.find((n) => n.label === label);

            if (node && card.filters[node.nodeid]) {
                results.push({
                    label: label,
                    node_id: node.nodeid,
                    qualifiers: available,
                });
            }
        }

        return results;
    },

    retry_search() {
        let vm = this._vm();
        if (!vm) return;

        if (typeof vm.update_query === 'function') {
            vm.update_query();
        }
    },

    set_filter(node_id, qualifier, text, is_val_qualifier) {
        let card = this._active_card();
        if (!card) return;

        let current = ko.toJS(card.filters[node_id]()) || {};

        if ('op' in current) {
            if (is_val_qualifier) {
                current.val = qualifier;
            } else {
                current.op = qualifier;
                current.val = text || '';
            }
        } else {
            current.val = qualifier;
        }

        card.filters[node_id](current);
    },

    set_translate_target(slug) {
        let sel = document.querySelector('.cross-model-option-select');
        if (!sel) return;

        sel.value = slug;
        sel.dispatchEvent(new Event('change', { bubbles: true }));

        if (window.jQuery) {
            jQuery(sel).trigger('change');
        }
    },
};
