#!/bin/bash
# Force refresh all model data
# EWW will automatically poll, but this triggers immediate refresh

notify-send "PurmaLinux" "Refreshing models..." -i view-refresh-symbolic -t 1000

# The poll variables will update automatically
# Just close and reopen to force refresh
eww close models-popup
sleep 0.2
eww open models-popup
