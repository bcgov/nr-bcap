## Using Arches w/ QGIS
### Strategy
1. Use `pg_tileserv` for general site / site visit visibility. This can't be used to push geometries back to server
2. Use `pg_featureserv` to get actual GeoJSON geometry for editing / pushing back to the server.
3. Modify app proxy to host `pg_featuresrf`

### 1. Installing 
1. Download qgis_testing_package.zip file
2. Uncompress qgis_testing_package.zip file this will have several files in it:
   1. arches_project.zip - Arches plugin 
   1. basemap_config.xml - WMS config for the BC Roads basemap and Borden Grid
   2. bcap_wfs_config.xml - WFS config for BCAP features - both DLVR & TEST
   3. oauth_config.xml - OAuth config for DLVR & TEST
2. Install the Arches Plugin:
   1. Start QGIS
   2. Select Plugins -> Manage and Install Plugins...
   3. Select Install from ZIP from LHS menu
   4. Select the arches_project.zip file in the ZIP file box
   5. Press Install Plugin button
      1. Select "Yes" when the security warning comes up
   6. Click "Installed" from the LHS menu and ensure "Arches Project" checkbox is checked
   7. Close Window
3. Install OAuth configuration (password required)
   1. Select Settings -> Options... from top menu
   2. Select Authentication on the LHS menu
   3. Click Utilities button in the bottom right
   4. Select Import Authentication Configurations from File...
   5. Navigate to `qgis_testing_package/oauth_config.xml` and select the file
   6. Click the Open button
   7. Enter password provided
   8. Click OK
   9. NB - nothing will show up in the window. You can re-open the Autentication settings to confirm they are there. There should be 2 - One for TEST and one for DLVR
4. Import the BCAP WFS configurations
   1. Open the Layer -> Data Source Manager menu item
   2. Select the WFS / OGC API - Features in the LHS menu
   3. Press the Load button in the top right
   4. Navigate to the `qgis_testing_package/bcap_wfs_config.xml` file and select it
   5. Click the Open button
   6. Press the Select All button in the popup window
   7. Press the Import button
   8. You will see the Server connections dropdown list populated with those two connections
   9. Select the BCAP Features - DLVR option
   10. Press the Edit button
   11. In the Authentication -> Configurations tab select the BCAP - Django OAuth Toolkit - DLVR (OAuth2) option
   12. Press OK
   13. Repeat steps ix->xii, substituting TEST for DLVR in all steps
5. Import the WMS configurations
   1. Select WMS/WMTS in the LHS menu
   2. Press the Load button in the top right of the window
   3. Navigate to the `qgis_testing_package/basemap_config.xml` file and select it
   4. Click the Open button
   5. Press the Select All button in the popup window
   6. Press the Import button
   7. You will see the Server connections dropdown list populated with those two connections
6. You're done!

### 2. Logging into QGIS plugin using OAuth
1. Login to Arches in your _default_ web browser (QGIS will )
2. Click Arches from plugin
3. Select Authentication method from list
4. Browser window should appear for OAuth process
5. You should see auth window with your information

### 2. Map layers
- pg_tileserv layer (Vector Tile): `http://<hostname>/bcap/bctileserver/public.geojson_geometries/{z}/{x}/{y}.pbf?source=local`
- pg_featureserv layer (OGC API): `http://<hostname>/bcap/bctileserver/?source=local-feature`
- Borden Grid (Vector Tile): `https://openmaps.gov.bc.ca/geo/pub/WHSE_ARCHAEOLOGY.RAAD_BORDENGRID/ows?service=WMS&request=GetCapabilities`
- BC Roads Basemap (WMS):  `https://maps.gov.bc.ca/arcserver/services/Province/roads_wm/MapServer/WMSServer`

### 3. How to copy feature to push back to server
    1. Select feature from pg_featureserv layer
    2. Copy feature
    3. Paste feature as -> Temporary Scratch layer
    4. Toggle "Make layer editable"
    4. Edit feature
    5. Select feature
    6. In Arches Project tab, confirm the feature selected matches the one you want to update
    7. Click "Replace geometry"

### 4. TO DO
1. confirm tileserv and featuresrv authentiation/authorization
2. Can we (they) create an Action on the featuresrv to automate the copy?
8. Confirm edits are logged w/ user that made the changes

### 4. Issues
- Can't download full Site / Site Visit set of geometries - way too big
- More than one feature is being copied back to the server? Need to look at copy geometry process.
- featuresrv and tileserv are displaying project boundary geometry.
- OAuth access token is currently valid for a week. Can this be configured to be e24h?
- Can't currently create resources because geometries aren't top-level objects. Maybe we can do a different endpoint for this?
- When pushing a geometry up to BCAP, if the tile isn't in a state that it can be saved, a 500 error is returned. Maybe we can put a card-level trigger to set the edit type?

### 6. Other notes / findings / Gotchas 
- Filters can't be used directly on the Layer, it must be done on the Connection otherwise the OAuth config is lost