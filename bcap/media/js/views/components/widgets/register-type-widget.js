import $ from 'jquery';
import ko from 'knockout';
import arches from 'arches';
import WidgetViewModel from 'viewmodels/widget';
import AlertViewModel from 'viewmodels/alert';
import registerTypeWidgetTemplate from 'templates/views/components/widgets/register-type-widget.htm';

const RegisterTypeWidget = function (params) {
    params.configKeys = [];

    WidgetViewModel.apply(this, [params]);
    let self = this;
    self.urls = arches.urls;

    self.display_items = ko.computed(function () {
        let raw = ko.unwrap(self.value);
        let val = ko.toJS(raw);
        if (!val) {
            return [];
        }
        if (typeof val === 'string') {
            return [val];
        }
        if (!Array.isArray(val) || val.length === 0) {
            return [];
        }
        return val.map(function (item) {
            if (typeof item === 'string') {
                return item;
            }
            if (item.labels && item.labels.length > 0) {
                let pref = item.labels.find(function (l) {
                    return l.valuetype_id === 'prefLabel';
                });
                return pref ? pref.value : item.labels[0].value;
            }
            return item.uri || 'Unknown';
        });
    }, self);

    self.display_values = ko.computed(function () {
        let items = self.display_items();
        if (items.length === 0) {
            return '';
        }
        return items.join(', ');
    }, self);

    self.disable = ko.computed(function () {
        return ko.unwrap(self.disabled) || ko.unwrap(self.form?.loading);
    }, self);

    self._extract_uris = function (reference_value) {
        if (!reference_value || !Array.isArray(reference_value)) {
            return [];
        }
        return reference_value
            .map(function (entry) {
                return typeof entry === 'object' ? entry.uri : entry;
            })
            .sort();
    };

    self._values_equal = function (current, incoming) {
        let current_uris = self._extract_uris(ko.toJS(current));
        let incoming_uris = self._extract_uris(ko.toJS(incoming));
        if (current_uris.length !== incoming_uris.length) {
            return false;
        }
        for (let i = 0; i < current_uris.length; i++) {
            if (current_uris[i] !== incoming_uris[i]) {
                return false;
            }
        }
        return true;
    };

    self.calculate_register_type = function () {
        let url = `${self.urls.root}register_type/${self.tile.resourceinstance_id}`;
        self.form.loading(true);
        $.ajax({
            url: url,
        })
            .done(function (data) {
                if (data.status === 'success') {
                    if (
                        !self._values_equal(self.value(), data.reference_value)
                    ) {
                        self.value(data.reference_value);
                    }
                    if (data.missing_labels && data.missing_labels.length > 0) {
                        self.form.alert(
                            new AlertViewModel(
                                'ep-alert-blue',
                                'Warning',
                                'The following register types are not yet in the controlled list: ' +
                                    data.missing_labels.join(', '),
                                null,
                                function () {},
                            ),
                        );
                    }
                } else {
                    self.form.alert(
                        new AlertViewModel(
                            'ep-alert-red',
                            'Error',
                            data.message,
                            null,
                            function () {},
                        ),
                    );
                }
                self.form.loading(false);
            })
            .fail(function () {
                self.form.alert(
                    new AlertViewModel(
                        'ep-alert-red',
                        'Error',
                        'Failed to calculate register type. Please try again.',
                        null,
                        function () {},
                    ),
                );
                self.form.loading(false);
            });
    };
};

export default ko.components.register('register-type-widget', {
    viewModel: RegisterTypeWidget,
    template: registerTypeWidgetTemplate,
});
