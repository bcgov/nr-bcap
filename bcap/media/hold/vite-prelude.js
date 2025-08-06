// bcap/media/js/vite-prelude.js
import $ from 'jquery';
window.$ = window.jQuery = $;

import 'bootstrap/dist/js/bootstrap.js'; // attaches tooltip/popover onto $.fn

// DataTables (core first, then Bootstrap, then responsive, then buttons)
import 'datatables.net';                  // sets $.fn.dataTable
import 'datatables.net-bs';
import 'datatables.net-responsive';
import 'datatables.net-responsive-bs';
import 'datatables.net-buttons';
import 'datatables.net-buttons-bs';
import 'datatables.net-buttons-html5';
import 'datatables.net-buttons-print';

// Underscore + Backbone (Backbone needs $)
import _ from 'underscore';
window._ = _;
import Backbone from 'backbone';
Backbone.$ = $;
window.Backbone = Backbone;

// Knockout
import ko from 'knockout';
window.ko = ko;