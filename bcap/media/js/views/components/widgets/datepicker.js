// Override of node_modules/arches/arches/app/media/js/views/components/widgets/datepicker.js
//
// This file is a verbatim copy of the upstream arches widget with two patches
// added so the graph designer's "Disable Editing" switch works for date nodes
// (#1179). The diff vs. upstream is contained to the two `BCAP OVERRIDE` blocks
// below - keep this file in sync with upstream when bumping arches, applying
// only those two changes.
import ko from 'knockout';
import koMapping from 'knockout-mapping';
import _ from 'underscore';
import WidgetViewModel from 'viewmodels/widget';
import datePickerWidgetTemplate from 'templates/views/components/widgets/datepicker.htm';
import 'bindings/datepicker';
import 'bindings/moment-date';
import 'bindings/chosen';
import 'bindings/key-events-click';


var DatePickerWidget = function(params) {
    var self = this;
    // ===== BCAP OVERRIDE (1/2): add 'uneditable' so the config-form switch persists =====
    params.configKeys = ['minDate', 'maxDate', 'viewMode', 'dateFormat', 'defaultValue', 'uneditable'];
    // ===== END BCAP OVERRIDE =====

    WidgetViewModel.apply(this, [params]);

    if (self.node.config && ko.unwrap(self.node.config.dateFormat)) {
        this.dateFormat(ko.unwrap(self.node.config.dateFormat));
    }
    if (!ko.unwrap(this.dateFormat)) {
        this.dateFormat = ko.observable(self.node.datatypeLookup.date.config);
    }

    // ===== BCAP OVERRIDE (2/2): template binds `disable: disable` to this computed =====
    this.disable = ko.computed(() => {
        return ko.unwrap(self.disabled) || ko.unwrap(self.uneditable);
    }, self);
    // ===== END BCAP OVERRIDE =====

    this.placeholder = this.config().placeholder;
    this.viewModeOptions = ko.observableArray([{
        'id': 'days',
        'name': 'Days'
    }, {
        'id': 'months',
        'name': 'Months'
    }, {
        'id': 'years',
        'name': 'Years'
    }, {
        'id': 'decades',
        'name': 'Decades'
    }]);

    this.onViewModeSelection = function(val, e) {
        this.viewMode(e.currentTarget.value);
    };

    this.on = this.config().on || 'Date of Data Entry';
    this.off = this.config().off || '';
    this.setvalue = this.config().setvalue || function(self){
        if(self.defaultValue() === self.on){
            self.defaultValue(self.off);
        }else{
            self.defaultValue(self.on);
        }
    };

    this.setdefault = this.config().setdefault || function(self){
        if(self.defaultValue() === self.on){
            self.defaultValue(self.off);
        }else{
            self.defaultValue(self.on);
        }
    };

    this.getdefault = this.config().getdefault || ko.computed(function(){
        return this.defaultValue() == this.on;
    }, this);

    if (self.form && this.defaultValue() === 'Date of Data Entry') {
        if (this.value() === 'Date of Data Entry') {
            const today = new Date();
            self.value(today.toLocaleDateString("en-CA"));
            const tileData = JSON.parse(self.tile._tileData());
            tileData[this.node.id] = today.toLocaleDateString("en-CA");
            self.tile._tileData(koMapping.toJSON(tileData));
        }
    }

    this.disposables.push(this.getdefault);
};

export default ko.components.register('datepicker-widget', {
    viewModel: DatePickerWidget,
    template: datePickerWidgetTemplate,
});
