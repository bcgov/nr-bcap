define(['underscore',
    'knockout',
    'knockout-mapping',
    'viewmodels/bcap-site',
    'reports/map-header',
    'templates/views/report-templates/map.htm',
    'templates/views/report-templates/details/archaeological_site.htm'
], function(_, ko, koMapping, MapReportViewModel, MapHeader, defaultSiteTemplate) {
    var siteViewModel = MapReportViewModel;
    /*
    siteViewModel.extend({
            var self = this;
            self.hi = ko.observable("hi");
            ko.utils.extend(self, new (params));
        }
    }
     */
    return ko.components.register('bcap-site-report', {
        viewModel: siteViewModel,
        template: defaultSiteTemplate
    });
});
