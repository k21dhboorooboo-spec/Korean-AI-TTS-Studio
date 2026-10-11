WINDOWS EXE BUILD (not prebuilt)

This archive does not contain an EXE. It contains a GitHub Actions workflow
(.github/workflows/windows-exe.yml) that runs on Windows to produce:
- KoreanAITTSStudioNeural_Windows_Portable (folder containing .exe)
- KoreanAITTSStudioNeural_Windows_Setup (installer .exe)

Upload all files, including .github, to a GitHub repository and run
Actions > Build Windows EXE > Run workflow. Download artifacts after success.
First neural model use needs internet. Large CPU dependencies; builds can fail.
Windows build and speech inference have not been verified by the author.
