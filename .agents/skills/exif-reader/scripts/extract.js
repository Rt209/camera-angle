#!/usr/bin/env node
/**
 * exif-reader skill script
 * Extracts EXIF metadata from image files using the exifr library.
 *
 * Usage: node extract.js "<image-path>"
 * Output: JSON to stdout
 *
 * Requires: exifr (installed in project root node_modules)
 */

import { parse } from 'exifr';
import { resolve } from 'path';

const filePath = process.argv[2];

if (!filePath) {
  console.error(JSON.stringify({ error: 'Usage: node extract.js "<image-path>"' }));
  process.exit(1);
}

const absolutePath = resolve(filePath);

parse(absolutePath, {
  tiff: true,
  exif: true,
  gps: true,
  icc: false,
  iptc: false,
  xmp: false,
  pick: [
    'DateTimeOriginal',
    'CreateDate',
    'GPSLatitude',
    'GPSLongitude',
    'GPSLatitudeRef',
    'GPSLongitudeRef',
    'Make',
    'Model',
    'ImageWidth',
    'ImageHeight',
    'ExifImageWidth',
    'ExifImageHeight',
    'Orientation',
  ],
})
  .then((exif) => {
    if (!exif) {
      console.log(JSON.stringify({}));
      return;
    }

    const result = {};

    // Capture time: prefer DateTimeOriginal over CreateDate
    const rawDate = exif.DateTimeOriginal ?? exif.CreateDate ?? null;
    result.created_at = rawDate ? rawDate.toISOString() : null;

    // GPS coordinates
    const lat = exif.GPSLatitude ?? null;
    const lng = exif.GPSLongitude ?? null;
    if (lat !== null && lng !== null) {
      result.location = { lat, lng };
    } else {
      result.location = null;
    }

    // Device (combine Make + Model, deduplicate prefix)
    const make = exif.Make?.trim() ?? null;
    const model = exif.Model?.trim() ?? null;
    if (make && model) {
      result.device = model.startsWith(make) ? model : `${make} ${model}`;
    } else {
      result.device = model ?? make ?? null;
    }

    // Dimensions
    result.width = exif.ExifImageWidth ?? exif.ImageWidth ?? null;
    result.height = exif.ExifImageHeight ?? exif.ImageHeight ?? null;

    // Orientation
    result.orientation = exif.Orientation ?? null;

    console.log(JSON.stringify(result, null, 2));
  })
  .catch((err) => {
    console.error(JSON.stringify({ error: err.message }));
    process.exit(1);
  });
