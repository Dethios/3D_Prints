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
 "Background replacement only. Isolate exactly the complete Mickey artwork, two yellow shoes, white ribbon and all ten "
 "four-point twinkles already rendered in image 1. Replace the gold frame and the cream paper throughout with one completely "
 "solid flat matte deep navy (#1c3363) color identical inside and outside the former rim. No rim or border. The lower-left "
 "curled swirl, the tiny star beside its curl, both whole shoes, and the upper-right loop must remain 100% complete and "
 "unchanged from image 1, including those parts that extend past the gold frame right now. Image 2 supports the exact original "
 "sticker artwork placement. Keep the figure, artwork color, every contour, angle, size, and the ten stars registered in the "
 "same position as image 1, preserving all pixel detail. Do not recolor or redesign Mickey, do not add extra objects, and "
 "do not alter the typography-free square framing. Flat navy everywhere behind the artwork with no lighting or field gradient."
)
seed = 20261123894
key = "mickey-sticker-isolate-full-art"
g = graph(["qwen-sticker-first.png", "sticker-composition.png"], prompt, seed, key)
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
(out / "workflow-isolate-api.json").write_text(json.dumps(g, indent=2) + "\n")
job = post("/prompt", {"prompt":g,"client_id":session})["prompt_id"]
(out / "isolate-job.json").write_text(json.dumps({"prompt_id":job,"session":session}) + "\n")
print(job)
