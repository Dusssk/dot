@echo off
title Render+ Batch Server

:: Set this to the Blender version you want to use
SET "blender_version=4.3"
SET "python_version=3.11"

:: Set this to the path of Blender
SET "blender_path=C:\Program Files\Blender Foundation\Blender %blender_version%"
:: SET "blender_path=C:\Program Files (x86)\Steam\steamapps\common\Blender\%blender_version%"

:: This part builds the file paths to run the server
SET "python_bin=^"%blender_path%\%blender_version%\python\bin\python^""
SET "server_path="%APPDATA%\Blender Foundation\Blender\%blender_version%\extensions\user_default\renderplus\server""


if not exist %server_path% (
    ECHO Path to Batch Server incorrect. Please fix the blender_path variable in this bat file.
)

:: Finally, run the server
start "" %python_bin% %server_path%
