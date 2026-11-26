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
    "Edit image 1, the FULL square enamel-pin art. Make a targeted, professional revision of Mickey's TWO WHITE GLOVES "
    "only. Image 2 is the original animation pose and anatomy guide, not a texture source. Draw the two gloves in image 1's "
    "existing clean high-resolution enamel illustration style: very smooth continuous precise curves, smooth thin consistent "
    "brown inner contours and gold keyline, solid warm ivory, consistent with the existing facial contours, nose, hat edge and "
    "robe. Preserve the exact image 1 composition, angle, body, shoes, head, hat, sleeve shapes, rim, stars, navy field, and "
    "the wrist positions. The raised right glove is a PALM-UP offering gesture: open cupped palm as in image 2, aligned "
    "fingers extended gently right, rounded lifted thumb at left, one short curved natural thumb-base palm crease, short finger "
    "separations near their tips. There are no three cartoon back-of-hand marks on the raised palm. White cuff smoothly encloses "
    "the top of the existing black forearm with absolutely no blue gap. Lowered left glove at the waist is the back of a relaxed "
    "curled fist, round short scalloped curled fingertips and thumb at right, three short smooth back-of-hand markings as in image 2. "
    "Keep its white cuff attached to the sleeve. Preserve the exact placement and size of both hands and the artwork outside "
    "the glove-and-cuff areas. Crisp clean continuous linework, distinct contours, smooth even ink, no blur, shading, photo texture "
    "or jagged lines. Render the full original square frame with the local edits."
)
seed = 20261123717
key = "mickey-full-art-targeted-hands"
g = graph(["full-enamel-art-input.png", "animation-pose-reference.png"], prompt, seed, key)
del g["4"]
for i, mp in ((1, 1.05), (2, .38)):
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
