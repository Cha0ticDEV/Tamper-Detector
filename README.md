# 🔍 Digital Document Tamper Detector

A Python desktop **image-forensics prototype** for investigating possible manipulation in digital document images.

## Three checks

1. **Adaptive Error Level Analysis (ELA)** — compares JPEG compression behavior using image-adaptive block statistics.
2. **Local consistency analysis** — compares local high-frequency/noise characteristics between neighboring image regions.
3. **File & metadata inspection** — reports format, resolution, file size and EXIF count.

The GUI combines the first two checks into primary evidence and keeps metadata informational.

> **Important:** This is not an official document-authentication system. It does not prove that a document is genuine, fake, or fraudulent.

## Why this version is better

The earlier prototype used fixed global thresholds. Small edits can occupy only a tiny part of a document and disappear in global statistics.

This version uses:
- adaptive ELA thresholds
- block-level statistics
- robust outlier detection
- local neighborhood comparison
- clustered anomalies
- a visual anomaly overlay
- metadata separated from the main tampering score

## Project structure

```text
digital-document-tamper-detector/
├── app/
│   ├── main.py
│   └── detector.py
├── assets/
│   └── screenshots/
├── sample_images/
├── requirements.txt
├── README.md
└── .gitignore
```

## Run

```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app\main.py
```

## Build Windows EXE

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed app\main.py
```

Output:

```text
dist\main.exe
```

## Testing

Create a small test set containing both clean and intentionally edited images:

```text
sample_images/
├── clean.jpg
├── edited_text.jpg
├── edited_photo.jpg
└── edited_region.jpg
```

For each image record what was changed and which check responded. Do not tune the detector simply to force every edited image to return "tampered".

## Limitations

The output is a forensic indicator, not proof. JPEG recompression, screenshots, scans, resizing, camera capture and export software can create or remove image-level traces.

The project cannot verify an Aadhaar number, verify a UIDAI digital signature, authenticate identity, identify an editor, or guarantee document authenticity.

For real document verification, use the relevant official verification mechanisms.

## Future improvements

- Copy-move detection
- OCR-assisted comparison
- QR-code consistency checks
- suspicious-region crops
- PDF forensic reports
- benchmark dataset
- precision/recall evaluation
- machine-learning features

## Tech stack

Python • Tkinter • Pillow • NumPy • PyInstaller
