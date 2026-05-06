---
name: exif-reader
description: "Extract EXIF metadata from image files (JPEG, PNG, HEIC, WebP). Use when you need the precise capture time, GPS coordinates, or device information embedded in a photo."
---

# EXIF Reader Skill

Extracts embedded EXIF metadata from image files using the `exifr` library. This provides reliable, precise data directly from the file — no AI inference needed.

## What it extracts

| Field | EXIF Source | Output key |
|-------|------------|------------|
| Capture time | `DateTimeOriginal` | `created_at` |
| GPS latitude | `GPSLatitude` | `location.lat` |
| GPS longitude | `GPSLongitude` | `location.lng` |
| Camera make | `Make` | `device` (combined) |
| Camera model | `Model` | `device` (combined) |
| Image width | `ImageWidth` | `width` |
| Image height | `ImageHeight` | `height` |
| Orientation | `Orientation` | `orientation` |

## Usage

```bash
node {baseDir}/scripts/extract.js "<image-path>"
```

Example:
```bash
node {baseDir}/scripts/extract.js "/Users/fanyang/Photos/disney.jpg"
```

## Output format

Returns JSON to stdout:
```json
{
  "created_at": "2019-08-03T14:22:11.000Z",
  "location": {
    "lat": 31.144,
    "lng": 121.657
  },
  "device": "Apple iPhone X",
  "width": 4032,
  "height": 3024,
  "orientation": 1
}
```

Fields are `null` when not present in the file. If no EXIF data exists at all, returns `{}`.

## Notes

- `created_at` is always preferred over the file system creation time
- GPS coordinates are in decimal degrees (WGS84)
- HEIC files from iPhones are fully supported via `exifr`
