import ko from "knockout";
import ReportViewModel from "viewmodels/bcap-site";
import defaultTemplate from "templates/views/report-templates/bcap_default.htm";

export default ko.components.register("default-report", {
    viewModel: function (params) {
        params.configKeys = [];
        ReportViewModel.apply(this, [params]);
    },
    template: defaultTemplate,
});
