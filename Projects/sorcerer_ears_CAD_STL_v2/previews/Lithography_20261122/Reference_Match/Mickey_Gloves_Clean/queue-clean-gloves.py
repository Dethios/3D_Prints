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
 "Cleanly restore the two hand details in image 1 in their exact positions, matching the glove anatomy and seams "
 "in image 2. On the left, Mickey's lifted ivory glove is seen PALM UP. Match the upright thumb, fingers held out "
 "together, the one short fold beside the thumb and small natural finger divisions near the tips. No three "
 "decorative dorsal knuckle lines on the raised palm. On the right the lower ivory glove is a compact relaxed curl "
 "with three short lines on the back of the hand and very short marks separating the curled finger tips. "
 "Keep the exact cuff positions and silhouettes, black wrists, red sleeve and navy background. Render each glove "
 "with solid clean ivory and crisp continuous thin dark-brown engraving and subtle antique-gold edge lines, "
 "just like finished flat vector enamel pin art. Remove all pixelation, blur and noisy shading. Do not move the crops, "
 "redesign the gloves, add extra fingers or regenerate the layout. The clean palm crease and two distinct hand poses "
 "matter above all."
)
seed = 20261123629
key = "mickey-glove-enamel-cleanup"
g = graph(["glove-shape-guide.png", "animation-gloves.png"], prompt, seed, key)
del g["4"]
for i, mp in ((1, .80), (2, .35)):
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
