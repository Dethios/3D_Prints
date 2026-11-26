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
 "Put the ENTIRE Sorcerer Mickey sticker artwork from image 2 inside the gold-edged navy ear opening in image 1. "
 "Trace image 2 with close visual fidelity. Use its exact expressive face, blue bent pointed hat and two gold stars with gold crescent, "
 "red robe and gold rope, right hand pointing up with one raised index and thumb, lowered spread glove with three dark dashes, "
 "and most importantly BOTH soft, rounded golden-yellow flat cartoon shoes from image 2. Preserve exactly its small, partly robe-hidden "
 "left shoe extending to the left and its forward right shoe with rounded projecting toe and narrow heel next to black ankle. "
 "Same angles and proportions as image 2, with no brown oxfords, added toe seams or added boot soles. Use the exact long ivory "
 "ribbon-like spiral: thin rising hook at the upper right by the pointing finger, one broad sweep to the left past the face and hat, "
 "back around the waist to the right, then the curled lower-left tip. Keep the small distinct four-point ivory twinkles from the sticker "
 "in their relative places, including the upper-right, around the head and waist, and lower-left points. Copy the sticker artwork only. "
 "Remove the photographed finger, translucent border, photo surface texture, and bokeh. Use clean precise editorial illustration edges "
 "and solid sticker colors, restrained fine contours. Keep the exact mounted rim shape, angle, plain navy field, and border from image 1. "
 "Fit the whole sticker composition generously inside the ear, retain all star and swirl endpoints, and keep Mickey upright as in the sticker. "
 "Put the two visible shoes close to the lower region, keep the adjacent ivory curl visible. Deliver one full ear on cream paper."
)
seed = 20261123893
key = "mickey-sticker-in-mounted-ear"
g = graph(["blank-mounted-ear.png", "sticker-composition.png"], prompt, seed, key)
del g["4"]
for i, mp in ((1, .99), (2, .63)):
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
