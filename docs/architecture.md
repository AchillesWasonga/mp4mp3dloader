# Architecture

## Overview
The MVP uses a wrapper application around proven media tools instead of building extraction logic from scratch.

Core components:
- yt-dlp for extraction and downloading
- ffmpeg for merging and conversion
- a lightweight custom interface for user input, output handling, and errors

## High-Level Flow
1. User provides a supported video URL
2. Application validates the input
3. Application passes the URL to yt-dlp
4. yt-dlp fetches the best available media streams
5. ffmpeg merges or converts streams as needed
6. Final file is saved locally
7. Application returns success or error feedback

## Component Responsibilities

### 1. Input Layer
Responsible for:
- accepting a single URL
- selecting output type (MP4 or MP3)
- optionally choosing an output folder

### 2. Validation Layer
Responsible for:
- checking that the input looks like a supported URL
- detecting obvious invalid input before attempting download

### 3. Download Layer
Responsible for:
- invoking yt-dlp
- requesting highest available quality
- retrieving metadata such as title when available

### 4. Media Processing Layer
Responsible for:
- invoking ffmpeg when merging separate audio/video streams
- converting extracted audio to MP3 when needed
- preserving quality where possible

### 5. Output Layer
Responsible for:
- generating readable filenames
- writing files to the output directory
- reporting final file path to the user

### 6. Error Handling Layer
Responsible for:
- surfacing unsupported or invalid URLs
- reporting authentication-related failures
- reporting merge/conversion failures
- handling unavailable or private content

## Recommended MVP Interface
CLI-first.

Reason:
- fastest to build
- simplest to test
- lowest overhead
- easiest to demo internally

## Platform Support Strategy
### Phase 1
- YouTube videos
- YouTube Shorts

### Phase 2
- Instagram Reels

Instagram support is intentionally delayed because reliability and authentication are more complex.

## Quality Strategy
To preserve highest possible quality:
- request best available video stream
- request best available audio stream
- merge streams without unnecessary re-encoding when possible
- convert only when required for output compatibility

## File Output Strategy
Recommended defaults:
- save files in a dedicated output folder
- use media title in the filename when available
- sanitize filenames for filesystem safety

## Reliability Strategy
- keep yt-dlp updated
- keep ffmpeg installed and accessible
- use clear error messages for known failure states
- isolate platform-specific logic where possible

## Security and Operational Notes
- do not hardcode credentials
- if Instagram authentication is later needed, use a secure local credential/session approach
- avoid storing sensitive tokens in source control

## Future Extensions
Later versions could add:
- local web UI
- batch processing
- metadata sidecar files
- source attribution logging
- watermark and edit pipeline integration
- posting/scheduling workflow support