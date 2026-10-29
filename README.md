# MP4 FFmpeg Playblast for Maya

Create MP4 playblasts with timeline audio from Maya's normal Playblast Options. Videos open automatically when finished.

**Windows 10/11 · Maya 2023 tested · Maya 2024–2027 experimental**

## Install

1. Download and extract the ZIP.
2. Open Maya and drag `install.py` into the viewport.
3. Wait for **“MP4 FFmpeg installed successfully.”** Then restart Maya.

No shelf button or separate FFmpeg installation is needed. The GitHub package downloads FFmpeg during first setup; internet access is required once.

## Use

1. Open **Playblast Options**.
2. Choose **MP4 (FFmpeg)** and click **Playblast**.

With **Save to File** off, videos use the scene name in your project's movie folder. Turn it on to use your own filename/path. If the output is open or locked, the new MP4 goes directly into Windows Temp and a message shows its location. Temporary AVI files are deleted after successful export.

## Clipboard (optional)

In `scripts/maya_ffmpeg_playblast/config.py`, change:

```python
COPY_TO_CLIPBOARD = True
```

The default is `False`. Restart Maya after editing the installed file. When enabled, paste the completed video into your chat app.

## Update or remove

To update, install the new ZIP and restart Maya. To disable it, uncheck **Auto load** and unload `mayaFfmpegPlayblast.py` in Maya's Plug-in Manager.

Developed with assistance from **OpenAI Codex (AI)**, with feedback and testing by the project owner.

FFmpeg is a separate third-party program downloaded from [Gyan's FFmpeg builds](https://www.gyan.dev/ffmpeg/builds/). Its license and notices are retained during setup.
