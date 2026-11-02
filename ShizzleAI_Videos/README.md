# ShizzleAI Video Archives

Videos are stored as AES-256 encrypted ZIP archives.

## How to restore an archive

1. Download all parts belonging to the same ZIP file.
2. Put all parts in the same folder.
3. Rebuild the original ZIP file.
4. Open the ZIP file with 7-Zip.
5. Enter the archive password.

### Windows CMD

```cmd
copy /b "12345.zip.part-*" "12345.zip"
```

### Linux

```bash
cat 12345.zip.part-* > 12345.zip
```

## Archive details

- Encryption: AES-256
- Archive format: ZIP
- Part size: 45 MB
- Downloader: yt-dlp + Aria2
- Aria2 connections: 16

## Latest run

- Date: 2026-11-02 07:46:10 UTC
- Total links: 0
- Completed this run: 0
- Failed this run: 0
