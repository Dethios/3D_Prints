import json, os, urllib.request
from pathlib import Path
from PIL import Image

out = Path(os.environ["SORCERER_LITHO_OUTPUT"])
ref = out.parent.parent
source = (ref.parent / "queue-comfyui.py").read_text(encoding="utf-8-sig")
exec(source.split("\ncommon=", 1)[0])
queue = json.load(urllib.request.urlopen(base + "/queue", timeout=10))
assert not queue["queue_running"] and not queue["queue_pending"]
prompt = (
    "Restore image 1 as a crisp enamel-pin design on its existing plain deep navy background. Image 1 controls "
    "the exact silhouette, outlined contours and anatomy. Image 2 shows metal-and-enamel finish and color. "
    "In particular TRACE the straw profile: one wide, low, asymmetrical connected straw sweep at the bottom, "
    "long gradually pointed lower left sweep, small upward flick on the right and just a tiny shallow indentation "
    "in the CONTINUOUS lower edge. The straw skirt stays together as one low mass, with no big arch, legs, "
    "air gap, or human feet. Preserve the little strip of water on top of each bucket and the separate bent hands "
    "closed around the arched bucket handles. Use copper-orange wood, yellow ivory straw and narrow engraved detail, "
    "warm red-orange bucket staves with muted blue hoops and cyan water. Keep every object at the registered position "
    "and overall fixed size. Only one broom. Clean solid readable colors and subtle thin antique gold outlines."
)
seed = 20261123625
key = "broom-connected-straw-profile"
g = graph(["new-profile-guide.png", "new-pin-finish-reference.png"], prompt, seed, key)
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
