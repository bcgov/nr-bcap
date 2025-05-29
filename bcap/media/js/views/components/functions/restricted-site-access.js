import ko from "knockout";
import FunctionViewModel from "viewmodels/function-view-model";
import defaultSampleFunctionTemplate from "templates/views/components/functions/restricted-site-access.htm";
export default ko.components.register(
    "views/components/functions/restricted-site-access",
    {
        viewModel: function (params) {
            FunctionViewModel.apply(this, arguments);
        },
        template: defaultSampleFunctionTemplate,
    },
);
