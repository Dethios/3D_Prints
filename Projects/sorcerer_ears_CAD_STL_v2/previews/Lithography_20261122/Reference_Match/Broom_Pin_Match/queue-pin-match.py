import json, os, urllib.request
from pathlib import Path
from PIL import Image

out = Path(os.environ["SORCERER_LITHO_OUTPUT"])
ref = out.parent
source = (ref.parent / "queue-comfyui.py").read_text(encoding="utf-8-sig")
exec(source.split("\ncommon=", 1)[0])
queue = json.load(urllib.request.urlopen(base + "/queue", timeout=10))
assert not queue["queue_running"] and not queue["queue_pending"]
for name in ("exact-broom-pin-contour-guide.png", "broom-direct-pin-reference.png"):
    (out / name).write_bytes((ref / name).read_bytes())
prompt = (
    "Restore the isolated enamel-pin broom from these two images into clean, crisp flat colors. "
    "Image 1 fixes the exact silhouette and placements and image 2 shows the same actual pin. Preserve its proportions "
    "and every edge, particularly both short asymmetric straw feet, the late rounded opening offset to the right of the shaft, "
    "the higher outward right toe and planted left toe, and the compact mitten hands gripping visibly separate handles. "
    "Keep both pails tilted outward with their original unequal placement. Use crisp thin gold and dark engraving lines, "
    "warm golden-yellow straw, red buckets with broad ivory hoops, and the exact same solid navy backdrop. "
    "Remove the tiny stray adjacent red cape fragment below the left bucket only. Present a single broom. "
    "The geometry remains registered to the guide at the same size. Smooth the color noise and improve edges."
)
seed = 20261123531
key = "broom-pin-regular-consistency"
g = graph(["exact-broom-pin-contour-guide.png", "broom-direct-pin-reference.png"], prompt, seed, key)
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
