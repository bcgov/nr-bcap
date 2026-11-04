import $ from 'jquery';
import arches from 'arches';
import ko from 'knockout';
import FunctionViewModel from 'viewmodels/function-view-model';
import contributorDescriptorsTemplate from 'templates/views/components/functions/contributor-descriptors.htm';

// The descriptor nodes are hardcoded in ContributorDescriptorNodes, so the only
// thing this panel offers is re-indexing.
export default ko.components.register(
    'views/components/functions/contributor-descriptors',
    {
        viewModel: function () {
            FunctionViewModel.apply(this, arguments);
            this.loading = ko.observable(false);

            this.reindexdb = function () {
                this.loading(true);
                $.ajax({
                    type: 'POST',
                    url: arches.urls.reindex,
                    context: this,
                    data: JSON.stringify({ graphids: [this.graph.graphid] }),
                    error: function () {
                        console.error('Re-index request failed');
                    },
                    complete: function () {
                        this.loading(false);
                    },
                });
            };
        },
        template: contributorDescriptorsTemplate,
    },
);
