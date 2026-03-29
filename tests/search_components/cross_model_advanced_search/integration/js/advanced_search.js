window.__adv = {
    _facet() {
        return document.getElementById('facet-filter-0');
    },

    _selects() {
        let facet = this._facet();
        return facet ? facet.querySelectorAll('select.resources') : [];
    },

    _input_near(select_el) {
        let widget =
            select_el.closest('.widget-wrapper') ||
            select_el.closest('div').parentElement;
        let input = widget
            ? widget.querySelector('input[type="text"], input[type="number"]')
            : null;

        if (!input) {
            let parent =
                select_el.closest('.row') ||
                select_el.parentElement.parentElement;
            input = parent
                ? parent.querySelector(
                      'input[type="text"], input[type="number"]',
                  )
                : null;
        }

        return input;
    },

    _adv_vm() {
        let container = document.querySelector(
            '.faceted-search-card-container',
        );

        if (!container || !window.ko) {
            return null;
        }

        let ctx = ko.contextFor(container);

        return ctx ? ctx.$parent : null;
    },

    _find_facet_target(el) {
        if (!window.ko) {
            return null;
        }

        let ctx = ko.contextFor(el);

        if (!ctx) {
            return null;
        }

        let chain = [ctx.$data].concat(ctx.$parents);
        let nodeid = null;

        for (let p of chain) {
            if (p && p.nodeid) {
                nodeid = typeof p.nodeid === 'function' ? p.nodeid() : p.nodeid;
                break;
            }
        }

        if (!nodeid) {
            return null;
        }

        for (let p of chain) {
            if (
                p &&
                p.value &&
                typeof p.value === 'object' &&
                p.value[nodeid]
            ) {
                return { facet_value: p.value, nodeid: nodeid };
            }
        }

        return null;
    },

    _ko_set(select_el, qualifier, text) {
        let input = this._input_near(select_el);
        let candidates = [select_el];

        if (input) {
            candidates.push(input);
        }

        for (let el of candidates) {
            let target = this._find_facet_target(el);

            if (!target) {
                continue;
            }

            let current = ko.toJS(target.facet_value[target.nodeid]()) || {};

            if ('op' in current) {
                current.op = qualifier;
                current.val = text || '';
            } else {
                current.val = qualifier;
            }

            target.facet_value[target.nodeid](current);

            if (
                window.ko &&
                ko.tasks &&
                typeof ko.tasks.runEarly === 'function'
            ) {
                ko.tasks.runEarly();
            }

            let vm = this._adv_vm();

            if (vm && typeof vm.updateQuery === 'function') {
                vm.updateQuery();
            }

            return true;
        }

        return false;
    },

    _set_native_value(el, value) {
        let setter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype,
            'value',
        ).set;
        setter.call(el, value);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));

        if (window.jQuery) {
            jQuery(el).trigger('change');
        }
    },

    _trigger_change(el) {
        el.dispatchEvent(new Event('change', { bubbles: true }));

        if (window.jQuery) {
            jQuery(el).trigger('change');
        }
    },

    get_testable_fields(qualifiers) {
        let selects = this._selects();
        let results = [];

        for (let i = 0; i < selects.length; i++) {
            let sel = selects[i];
            let available = [];

            for (let o of sel.options) {
                if (qualifiers.includes(o.value)) {
                    available.push(o.value);
                }
            }

            if (available.length === 0) {
                continue;
            }

            let label = '';
            let prev = sel.closest('div')?.previousElementSibling;

            if (prev && prev.tagName === 'DIV' && prev.childNodes.length <= 3) {
                label = prev.textContent.trim();
            }

            if (!label) {
                let acc = sel.getAttribute('aria-label') || '';

                if (acc) {
                    label = acc.split(',')[0].trim();
                }
            }

            results.push({ index: i, label: label, qualifiers: available });
        }

        return results;
    },

    set_qualifier(index, qualifier, text) {
        let sel = this._selects()[index];

        if (!sel) {
            return;
        }

        if (this._ko_set(sel, qualifier, text)) {
            return;
        }

        sel.value = qualifier;
        this._trigger_change(sel);

        if (text) {
            let input = this._input_near(sel);

            if (input) {
                this._set_native_value(input, text);
            }
        }
    },

    reset_qualifier(index) {
        let sel = this._selects()[index];

        if (!sel) {
            return;
        }

        let default_op = sel.options.length > 0 ? sel.options[0].value : '';

        if (this._ko_set(sel, default_op, '')) {
            return;
        }

        sel.value = default_op;
        this._trigger_change(sel);

        let input = this._input_near(sel);

        if (input) {
            this._set_native_value(input, '');
        }
    },
};
