import { afterEach, describe, expect, it, vi } from 'vitest';
import proj4 from 'proj4';
import shp from 'shpjs';

import * as shapefileImport from './shapefile-import';
import { processDroppedFiles, readFile } from './shapefile-import';

const point = (coordinates) => ({
    type: 'FeatureCollection',
    features: [
        {
            type: 'Feature',
            properties: {},
            geometry: { type: 'Point', coordinates },
        },
    ],
});

const NAD83_UTM_ZONE_10 =
    'PROJCS["NAD83 / UTM zone 10N",GEOGCS["NAD83",DATUM["North_American_Datum_1983",SPHEROID["GRS 1980",6378137,298.257222101]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-123],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1],AXIS["Easting",EAST],AXIS["Northing",NORTH]]';

const pointShapefile = (x, y) => {
    const buffer = new ArrayBuffer(128);
    const view = new DataView(buffer);
    view.setInt32(0, 9994, false);
    view.setInt32(24, 64, false);
    view.setInt32(28, 1000, true);
    view.setInt32(32, 1, true);
    view.setFloat64(36, x, true);
    view.setFloat64(44, y, true);
    view.setFloat64(52, x, true);
    view.setFloat64(60, y, true);
    view.setInt32(100, 1, false);
    view.setInt32(104, 10, false);
    view.setInt32(108, 1, true);
    view.setFloat64(112, x, true);
    view.setFloat64(120, y, true);
    return buffer;
};

const pointDbf = (value) => {
    const encodedValue = new TextEncoder().encode(value);
    const fieldLength = 20;
    const headerLength = 65;
    const recordLength = fieldLength + 1;
    const bytes = new Uint8Array(headerLength + recordLength + 1);
    const view = new DataView(bytes.buffer);
    bytes[0] = 3;
    view.setUint32(4, 1, true);
    view.setUint16(8, headerLength, true);
    view.setUint16(10, recordLength, true);
    bytes.set(new TextEncoder().encode('NAME'), 32);
    bytes[43] = 'C'.charCodeAt(0);
    bytes[48] = fieldLength;
    bytes[64] = 13;
    bytes[65] = 32;
    bytes.fill(32, 66, 66 + fieldLength);
    bytes.set(encodedValue, 66);
    bytes[bytes.length - 1] = 26;
    return bytes.buffer;
};

const crc32 = (bytes) => {
    let crc = 0xffffffff;
    bytes.forEach((byte) => {
        crc ^= byte;
        for (let bit = 0; bit < 8; bit += 1)
            crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
    });
    return (crc ^ 0xffffffff) >>> 0;
};

const storedZip = (files) => {
    const encoder = new TextEncoder();
    const localParts = [];
    const centralParts = [];
    let localOffset = 0;

    files.forEach(([name, contents]) => {
        const nameBytes = encoder.encode(name);
        const data =
            typeof contents === 'string'
                ? encoder.encode(contents)
                : new Uint8Array(contents);
        const checksum = crc32(data);
        const local = new Uint8Array(30 + nameBytes.length + data.length);
        const localView = new DataView(local.buffer);
        localView.setUint32(0, 0x04034b50, true);
        localView.setUint16(4, 20, true);
        localView.setUint32(14, checksum, true);
        localView.setUint32(18, data.length, true);
        localView.setUint32(22, data.length, true);
        localView.setUint16(26, nameBytes.length, true);
        local.set(nameBytes, 30);
        local.set(data, 30 + nameBytes.length);
        localParts.push(local);

        const central = new Uint8Array(46 + nameBytes.length);
        const centralView = new DataView(central.buffer);
        centralView.setUint32(0, 0x02014b50, true);
        centralView.setUint16(4, 20, true);
        centralView.setUint16(6, 20, true);
        centralView.setUint32(16, checksum, true);
        centralView.setUint32(20, data.length, true);
        centralView.setUint32(24, data.length, true);
        centralView.setUint16(28, nameBytes.length, true);
        centralView.setUint32(42, localOffset, true);
        central.set(nameBytes, 46);
        centralParts.push(central);
        localOffset += local.length;
    });

    const centralSize = centralParts.reduce(
        (total, part) => total + part.length,
        0,
    );
    const end = new Uint8Array(22);
    const endView = new DataView(end.buffer);
    endView.setUint32(0, 0x06054b50, true);
    endView.setUint16(8, files.length, true);
    endView.setUint16(10, files.length, true);
    endView.setUint32(12, centralSize, true);
    endView.setUint32(16, localOffset, true);

    const output = new Uint8Array(localOffset + centralSize + end.length);
    let offset = 0;
    [...localParts, ...centralParts, end].forEach((part) => {
        output.set(part, offset);
        offset += part.length;
    });
    return output.buffer;
};

const deferredReader = () => {
    const reads = new Map();
    const readFile = vi.fn((file, mode) => {
        return new Promise((resolve, reject) => {
            reads.set(file.name + ':' + mode, { resolve, reject });
        });
    });
    return { readFile, reads };
};

describe('processDroppedFiles', () => {
    afterEach(() => {
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    it('waits for the matching projection when the shapefile read finishes first', async () => {
        const { readFile, reads } = deferredReader();
        const parseShapefile = vi
            .fn()
            .mockResolvedValue(point([-121.614831, 49.644257]));
        const validateProjection = vi.fn();
        const processing = processDroppedFiles(
            [{ name: 'survey.shp' }, { name: 'survey.prj' }],
            { readFile, parseShapefile, validateProjection },
        );

        reads.get('survey.shp:arrayBuffer').resolve(new ArrayBuffer(8));
        await Promise.resolve();

        expect(parseShapefile).not.toHaveBeenCalled();

        reads.get('survey.prj:text').resolve('NAD83 / UTM zone 10N');
        const result = await processing;

        expect(validateProjection).toHaveBeenCalledWith('NAD83 / UTM zone 10N');
        expect(parseShapefile).toHaveBeenCalledWith({
            shp: expect.any(ArrayBuffer),
            prj: 'NAD83 / UTM zone 10N',
        });
        expect(result).toEqual({
            geoJSON: point([-121.614831, 49.644257]),
            errors: [],
        });
    });

    it('reprojects synthetic NAD83 UTM zone 10 bytes with real shpjs', async () => {
        const buffer = pointShapefile(600000, 5500000);
        const result = await processDroppedFiles(
            [{ name: 'survey.shp' }, { name: 'survey.prj' }],
            {
                readFile: vi.fn((file, mode) =>
                    Promise.resolve(
                        mode === 'text' ? NAD83_UTM_ZONE_10 : buffer,
                    ),
                ),
                parseShapefile: shp,
                validateProjection: (projection) => proj4(projection),
            },
        );

        const coordinates = result.geoJSON.features[0].geometry.coordinates;
        expect(coordinates[0]).toBeCloseTo(-121.614831, 6);
        expect(coordinates[1]).toBeCloseTo(49.644257, 6);
        expect(result.errors).toEqual([]);
    });

    it('preserves matching DBF properties and CPG Unicode for loose bundles', async () => {
        const files = [
            { name: 'survey.shp', contents: pointShapefile(600000, 5500000) },
            { name: 'survey.prj', contents: NAD83_UTM_ZONE_10 },
            { name: 'survey.dbf', contents: pointDbf('café') },
            { name: 'survey.cpg', contents: 'UTF-8' },
            { name: 'other.dbf', contents: pointDbf('wrong') },
        ];
        const result = await processDroppedFiles(files, {
            readFile: vi.fn((file) => Promise.resolve(file.contents)),
            parseShapefile: shp,
            validateProjection: (projection) => proj4(projection),
        });

        expect(result.errors).toEqual([]);
        expect(result.geoJSON.features[0].properties).toEqual({ NAME: 'café' });
    });

    it('matches each shapefile only to the projection with the same basename', async () => {
        const parseShapefile = vi.fn(({ prj }) =>
            Promise.resolve(
                point(prj === 'roads projection' ? [-123, 49] : [-124, 50]),
            ),
        );
        const readFile = vi.fn((file, mode) =>
            Promise.resolve(
                mode === 'text'
                    ? file.name.replace('.prj', ' projection')
                    : new ArrayBuffer(8),
            ),
        );

        const result = await processDroppedFiles(
            [
                { name: 'roads.shp' },
                { name: 'parcels.prj' },
                { name: 'parcels.shp' },
                { name: 'roads.prj' },
            ],
            { readFile, parseShapefile, validateProjection: vi.fn() },
        );

        expect(parseShapefile).toHaveBeenCalledWith({
            shp: expect.any(ArrayBuffer),
            prj: 'roads projection',
        });
        expect(parseShapefile).toHaveBeenCalledWith({
            shp: expect.any(ArrayBuffer),
            prj: 'parcels projection',
        });
        expect(
            result.geoJSON.features.map(
                (feature) => feature.geometry.coordinates,
            ),
        ).toEqual([
            [-123, 49],
            [-124, 50],
        ]);
    });

    it('rejects a bare shapefile instead of guessing its projection', async () => {
        const readFile = vi.fn().mockResolvedValue(new ArrayBuffer(8));
        const parseShapefile = vi.fn();

        const result = await processDroppedFiles([{ name: 'survey.shp' }], {
            readFile,
            parseShapefile,
            validateProjection: vi.fn(),
        });

        expect(parseShapefile).not.toHaveBeenCalled();
        expect(readFile).not.toHaveBeenCalled();
        expect(result).toEqual({
            geoJSON: { type: 'FeatureCollection', features: [] },
            errors: [
                {
                    message:
                        'Projection file missing for shapefile: "survey.shp"',
                },
            ],
        });
    });

    it('fails closed on duplicate case-insensitive projection basenames', async () => {
        const readFile = vi.fn();
        const parseShapefile = vi.fn();

        const result = await processDroppedFiles(
            [
                { name: 'survey.shp' },
                { name: 'survey.prj' },
                { name: 'SURVEY.PRJ' },
            ],
            { readFile, parseShapefile, validateProjection: vi.fn() },
        );

        expect(parseShapefile).not.toHaveBeenCalled();
        expect(readFile).not.toHaveBeenCalled();
        expect(result.errors).toEqual([
            {
                message:
                    'Projection file is ambiguous for shapefile: "survey.shp"',
            },
        ]);
    });

    it('rejects an invalid projection without parsing its shapefile', async () => {
        const parseShapefile = vi.fn();
        const validateProjection = vi.fn(() => {
            throw new Error('unrecognized projection');
        });
        const readFile = vi.fn((file, mode) =>
            Promise.resolve(
                mode === 'text' ? 'not a projection' : new ArrayBuffer(8),
            ),
        );

        const result = await processDroppedFiles(
            [{ name: 'survey.shp' }, { name: 'survey.prj' }],
            { readFile, parseShapefile, validateProjection },
        );

        expect(parseShapefile).not.toHaveBeenCalled();
        expect(result.errors).toEqual([
            {
                message:
                    'Unable to import shapefile "survey.shp": unrecognized projection',
            },
        ]);
        expect(result.geoJSON.features).toEqual([]);
    });

    it('rejects shapefile output that was not transformed to WGS84', async () => {
        const result = await processDroppedFiles(
            [{ name: 'survey.shp' }, { name: 'survey.prj' }],
            {
                readFile: vi.fn((file, mode) =>
                    Promise.resolve(
                        mode === 'text'
                            ? 'valid projection'
                            : new ArrayBuffer(8),
                    ),
                ),
                parseShapefile: vi
                    .fn()
                    .mockResolvedValue(point([600000, 5500000])),
                validateProjection: vi.fn(),
            },
        );

        expect(result.geoJSON.features).toEqual([]);
        expect(result.errors).toEqual([
            {
                message:
                    'Unable to import shapefile "survey.shp": Projection did not transform coordinates to WGS84',
            },
        ]);
    });

    it('rejects plausible WGS84 shapefile output outside the buffered B.C. envelope', async () => {
        const result = await processDroppedFiles(
            [{ name: 'survey.shp' }, { name: 'survey.prj' }],
            {
                readFile: vi.fn((file, mode) =>
                    Promise.resolve(
                        mode === 'text'
                            ? 'valid but mismatched projection'
                            : new ArrayBuffer(8),
                    ),
                ),
                parseShapefile: vi
                    .fn()
                    .mockResolvedValue(point([-73.5673, 45.5019])),
                validateProjection: vi.fn(),
            },
        );

        expect(result.geoJSON.features).toEqual([]);
        expect(result.errors).toEqual([
            {
                message:
                    'Unable to import shapefile "survey.shp": Shapefile coordinates fall outside the supported B.C. area',
            },
        ]);
    });

    it('keeps GeoJSON imports unchanged', async () => {
        const geoJSON = point([-123, 49]);
        const readFile = vi.fn().mockResolvedValue(JSON.stringify(geoJSON));

        const result = await processDroppedFiles([{ name: 'point.geojson' }], {
            readFile,
            parseShapefile: vi.fn(),
            validateProjection: vi.fn(),
            parseKml: vi.fn(),
        });

        expect(readFile).toHaveBeenCalledWith(
            { name: 'point.geojson' },
            'text',
        );
        expect(result).toEqual({ geoJSON, errors: [] });
    });

    it('rejects structurally invalid GeoJSON without rejecting the batch', async () => {
        const result = await processDroppedFiles([{ name: 'bad.geojson' }], {
            readFile: vi.fn().mockResolvedValue('{"type":"FeatureCollection"}'),
            parseShapefile: vi.fn(),
            validateProjection: vi.fn(),
            parseKml: vi.fn(),
        });

        expect(result.geoJSON.features).toEqual([]);
        expect(result.errors).toEqual([
            {
                message:
                    'Unable to import file "bad.geojson": Imported data is not a valid GeoJSON FeatureCollection',
            },
        ]);
    });

    it('surfaces an asynchronous shapefile parser failure', async () => {
        const result = await processDroppedFiles(
            [{ name: 'survey.shp' }, { name: 'survey.prj' }],
            {
                readFile: vi.fn((file, mode) =>
                    Promise.resolve(
                        mode === 'text'
                            ? NAD83_UTM_ZONE_10
                            : new ArrayBuffer(8),
                    ),
                ),
                parseShapefile: vi
                    .fn()
                    .mockRejectedValue(new Error('truncated shapefile')),
                validateProjection: vi.fn(),
            },
        );

        expect(result.geoJSON.features).toEqual([]);
        expect(result.errors).toEqual([
            {
                message:
                    'Unable to import shapefile "survey.shp": truncated shapefile',
            },
        ]);
    });

    it('keeps valid ZIP shapefile imports working', async () => {
        const buffer = storedZip([
            ['survey.shp', pointShapefile(600000, 5500000)],
            ['survey.prj', NAD83_UTM_ZONE_10],
            ['survey.dbf', pointDbf('café')],
            ['survey.cpg', 'UTF-8'],
        ]);

        const result = await processDroppedFiles([{ name: 'shapes.zip' }], {
            readFile: vi.fn().mockResolvedValue(buffer),
            parseShapefile: shp,
            validateProjection: (projection) => proj4(projection),
        });

        expect(result.errors).toEqual([]);
        expect(result.geoJSON.features[0].properties).toEqual({ NAME: 'café' });
        expect(result.geoJSON.features[0].geometry.coordinates[0]).toBeCloseTo(
            -121.614831,
            6,
        );
    });

    it.each([
        {
            name: 'missing',
            entries: [['survey.shp', pointShapefile(600000, 5500000)]],
            detail: 'Projection file missing for archived shapefile: "survey.shp"',
        },
        {
            name: 'duplicate',
            entries: [
                ['survey.shp', pointShapefile(600000, 5500000)],
                ['survey.prj', NAD83_UTM_ZONE_10],
                ['SURVEY.PRJ', NAD83_UTM_ZONE_10],
            ],
            detail: 'Projection file is ambiguous for archived shapefile: "survey.shp"',
        },
        {
            name: 'case-mismatched filename',
            entries: [
                ['survey.shp', pointShapefile(600000, 5500000)],
                ['SURVEY.PRJ', NAD83_UTM_ZONE_10],
            ],
            detail: 'Projection filename does not exactly match archived shapefile: "survey.shp"',
        },
        {
            name: 'empty',
            entries: [
                ['survey.shp', pointShapefile(600000, 5500000)],
                ['survey.prj', ''],
            ],
            detail: 'Projection file is empty',
        },
        {
            name: 'invalid',
            entries: [
                ['survey.shp', pointShapefile(600000, 5500000)],
                ['survey.prj', 'not a projection'],
            ],
            detail: 'Projection file is invalid',
        },
    ])('rejects a ZIP with a $name projection', async ({ entries, detail }) => {
        const parseShapefile = vi.fn();
        const result = await processDroppedFiles([{ name: 'shapes.zip' }], {
            readFile: vi.fn().mockResolvedValue(storedZip(entries)),
            parseShapefile,
            validateProjection: (projection) => {
                if (!projection.trim())
                    throw new Error('Projection file is empty');
                try {
                    proj4(projection);
                } catch {
                    throw new Error('Projection file is invalid');
                }
            },
        });

        expect(parseShapefile).not.toHaveBeenCalled();
        expect(result.geoJSON.features).toEqual([]);
        expect(result.errors).toEqual([
            {
                message: 'Unable to import file "shapes.zip": ' + detail,
            },
        ]);
    });

    it('combines all feature collections returned by a ZIP', async () => {
        const first = point([-123, 49]);
        const second = point([-124, 50]);
        const buffer = storedZip([
            ['survey.shp', pointShapefile(600000, 5500000)],
            ['survey.prj', NAD83_UTM_ZONE_10],
        ]);

        const result = await processDroppedFiles([{ name: 'shapes.zip' }], {
            readFile: vi.fn().mockResolvedValue(buffer),
            parseShapefile: vi.fn().mockResolvedValue([first, second]),
            validateProjection: (projection) => proj4(projection),
        });

        expect(result.geoJSON.features).toEqual([
            first.features[0],
            second.features[0],
        ]);
        expect(result.errors).toEqual([]);
    });

    it('surfaces a malformed ZIP without rejecting the batch', async () => {
        const result = await processDroppedFiles([{ name: 'bad.zip' }], {
            readFile: vi
                .fn()
                .mockResolvedValue(new Uint8Array([1, 2, 3]).buffer),
            parseShapefile: vi.fn(),
            validateProjection: vi.fn(),
        });

        expect(result.geoJSON.features).toEqual([]);
        expect(result.errors).toHaveLength(1);
        expect(result.errors[0].message).toMatch(
            /^Unable to import file "bad\.zip":/,
        );
    });

    it('rejects malformed KML before conversion', () => {
        expect(shapefileImport.parseKmlText).toBeTypeOf('function');
        const convertKml = vi.fn();

        expect(() =>
            shapefileImport.parseKmlText(
                '<kml><Placemark></kml>',
                new window.DOMParser(),
                convertKml,
            ),
        ).toThrow('KML document is malformed');
        expect(convertKml).not.toHaveBeenCalled();
    });

    it('keeps KML imports working', async () => {
        const geoJSON = point([-123, 49]);
        const parseKml = vi.fn().mockReturnValue(geoJSON);

        const result = await processDroppedFiles([{ name: 'point.kml' }], {
            readFile: vi.fn().mockResolvedValue('<kml/>'),
            parseShapefile: vi.fn(),
            validateProjection: vi.fn(),
            parseKml,
        });

        expect(parseKml).toHaveBeenCalledWith('<kml/>');
        expect(result).toEqual({ geoJSON, errors: [] });
    });

    it('turns a final file-handler rejection into a visible error', async () => {
        expect(shapefileImport.finishDroppedFileImport).toBeTypeOf('function');
        const setErrors = vi.fn();

        const result = await shapefileImport.finishDroppedFileImport(
            Promise.reject(new Error('unexpected import failure')),
            'node-id',
            vi.fn(),
            setErrors,
        );

        const errors = [
            {
                message:
                    'Unable to import dropped files: unexpected import failure',
            },
        ];
        expect(setErrors).toHaveBeenCalledWith(errors);
        expect(result).toEqual({
            geoJSON: { type: 'FeatureCollection', features: [] },
            errors,
        });
    });

    it('surfaces a FileReader failure without waiting indefinitely', async () => {
        const result = await processDroppedFiles(
            [{ name: 'survey.shp' }, { name: 'survey.prj' }],
            {
                readFile: vi
                    .fn()
                    .mockRejectedValue(new Error('Unable to read file')),
                parseShapefile: vi.fn(),
                validateProjection: vi.fn(),
            },
        );

        expect(result.geoJSON.features).toEqual([]);
        expect(result.errors).toEqual([
            {
                message:
                    'Unable to import shapefile "survey.shp": Unable to read file',
            },
        ]);
    });

    it('rejects when FileReader cannot read a file', async () => {
        class FailingReader {
            readAsText() {
                this.onerror();
            }
        }
        vi.stubGlobal('FileReader', FailingReader);

        await expect(readFile({ name: 'broken.prj' }, 'text')).rejects.toThrow(
            'Unable to read file: "broken.prj"',
        );

        vi.unstubAllGlobals();
    });
});
