from ffmpeg import input as ff_input, output as ff_output, concat as ff_concat
import tempfile, os

def render_video(scenes, audio_path, output_path):
    clips = []
    for idx, scene in enumerate(scenes):
        duration = scene.get("duration", 3)
        text = scene.get("text", "")
        # create a colored background clip with overlaid text
        bg = ff_input(f"color=black:size=720x1280:rate=25:duration={duration}", f="lavfi")
        txt = (
            ff_output(bg, f"pipe:{idx}.mp4",
                      vf=f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                         f"text='{text}':x=(w-text_w)/2:y=(h-text_h)/2:fontsize=48:fontcolor=white",
                      vcodec="libx264", pix_fmt="yuv420p", t=duration)
        )
        txt.run(overwrite_output=True)
        clips.append(ff_input(f"pipe:{idx}.mp4", format="mp4", framerate=25))

    # concatenate
    joined = ff_concat(*clips, v=1, a=0).node
    v = joined[0]
    # add audio and produce final
    out = ff_output(v, audio_path, output_path, vcodec="libx264", acodec="aac", shortest=None)
    out.run(overwrite_output=True)

    # cleanup
    for idx in range(len(scenes)):
        os.remove(f"pipe:{idx}.mp4")
