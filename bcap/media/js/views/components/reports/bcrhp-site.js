define(['underscore',
        'knockout',
        'knockout-mapping',
        'viewmodels/map-report',
        'reports/map-header',
        'templates/views/report-templates/bcap_default.htm'],
    function(_, ko, koMapping, MapReportViewModel, MapHeader, defaultBchpSiteTemplate) {
    return ko.components.register('bcap-site-report', {
        viewModel: MapReportViewModel,
        template: defaultBchpSiteTemplate
    });
});
