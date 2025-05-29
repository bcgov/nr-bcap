import ko from "knockout";
import MapReportViewModel from "viewmodels/bcap-site";
import defaultSiteTemplate from "templates/views/report-templates/details/archaeological_site.htm";

export default ko.components.register("bcap-site-report", {
    viewModel: MapReportViewModel,
    template: defaultSiteTemplate,
});
