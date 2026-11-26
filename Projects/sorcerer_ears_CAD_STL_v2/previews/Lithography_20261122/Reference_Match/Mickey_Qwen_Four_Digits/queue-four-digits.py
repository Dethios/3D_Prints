import json, os, urllib.request
from pathlib import Path
from PIL import Image

out = Path(os.environ["SORCERER_LITHO_OUTPUT"])
ref = out.parent
source = (ref.parent / "queue-comfyui.py").read_text(encoding="utf-8-sig")
exec(source.split("\ncommon=", 1)[0])
queue = json.load(urllib.request.urlopen(base + "/queue", timeout=10))
assert not queue["queue_pending"]
prompt = (
    "Edit the single lowered left glove in image 1, fine smooth enamel illustration. Use the lowered clenched hand in "
    "image 2 as the anatomy reference. Exactly FOUR DIGITS TOTAL, anatomically classic Mickey Mouse: ONE short curled thumb "
    "on viewer-right and exactly THREE regular rounded curled fingers next to it. Under the fist draw ONLY TWO dividing seams "
    "between the three regular fingers. The small thumb notch is a separate contour at far right and belongs to the thumb. "
    "As a single local correction, fuse the two far-left narrow fingertip lobes into one broader smooth rounded fingertip, "
    "remove the leftmost fingertip separation line, and smooth the lower outer contour at that exact join. The other two short "
    "finger separations and the three back-of-glove seam dashes near the cuff remain. A solid warm ivory glove, gold and medium "
    "brown continuous sharp linework from image 1, exact wrist, cuff, sleeve, hand footprint, position, red and navy backdrop. "
    "No extra pinky, no fourth regular finger, no new seam below the glove and no changes elsewhere. Keep framing fixed. "
    "Every illustration contour should be smooth professional enamel-line detail."
)
seed = 20261123733
key = "mickey-lower-glove-four-total-digits"
g = graph(["lower-glove-context.png", "animation-pose-reference.png"], prompt, seed, key)
del g["4"]
for i, mp in ((1, .60), (2, .30)):
    n = str(30 + i)
    g[n] = node("AUSBOSS_NODES_ImageCropRotatePad", image=g[str(4+i)]["inputs"]["image"], rotation_degrees=0.0,
                crop_aspect_ratio="free", crop_x=0, crop_y=0, crop_width=0, crop_height=0,
                pad_left=0, pad_top=0, pad_right=0, pad_bottom=0, feather=0, canvas_multiple=16,
                fill_color="#163263", resize_to_megapixels=True, megapixels=mp, resize_method="lanczos",
                resolution_steps=16)
    del g[str(4+i)]
    g["10"]["inputs"][f"images.image_{i}"] = [n, 0]
del g["11"]
g["22"] = node("LoraLoaderModelOnly", model=["1",0], lora_name="qwen-image-2.1-consistency.safetensors", strength_model=.5)
g["23"] = node("BasicScheduler", model=["1",0], scheduler="simple", steps=40, denoise=1.0)
g["24"] = node("SplitSigmas", sigmas=["23",0], step=39)
g["25"] = node("KSamplerSelect", sampler_name="euler")
common = dict(noise_seed=seed, cfg=1.0, positive=["10",0], negative=["10",1], sampler=["25",0])
g["26"] = node("SamplerCustom", model=["22",0], add_noise=True, sigmas=["24",0], latent_image=["10",2], **common)
g["27"] = node("SamplerCustom", model=["1",0], add_noise=False, sigmas=["24",1], latent_image=["26",0], **common)
g["12"]["inputs"]["samples"] = ["27",0]
(out / "workflow-api.json").write_text(json.dumps(g, indent=2) + "\n")
job = post("/prompt", {"prompt":g,"client_id":session})["prompt_id"]
(out / "job.json").write_text(json.dumps({"prompt_id":job,"session":session}) + "\n")
print(job)
