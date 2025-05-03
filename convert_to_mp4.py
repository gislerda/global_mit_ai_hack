import subprocess
from pathlib import Path

input_dir = Path("convert")
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

for mkv_file in input_dir.glob("*.mkv"):
    output_file = output_dir / f"{mkv_file.stem}.mp4"
    
    command = [
        "ffmpeg",
        "-i", str(mkv_file),
        "-c:v", "copy",     # Copy video without re-encoding
        "-c:a", "aac",      # Convert audio to AAC (widely supported)
        "-b:a", "192k",
        str(output_file)
    ]
    
    print(f"🔄 Converting {mkv_file.name} to {output_file.name}")
    subprocess.run(command, check=True)

print("✅ All files converted.")
