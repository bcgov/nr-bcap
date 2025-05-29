import ko from "knockout";
import $ from "jquery";
import _ from "underscore";
import arches from "arches";
import WidgetViewModel from "viewmodels/widget";
import defaultCivicAddressWidgetTemplate from "templates/views/components/widgets/significant-event-widget.htm";
export default ko.components.register("significant-event-widget", {
    viewModel: function (params) {
        params.configKeys = ["x_placeholder", "y_placeholder"];
        WidgetViewModel.apply(this, [params]);
        var self = this;
        this.card = ko.observable(params.card);
        this.tile = ko.observable(params.tile);

        this.eventTypes = params.event_types || ko.observableArray();
        this.showEvent = ko.observable(false);

        this.eventLabel = ko.observable("Event");

        this.getWidgetWithLabel = function (card, widgetName) {
            let namedWidget = _.find(card.widgets(), function (widget) {
                return widget.node.attributes.source["alias"] === widgetName;
            });
            return namedWidget;
        };

        ko.computed(function () {
            const widget = self.getWidgetWithLabel(self.card(), "chronology");
            const valueid = self.value[widget.node.nodeid]();
            if (valueid) {
                $.ajax(arches.urls.get_pref_label + "?valueid=" + valueid, {
                    dataType: "json",
                }).done(function (data) {
                    self.showEvent(self.eventTypes.includes(data.value));
                    self.eventLabel(`${data.value} Event`);
                });
            }
        });

        this.eventNotes = ko.computed(function () {
            return self.getWidgetWithLabel(self.card(), "chronology_notes");
        });

        this.startYear = ko.computed(function () {
            return self.getWidgetWithLabel(self.card(), "start_year");
        });

        this.endYear = ko.computed(function () {
            return self.getWidgetWithLabel(self.card(), "end_year");
        });

        this.startYearQualifier = ko.computed(function () {
            return self.getWidgetWithLabel(self.card(), "dates_approximate");
        });
    },
    template: defaultCivicAddressWidgetTemplate,
});
