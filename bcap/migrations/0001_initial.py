from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("models", "12229_add_lifecycle_filter_to_standard_search"),
        ("bcgov_arches_common", "2025-02-07_create_concept_functions"),
        ("guardian", "0002_generic_permissions_index"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("admin", "0003_logentry_add_action_flag_choices"),
        ("sessions", "0001_initial"),
        ("oauth2_provider", "0005_auto_20211222_2352"),
        ("django_celery_results", "0011_taskresult_periodic_task_name"),
    ]

    fn_sql = """
    insert into functions (functionid, functiontype, name, description, defaultconfig, modulename, classname, component)
    values ('60000000-0000-0000-0000-000000002001',
        'node',
        'Unique Boolean Value',
        'Enforces that only one card is set to the boolean value for a resource',
        '{"module": "bcgov_arches_common.functions.unique_boolean_value", "class_name": "UniqueBooleanValue", "triggering_nodegroups": []}',
        'unique_boolean_value.py',
        'UniqueBooleanValue',
        'views/components/functions/unique-boolean-value'
    );
    """

    reverse_fn_sql = """
        delete from functions where functionid = '60000000-0000-0000-0000-000000002001';
    """

    widget_sql = """
    INSERT INTO widgets (widgetid, name, component, defaultconfig, helptext, datatype) 
    VALUES ('0346bc9c-d235-4313-adc8-d0e210b2ef25', 
        'checkbox-boolean-widget', 
        'views/components/widgets/checkbox-boolean-widget', 
        '{"defaultValue": false}', null, 'boolean');
    """

    reverse_widget_sql = """
        delete from widgets where widgetid = '0346bc9c-d235-4313-adc8-d0e210b2ef25';
    """

    operations = [
        migrations.RunSQL(
            fn_sql,
            reverse_fn_sql,
        ),
        migrations.RunSQL(
            widget_sql,
            reverse_widget_sql,
        ),
    ]
