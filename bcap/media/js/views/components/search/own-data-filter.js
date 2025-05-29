import ko from "knockout";
import BaseFilter from "views/components/search/base-filter";
import defaultFilterView from "templates/views/components/search/own-data-filter.htm";

export default ko.components.register("own-data-filter", {
    viewModel: BaseFilter.extend({
        initialize: function (options) {
            options.name = "Own Data Filter";
            BaseFilter.prototype.initialize.call(this, options);
            this.restoreState();
        },

        restoreState: function () {
            var queryObj = this.query();
            queryObj["own-data-filter"] = "enabled";
            this.query(queryObj);
        },
    }),
    template: defaultFilterView,
});
