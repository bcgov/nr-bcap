import $ from "jquery";
import ko from "knockout";
import arches from "arches";
import WidgetViewModel from "viewmodels/widget";
import AlertViewModel from "viewmodels/alert";
import bordenNumberWidgetTemplate from "templates/views/components/widgets/borden-number-widget.htm";

/**
 * registers a text-widget component for use in forms
 * @function external:"ko.components".text-widget
 * @param {object} params
 * @param {string} params.value - the value being managed
 * @param {function} params.config - observable containing config object
 * @param {string} params.config().label - label to use alongside the text input
 * @param {string} params.config().placeholder - default text to show in the text input
 * @param {string} params.config().uneditable - disables widget
 */

const BordenNumberWidget = function (params) {
    params.configKeys = [
        "placeholder",
        "width",
        "maxLength",
        "defaultValue",
        "uneditable",
    ];

    WidgetViewModel.apply(this, [params]);
    const self = this;
    self.urls = arches.urls;

    self.disable = ko.computed(() => {
        return (
            ko.unwrap(self.disabled) ||
            ko.unwrap(self.uneditable) ||
            !!ko.unwrap(self.value)
        );
    }, self);

    self.getBordenNumber = function () {
        let url = `${self.urls.root}borden_number/${self.tile.resourceinstance_id}`;
        console.log(`Get borden number from ${url}...`);
        self.form.loading(true);
        $.ajax({
            // type: "PUT",
            url: url,
        }).done(function (data) {
            console.log(`Data: ${JSON.stringify(data)}`);
            console.log(data);
            if (data.status === "success") {
                self.value(data.borden_number);
            } else {
                self.form.alert(
                    new AlertViewModel(
                        "ep-alert-red",
                        "Error",
                        data.message,
                        null,
                        function () {},
                    ),
                );
                // self.form.alert(data.message);
            }
            self.form.loading(false);
        });
    };
};

export default ko.components.register("borden-number-widget", {
    viewModel: BordenNumberWidget,
    template: bordenNumberWidgetTemplate,
});
