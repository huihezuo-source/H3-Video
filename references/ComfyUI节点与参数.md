# ComfyUI 节点与参数

测试环境：Windows + RTX 4090 24GB，ComfyUI 新版。下面的参数都实际跑通过。

## 角色母版：Qwen-Image 文生图

| 项 | 值 |
|---|---|
| UNETLoader | `qwen_image_fp8_e4m3fn.safetensors`，weight_dtype default |
| CLIPLoader | `qwen_2.5_vl_7b_fp8_scaled.safetensors`，type qwen_image |
| VAE | `qwen_image_vae.safetensors` |
| ModelSamplingAuraFlow | shift 3.1 |
| 尺寸 | 896×1232（竖版全身），batch 2 |
| KSampler | cfg 3，30 步，euler，simple |

提示词 = 风格前缀 + 角色描述。风格前缀示例（黑暗古装恐怖片）：

> 真实的电影剧照，阴冷压抑的古装恐怖片实拍画面，不是动画，不是插画，不是游戏CG。竖构图，人物全身站立，从头到脚完整在画面内，面向镜头。唯一的光源是从左上方照下的青白色冷光，人物一半在阴影里，大面积暗部，背景几乎全黑，飘着稀薄的雾气，地面是潮湿的旧石板。低饱和，青灰和暗金色调，胶片颗粒，真实的皮肤和毛发质感，衣物陈旧脏污、磨损潮湿，脸上有尘土，没有美化，没有修图。

负面词只放风格层面的：`卡通,动画,插画,游戏CG,3D渲染,塑料质感,美颜,磨皮,偶像,明亮,摄影棚,纯色背景,干净的衣服,鲜艳色彩,文字,水印,logo`。

## 改图：Qwen-Image-Edit-2511

| 项 | 值 |
|---|---|
| UNETLoader | `qwen_image_edit_2511_fp8mixed.safetensors`，**weight_dtype fp8_e4m3fn** |
| ModelSamplingAuraFlow | shift 3.1 |
| CFGNorm | strength 1.0 |
| 正向 | TextEncodeQwenImageEditPlus（image1 = 原图，prompt = 改动 + 保持句） |
| 负向 | TextEncodeQwenImageEditPlus，prompt 为空 |
| Latent | VAEEncode 原图 → RepeatLatentBatch 2 |
| KSampler | cfg 4，30 步，euler，simple，denoise 1.0 |

保持句：

> 其余全部保持完全不变：脸、五官、表情、发型、衣服、姿势、光线、雾气、背景和构图都不变。真实的电影剧照质感。

**已知故障：** 某次更新后，weight_dtype 选 default 加载这个模型时 ComfyUI 直接崩溃（Windows fatal exception: access violation）。文件哈希和官方一致，内存也够。改成 `fp8_e4m3fn` 就正常。

## 配音：VoxCPM2 克隆

节点：`LoadAudio` → `VoxCPM_VoiceCloning`（prompt_audio 和 reference_audio 都接参考音，prompt_text 填参考音的原文，trim_silence true）→ `VoxCPM_TTS`（model VoxCPM2，cfg 2.0，steps 10，normalize_text false）→ `SaveAudio`。

- 参考音 6–10 秒、干净、和目标风格一致最好。
- 每条换一个 seed；不满意只重出那一条。
- 显存紧张时 force_offload 设为 true。

## 视频：MiniMax H3 Ref2VA

| 项 | 值 |
|---|---|
| UNETLoader | `minimax_h3_ref2va_pruned_int8_convrot.safetensors` |
| CLIPLoader | `qwen3vl_32b_minimax_h3_int8_convrot.safetensors`，type minimax |
| 视频 VAE | `minimax_h3_video_vae_int8_convrot.safetensors` |
| 音频 VAE | `minimax_h3_audio_vae_fp32.safetensors` |
| 主节点 | MiniMaxH3ReferenceToVideo（ref_images / ref_audios 动态输入） |
| 首帧锚定 | MiniMaxH3AddGuide，frame_idx 0，image = 首帧 |
| 采样 | BasicGuider + res_multistep + simple 调度 + SamplerCustomAdvanced |
| 输出 | VAEDecode + VAEDecodeAudio → CreateVideo（24 fps）→ SaveVideo |

速度参考（4090）：

- 448×608，约 15 秒：约 8 分钟。
- 576×800：更清晰 20–40%，但约 14 分钟。
- 加 Pika H3 Flex LoRA（lcm + 7 个手动 sigma）576×800 下 10.8 秒约 3.5 分钟，适合出草稿。
- 576×800 不加速时显存溢出，可能要几个小时，先用低分辨率。

换人：`h3_character_swap` LoRA 强度 1.0，20 步，源视频作参考视频并锁定音频，不用遮罩。每段最多一个硬切。

## 稳定性：连续切换大模型时崩溃

ComfyUI 0.43 在 Windows 上连续跑几个任务、切换大模型（Qwen-Image、Qwen-Image-Edit、文本编码器）时，Python 进程反复崩溃。报错是 0xc0000005 内存访问冲突，崩溃位置每次都不一样，有时在给模型打补丁，有时在加载文本编码器。日志里能看到“prepared for dynamic VRAM loading”“Using RAM pressure cache”。

解决：启动参数加上下面几项，关掉新的动态显存加载和内存压力缓存，改回旧的缓存方式。加上之后连续跑多个改图任务没有再崩。

```
--disable-dynamic-vram --cache-classic --disable-pinned-memory --disable-async-offload
```

另外，换模型前调用一次 `comfy.free()`（POST /free 卸载模型），可以减少重复打补丁引发的崩溃。

排查思路：先用 Windows 事件日志确认崩的是不是只有 python。如果系统其他程序也在崩、还有蓝屏，先查硬件（Intel 处理器诊断工具、7-Zip 基准测试、Windows 内存诊断）和系统文件（sfc /verifyonly、DISM /ScanHealth），硬件稳定了再修系统文件。

## 放大

RealESRGAN_x2 用 spandrel 加载，Mac 上走 mps 逐帧推理，再用 ffmpeg lanczos 缩放到目标尺寸。
