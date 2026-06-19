from django.db import migrations


class Migration(migrations.Migration):
    # Pin jit=off on the per-tile geojson refresh. It's a sub-ms point write run
    # once per tile, so JIT's per-call LLVM compile is pure overhead (~1.7x
    # slower seeding, measured). Depends on the arches migration that last
    # (re)defines the function so it exists before the ALTER.
    dependencies = [
        ("bcap", "1419_register_assign_application_id_function"),
        ("models", "10799_geojsongeometry_featureid"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER FUNCTION refresh_tile_geojson_geometries(uuid) "
                "SET jit = off;"
            ),
            reverse_sql=(
                "ALTER FUNCTION refresh_tile_geojson_geometries(uuid) "
                "RESET jit;"
            ),
        ),
    ]
