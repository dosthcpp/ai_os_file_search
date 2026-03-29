#!/bin/bash
# Session Reset Script for OpenClaw
echo "Clearing agent sessions..."
rm -rf ~/.openclaw/agents/*/sessions/*
echo "Setting default model to gemini-3-flash-preview..."
openclaw models set google/gemini-3-flash-preview
echo "Restarting OpenClaw gateway..."
openclaw gateway restart
