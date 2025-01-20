define([
    'underscore',
        'knockout',
        'viewmodels/bcap-site',
        'templates/views/report-templates/bcap_default.htm',
], function (_, ko, ReportViewModel, defaultTemplate) {
    const viewModel = function(params) {
        params.configKeys = [];
        ReportViewModel.apply(this, [params]);
    };

    return ko.components.register('default-report', {
        viewModel: viewModel,
        template: defaultTemplate
    });
});