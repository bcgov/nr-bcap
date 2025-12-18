import BaseFilter from "views/components/search/base-filter";
import ko from "knockout";
import koMapping from "knockout-mapping";
import ariaUtils from "utils/aria";
import pagingFilterTemplate from "templates/views/components/search/paging-filter.htm";


const componentName = "paging-filter";
const viewModel = BaseFilter.extend({
    initialize: function(options) {
        options.name = "Paging Filter";
        BaseFilter.prototype.initialize.call(this, options);
        this.page = ko.observable();
        this.preventLoop = false;
        this.userRequestedNewPage = false;
        this.pageInitialized = false;
        this.paginator = koMapping.fromJS({
            current_page: 1,
            end_index: 1,
            has_next: false,
            has_other_pages: true,
            has_previous: false,
            next_page_number: 2,
            pages: [],
            previous_page_number: null,
            start_index: 1
        });
        this.shiftFocus = ariaUtils.shiftFocus;

        this.query.subscribe(function() {
            if (this.preventLoop === false && this.userRequestedNewPage === false && this.pageInitialized === true) {
                this.preventLoop = true;
                this.page(1);
            } else {
                this.preventLoop = false;
                this.userRequestedNewPage = false;
            }
        }, this, "beforeChange");

        this.page.subscribe(function(timestamp) {
            this.updateQuery();
        }, this);

        this.searchResults.timestamp.subscribe(function(timestamp) {
            this.updateResults();
        }, this);

        this.searchFilterVms[componentName](this);
        this.restoreState();
        this.pageInitialized = true;
    },

    updateQuery: function() {
        var queryObj = this.query();

        var cleanQuery = {
            "paging-filter": this.page()
        };
        if (queryObj["ids"]) {
            cleanQuery["ids"] = queryObj["ids"];
        }
        if (queryObj["term-filter"]) {
            cleanQuery["term-filter"] = queryObj["term-filter"];
        }
        if (queryObj["resource-type-filter"]) {
            cleanQuery["resource-type-filter"] = queryObj["resource-type-filter"];
        }
        if (queryObj["map-filter"]) {
            cleanQuery["map-filter"] = queryObj["map-filter"];
        }
        if (queryObj["time-filter"]) {
            cleanQuery["time-filter"] = queryObj["time-filter"];
        }
        if (queryObj["provisional-filter"]) {
            cleanQuery["provisional-filter"] = queryObj["provisional-filter"];
        }
        if (queryObj["lifecycle-state-filter"]) {
            cleanQuery["lifecycle-state-filter"] = queryObj["lifecycle-state-filter"];
        }
        if (queryObj["sort-results"]) {
            cleanQuery["sort-results"] = queryObj["sort-results"];
        }
        if (queryObj["language"]) {
            cleanQuery["language"] = queryObj["language"];
        }

        this.query(cleanQuery);
    },

    newPage: function(page) {
        if (page) {
            this.userRequestedNewPage = true;
            this.page(page);
            this.shiftFocus("#search-results-list-type");
        }
    },

    restoreState: function() {
        var currentPage = this.query()[componentName];
        if (!currentPage) {
            currentPage = 1;
        }
        this.page(currentPage);
        this.updateResults();
    },

    updateResults: function() {
        if (!!this.searchResults[componentName] && !!this.searchResults[componentName]["paginator"]) {
            koMapping.fromJS(this.searchResults[componentName]["paginator"], this.paginator);
        }
    }
});

export default ko.components.register(componentName, {
    viewModel: viewModel,
    template: pagingFilterTemplate,
});
