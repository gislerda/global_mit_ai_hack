# parse the script into scenes, generate silent black clips with text overlays, concat, then add audio
import json, sys
from ffmpeg import input as ff_input, output as ff_output, concat as ff_concat

# Pseudocode: parse scenes, create per-scene clip, then concat and mux audio
