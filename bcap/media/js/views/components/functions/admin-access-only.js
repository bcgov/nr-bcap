import ko from "knockout";
import FunctionViewModel from "viewmodels/function-view-model";
import defaultSampleFunctionTemplate from "templates/views/components/functions/admin-access-only.htm";
export default ko.components.register(
    "views/components/functions/admin-access-only",
    {
        viewModel: function (params) {
            FunctionViewModel.apply(this, arguments);
        },
        template: defaultSampleFunctionTemplate,
    },
);
