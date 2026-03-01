# MP4/MP3 Downloader

A simple internal downloader tool for fetching high-quality media from supported video links without using third-party download websites.

## Overview

This project is being built to replace ad-filled external MP4/MP3 downloader sites with a cleaner internal workflow.

The MVP focuses on one job only:

- paste a supported URL
- choose MP4 or MP3
- download the highest available quality locally

## MVP Scope

This first version is intended for single-user internal use.

### Supported goals
- Download from YouTube videos
- Download from YouTube Shorts
- Output high-quality MP4
- Output MP3 audio
- Save files locally
- Avoid spammy third-party websites

### Not included in MVP
- watermarking
- logo overlays
- caption generation
- social media posting
- scheduling
- full workflow automation
- cloud deployment
- multi-user access

## Why this exists

Current third-party downloader websites often:
- reduce video/audio quality
- add ads and redirects
- feel unreliable or unsafe
- create unnecessary friction in a content workflow

This project aims to provide a cleaner and more reliable internal alternative.

## Proposed Architecture

The recommended implementation uses:

- **yt-dlp** for media extraction and downloading
- **ffmpeg** for merging/converting audio and video
- a lightweight custom wrapper for the user interface and workflow

## Target User

An internal team member who wants to download media from supported links quickly and at the highest available quality.

## User Story

> As an internal user, I want to paste a YouTube or Instagram link and download the media as MP4 or MP3 in the best available quality without using third-party websites.

## Functional Requirements

- Accept a single supported URL
- Allow MP4 or MP3 output selection
- Download best available audio/video quality
- Save files to a local folder
- Use readable filenames
- Show clear error messages for unsupported or failed downloads

## Initial Platform Support

### Priority 1
- YouTube videos
- YouTube Shorts

### Priority 2
- Instagram Reels

## Risks

- Instagram support may be less stable than YouTube
- Some content may require authentication
- Platform changes may require maintenance
- Content usage may require rights or permission depending on workflow

## Success Criteria

This MVP is successful if it can:
- download a YouTube or YouTube Shorts URL
- save a high-quality MP4 locally
- save an MP3 version when requested
- work reliably enough for an internal demo

## Future Enhancements

Possible future additions include:
- Instagram Reel reliability improvements
- batch downloads
- metadata logging
- watermarking
- caption generation
- creator attribution support
- automated posting workflow
- dashboard UI

## Status

Project setup has begun. Current focus is defining the MVP scope and architecture before implementation.

## Notes

This tool is intended for internal use. Any broader workflow involving reposting or redistribution should account for platform rules, permissions and copyright considerations.