"""Register the reference-number-widget from bcgov_arches_common.

The widget must exist in the widgets table before the bcap graphs are loaded
(0002_load_package), because the graph importer looks up each widget by id
when it configures CardXNodeXWidget rows.

Widget definition mirrors bcgov_arches_common/widgets/reference-number-widget.json.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("bcap", "0001d_fix_relational_views_for_reference_datatypes"),
    ]

    widget_sql = """
        INSERT INTO widgets (widgetid, name, component, defaultconfig, helptext, datatype)
        VALUES (
            '10000000-0000-0000-0000-000000001006',
            'reference-number-widget',
            'views/components/widgets/reference-number-widget',
            '{"width": "10%", "maxLength": 20, "uneditable": true, "defaultValue": "",
              "reportTypeAbbreviation": "AAA", "sequenceDigits": 4}',
            null,
            'non-localized-string'
        )
        ON CONFLICT (widgetid) DO NOTHING;
    """

    reverse_sql = """
        DELETE FROM widgets WHERE widgetid = '10000000-0000-0000-0000-000000001006';
    """

    operations = [
        migrations.RunSQL(widget_sql, reverse_sql),
    ]
