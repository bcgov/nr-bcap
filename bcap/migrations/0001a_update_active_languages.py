from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("bcap", "0001_initial"),
    ]

    set_default_language = """ 
        update languages set isdefault =  code = 'en';
    """

    operations = [
        migrations.RunSQL(
            set_default_language,
            migrations.RunSQL.noop,
        ),
    ]
