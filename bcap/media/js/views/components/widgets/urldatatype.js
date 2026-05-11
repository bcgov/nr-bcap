// Override of node_modules/arches/arches/app/media/js/views/components/widgets/urldatatype.js
//
// This file is a verbatim copy of the upstream arches widget with two patches
// added so the graph designer's "Disable Editing" switch works for url nodes
// (#1179). The diff vs. upstream is contained to the two `BCAP OVERRIDE` blocks
// below - keep this file in sync with upstream when bumping arches, applying
// only those two changes.
import ko from 'knockout';
import WidgetViewModel from 'viewmodels/widget';
import urlDatatypeWidgetTemplate from 'templates/views/components/widgets/urldatatype.htm';


var name = 'urldatatype';
const viewModel = function(params) {
    const self = this;
    // ===== BCAP OVERRIDE (1/2): add 'uneditable' so the config-form switch persists =====
    params.configKeys = ['url_placeholder','url_label_placeholder','link_color','uneditable'];
    // ===== END BCAP OVERRIDE =====
    params.valueProperties = ['url', 'url_label'];

    WidgetViewModel.apply(this, [params]);

    // ===== BCAP OVERRIDE (2/2): template binds `disable: disable` to this computed =====
    this.disable = ko.computed(() => {
        return ko.unwrap(self.disabled) || ko.unwrap(self.uneditable);
    }, self);
    // ===== END BCAP OVERRIDE =====

    if (ko.isObservable(this.value)) {

        // #10027 assign this.url & this.url_label with value versions for updating UI with edits
        if (this.value()) {
            var valueUrl = this.value().url;
            var valueUrlLabel = this.value().url_label;
            this.url(valueUrl);
            this.url_label(valueUrlLabel);
        }

        this.value.subscribe(function(newValue) {
            if (newValue) {
                if (newValue.url) {
                    self.url(newValue.url);
                } else {
                    self.url(null);
                }
                if (newValue.url_label) {
                    self.url_label(newValue.url_label);
                } else {
                    self.url_label(null);
                    newValue.url_label = null;
                }
            } else {
                self.url(null);
                self.url_label(null);
                newValue.url = null;
                newValue.url_label = null;
            }
        });

    } else {
        if (this.value) {
            this.value.url.subscribe(function(newUrl) {
                if (newUrl) {
                    self.url(newUrl);
                } else {
                    self.url(null);
                }
            })
            this.value.url_label.subscribe(function(newUrlLabel) {
                if (newUrlLabel) {
                    self.url_label(newUrlLabel);
                } else {
                    self.url_label(null);
                }
            })
        }
    }

    this.urlPreviewText = ko.pureComputed(function() {
        if(self.url()){
            if (self.url_label && self.url_label()) {
                return self.url_label();
            } else if (self.url && self.url()) {
                return self.url();
            }
        }
        else{
            return "--";
        }
    }, this);

};

ko.components.register(name, {
    viewModel: viewModel,
    template: urlDatatypeWidgetTemplate,
});

export default name;
