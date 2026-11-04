# 脚本用法

先设置 ComfyUI 地址（默认本机 8188）：

```bash
export COMFY_URL=http://127.0.0.1:8188
```

示例配置在 `../examples/`。所有提交类脚本加 `--wait 输出目录` 会等任务完成并下载结果；不加则只打印 prompt_id，之后用 `wait_download.py` 取。

| 步骤 | 命令 |
|---|---|
| 出母版 | `python3 t2i_masters.py ../examples/masters.json --wait out/masters` |
| 改母版 | `python3 edit_image.py out/masters/long_00001_.png "只改头部：把头饰去掉。" --wait out/edits` |
| 配音 | `python3 tts_clone.py ../examples/voice.json --wait out/voice` |
| 核对配音 | `python3 asr.py out/voice/*.flac` |
| 生成视频 | `python3 h3_ref2va.py ../examples/h3_job.json --wait out/video` |
| 看进度 | `python3 ws_progress.py 60` |
| 取结果 | `python3 wait_download.py <prompt_id> out/video` |
| 说话人检查 | `python3 speaker_grid.py out/video/seg3.mp4 ../examples/lines.json out/qa` |
| 放大 | `python3 upscale_video.py in.mp4 hd.mp4 RealESRGAN_x2.pth 1080 1500` |
| 字幕和响度 | `python3 post_subtitle_loud.py hd.mp4 final.mp4 ../examples/subs.json` |
| 封面 | `python3 make_cover.py frame.png out "第一行" "第二行" "标签"` |

依赖：Python 3.9+、ffmpeg、Pillow；放大和封面放大另需 `torch` 和 `spandrel`；转写需 `faster-whisper`。

ComfyUI 端需要的模型和自定义节点见 `../references/ComfyUI节点与参数.md`。
