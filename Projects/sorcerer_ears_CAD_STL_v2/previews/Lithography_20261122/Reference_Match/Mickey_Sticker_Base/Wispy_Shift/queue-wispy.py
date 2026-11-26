import json, os, urllib.request
from pathlib import Path
from PIL import Image

out = Path(os.environ["SORCERER_LITHO_OUTPUT"])
ref = out.parent.parent
source = (ref.parent / "queue-comfyui.py").read_text(encoding="utf-8-sig")
exec(source.split("\ncommon=", 1)[0])
queue = json.load(urllib.request.urlopen(base + "/queue", timeout=10))
assert not queue["queue_pending"]
prompt = (
 "Edit image 1, keeping the complete character exactly as it is at the original position and scale. "
 "Change ONLY the magical ivory ribbon that winds in the air behind Mickey. Make that same existing spiral much lighter, "
 "more wispy and delicate, with thin smooth gas-like streams, long graceful tapered ends and a few slender nested strokes. "
 "The current thick opaque white band should become a controlled airy ribbon, mostly one-third the previous thickness, "
 "still crisp and readable on the same dark navy field and light ivory, no blurred edges or fog. Keep the original exact "
 "spiral path and occlusion, from the pointing fingertip and upper-right hook to the broad left return and across the waist "
 "to the lower loop and curled lower-left tail. Preserve the ten twinkles in their exact positions. Do not modify Mickey "
 "including his outline, proportions, face, costume, hands, shoes, palette or pose. Image 2 identifies the original pose "
 "and magic motif. Preserve the square scene framing and the clean outline style of image 1."
)
seed = 20261123931
key = "mickey-sticker-wispy-spiral"
g = graph(["sticker-art-navy.png", "sticker-pose-reference.png"], prompt, seed, key)
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
