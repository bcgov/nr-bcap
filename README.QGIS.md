## Using Arches w/ QGIS
### Strategy
1. Use `pg_tileserv` for general site / site visit visibility. This can't be used to push geometries back to server
2. Use `pg_featureserv` to get actual GeoJSON geometry for editing / pushing back to the server.
3. Modify app proxy to host `pg_featuresrf`

### 1. Installing 
1. Download zip file
2. Put in...?


### 2. OAuth
1. Configuration
    1. Create... 
1. Steps to authenticate
   1. Login to Arches in your web browser
   1. Click Arches from plugin
   2. Select Authentication method from list
   3. Browser window should appear for OAuth process
   4. You should see auth window with your information
   ``
### 2. Map layers
- pg_tileserv layer (Vector Tile): `http://localhost:82/bcap/bctileserver/public.geojson_geometries/{z}/{x}/{y}.pbf?source=local`
- pg_featureserv layer (OGC API): `http://localhost:82/bcap/bctileserver/?source=local-feature`
- Borden Grid (Vector Tile): `https://openmaps.gov.bc.ca/geo/pub/WHSE_ARCHAEOLOGY.RAAD_BORDENGRID/ows?service=WMS&request=GetCapabilities`
- BC Roads Basemap (WMS):  `https://maps.gov.bc.ca/arcserver/services/Province/roads_wm/MapServer/WMSServer`

### 3. How to copy feature to push back to server
    1. Select feature from pg_tileserv layer (need to figure out how to get whole feature)
    2. Copy feature
    3. Paste feature as -> Temporary Scratch layer
    4. Edit feature
    5. Select feature
    6. In Arches Project tab, confirm the feature selected matches the one you want to update
    7. Click "Replace geometry"

### 4. TO DO
1. confirm tileserv and featuresrv authentiation/authorization
2. Can we create an Action on the featuresrv to automate the copy?
3. Only show desired geometries in tileserv / featureserv - Site, Site Visit, Sandcastle?
4. Create a series of views that can be used to turn on/off and style layers (`Arch Site -> Boundary`, `Arch Site -> Unprotected`, `Site Visit.*`, `Sandcastle`?, )
5. Add CD to configure `pg_featuresrv`
6. Install `pg_featuresrv` on `ENDOWMENT.bcgov` and `EARLY.bcgov` 
7. Create OAuth provider config for QGIS
8. Confirm edits are logged w/ user that made the changes

### 4. Issues
- Using PG tileserv - selected layers aren't whole. Need to retrieve the whole feature from Arches to edit -> `pg_featuresrv`
- Can't download full Site / Site Visit set of geometries - way too big
- Need to merge with 1.0.0 of plugin
- How to authenticate/authorize pg_tileserv & pg_faturesrv? (Through proxy?). The OAuth2 provider access token seems to work. It's an All/Nothing right now though, not fine-grained.
- More than one feature is being copied back to the server? Need to look at copy geometry process.
- featuresrv and tileserv are displaying project boundary geometry.
- OAuth access token is currently valid for a week. Can this be configured to be e24h?

### 6. Other notes / findings
- Filters can't be used directly on the Layer, it must be done on the Connection otherwise the OAuth config is lost