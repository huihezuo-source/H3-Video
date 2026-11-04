"""ComfyUI 小工具：提交工作流、上传文件、等待并下载输出。其他脚本都 import 它。

环境变量：
  COMFY_URL        ComfyUI 地址，默认 http://127.0.0.1:8188
  COMFY_CLIENT_ID  提交用的 client_id，默认 h3-video。看进度时必须用同一个。
"""
import json, os, subprocess, time, urllib.parse, urllib.request

URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")
CLIENT_ID = os.environ.get("COMFY_CLIENT_ID", "h3-video")


def submit(prompt):
    """提交 API 格式的工作流，返回 prompt_id。"""
    body = json.dumps({"prompt": prompt, "client_id": CLIENT_ID}).encode()
    req = urllib.request.Request(URL + "/prompt", body, {"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req))
    if r.get("node_errors"):
        raise SystemExit(f"工作流有错：{r['node_errors']}")
    return r["prompt_id"]


def upload(path, name, kind="input"):
    """把本地图片或音频传到 ComfyUI 的 input 目录，名字为 name。"""
    subprocess.run(["curl", "-s", "-m", "120", "-F", f"image=@{path};filename={name}",
                    "-F", "overwrite=true", "-F", f"type={kind}", URL + "/upload/image"],
                   check=True, capture_output=True)
    return name


def wait(pid, timeout=3600, every=8):
    """轮询 /history 直到任务完成或报错，返回 history 记录。"""
    t = time.time()
    while time.time() - t < timeout:
        try:
            h = json.load(urllib.request.urlopen(f"{URL}/history/{pid}", timeout=15))
            if pid in h:
                st = h[pid]["status"]
                if st.get("completed") or st.get("status_str") == "error":
                    return h[pid]
        except Exception:
            pass
        time.sleep(every)
    raise TimeoutError(f"{pid} 超过 {timeout} 秒没完成")


def download(rec, out):
    """下载一条 history 记录里的全部图片、音频、视频输出，返回文件名列表。"""
    os.makedirs(out, exist_ok=True)
    for m in rec["status"].get("messages", []):
        if m[0] == "execution_error":
            print("出错节点", m[1].get("node_type"), str(m[1].get("exception_message"))[:400])
    got = []
    for o in rec.get("outputs", {}).values():
        for x in o.get("images", []) + o.get("audio", []) + o.get("video", []) + o.get("gifs", []):
            if x.get("type") != "output":
                continue
            q = urllib.parse.urlencode({"filename": x["filename"], "subfolder": x["subfolder"], "type": "output"})
            urllib.request.urlretrieve(f"{URL}/view?{q}", os.path.join(out, x["filename"]))
            got.append(x["filename"])
    return got
