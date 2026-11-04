"""Qwen-Image-Edit-2511 局部改图，其余保持不变。一次出 2 张。

用法：python3 edit_image.py 原图.png "只改头部：把……去掉" [--prefix edits/name] [--wait out_dir]

注意：weight_dtype 必须是 fp8_e4m3fn，选 default 在部分环境会让 ComfyUI 崩溃（access violation）。
"""
import os, sys
import comfy

KEEP = "其余全部保持完全不变：脸、五官、表情、发型、衣服、姿势、光线、雾气、背景和构图都不变。真实的电影剧照质感。"
src, instruction = sys.argv[1], sys.argv[2]
arg = lambda f, d=None: sys.argv[sys.argv.index(f) + 1] if f in sys.argv else d
stem = os.path.splitext(os.path.basename(src))[0]
name = comfy.upload(src, f"edit_{stem}.png")
p = {
    "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_edit_2511_fp8mixed.safetensors", "weight_dtype": "fp8_e4m3fn"}},
    "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image"}},
    "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
    "4": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.1}},
    "5": {"class_type": "CFGNorm", "inputs": {"model": ["4", 0], "strength": 1.0}},
    "10": {"class_type": "LoadImage", "inputs": {"image": name}},
    "11": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "image1": ["10", 0], "prompt": instruction + KEEP}},
    "12": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "image1": ["10", 0], "prompt": ""}},
    "13": {"class_type": "VAEEncode", "inputs": {"pixels": ["10", 0], "vae": ["3", 0]}},
    "14": {"class_type": "RepeatLatentBatch", "inputs": {"samples": ["13", 0], "amount": 2}},
    "15": {"class_type": "KSampler", "inputs": {"model": ["5", 0], "positive": ["11", 0], "negative": ["12", 0], "latent_image": ["14", 0],
           "seed": int(arg("--seed", 9500)), "steps": 30, "cfg": 4.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
    "16": {"class_type": "VAEDecode", "inputs": {"samples": ["15", 0], "vae": ["3", 0]}},
    "17": {"class_type": "SaveImage", "inputs": {"images": ["16", 0], "filename_prefix": arg("--prefix", f"edits/{stem}")}},
}
pid = comfy.submit(p)
print("prompt_id", pid)
if "--wait" in sys.argv:
    print(comfy.download(comfy.wait(pid), arg("--wait")))
