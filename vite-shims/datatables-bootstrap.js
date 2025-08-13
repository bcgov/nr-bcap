import $ from 'jquery';

if (typeof window !== 'undefined') {
  window.$ = window.jQuery = window.jQuery || $;
}

import 'datatables.net';                    // core
import 'datatables.net-bs/js/dataTables.bootstrap.min.js';
import 'datatables.net-buttons';
import 'datatables.net-buttons-bs/js/buttons.bootstrap.min.js';
import 'datatables.net-buttons/js/buttons.html5.min.js';
import 'datatables.net-buttons/js/buttons.print.min.js';

export default $;