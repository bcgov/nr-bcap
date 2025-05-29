import ko from "knockout";
import defaultBcapSiteTemplate from "templates/views/report-templates/bcap_default.htm";
import MapReportViewModel from "viewmodels/map-report";
export default ko.components.register("bcap-site-report", {
    viewModel: MapReportViewModel,
    template: defaultBcapSiteTemplate,
});
