# 🎬 Video2Audio - 批量视频转音频工具

一个基于 **Python 3** 和 **FFmpeg** 的高效批量视频转音频 CLI 工具。支持递归搜索、多线程并行加速、断点续传（自动跳过已转换文件）、自定义音质格式，并提供实时的转换进度与剩余时间预测（ETA）。

---

## ✨ 核心特性

- ⚡ **多线程并发加速**：支持通过 `-j` 参数指定并发线程数，充分利用多核 CPU 性能。
- ⏯️ **智能断点续传**：自动识别已转换且非空的目标文件，重复运行命令自动跳过，无需重复等待。
- 📊 **实时进度与倒计时**：输出带有完成百分比、已用时间与动态计算的**预计剩余时间（ETA）**。
- 🎵 **丰富格式支持**：支持导出 MP3, WAV, FLAC, AAC, OGG, M4A, WMA 等多种音频格式，并可自定义比特率（如 192k, 320k）。
- 📂 **全目录递归查找**：能够自动递归扫描输入文件夹下的所有子目录中的视频文件。
- 📁 **扁平化高效输出**：将不同目录搜索到的视频统一输出到指定单层文件夹，方便音频播放器集中管理。
- 🛡️ **安全中断恢复**：随时可通过 `Ctrl + C` 安全中断，已转换完成的文件完好保留。

---

## 🛠️ 前置依赖

本工具依赖系统中的 **FFmpeg** 媒体处理工具，运行前请确保已安装：

### 安装 FFmpeg
- **macOS** (使用 Homebrew):
  ```bash
  brew install ffmpeg
  ```
- **Ubuntu / Debian**:
  ```bash
  sudo apt update && sudo apt install -y ffmpeg
  ```
- **Windows**:
  使用包管理器（推荐）：
  ```cmd
  winget install ffmpeg
  ```
  *或者前往 [FFmpeg 官网](https://ffmpeg.org/download.html) 下载解压，并将 `bin` 路径添加到系统环境变量 `PATH` 中。*

---

## 🚀 快速开始

将代码保存为 `video_to_audio.py`。

### 1. 最简用法
转换指定文件夹下的所有视频为 MP3（默认输出到 `<输入目录>/audio_output/`）：

```bash
python3 video_to_audio.py /path/to/your/videos
```

### 2. 指定输出文件夹与高音质
将视频转换为 **320k 高音质 MP3** 并保存到指定目录：

```bash
python3 video_to_audio.py /path/to/videos -o /path/to/output_dir -b 320k
```

### 3. 多线程加速转换
开启 **8 线程** 并行快速转换：

```bash
python3 video_to_audio.py /path/to/videos -j 8
```

---

## 📖 命令行参数详解

```text
python3 video_to_audio.py <input_dir> [选项]
```

| 参数 | 缩写 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `input_dir` | *(无)* | **(必填)** | 包含视频文件的源文件夹路径（会自动递归搜索子文件夹） |
| `--output` | `-o` | `<输入目录>/audio_output` | 音频输出文件夹路径 |
| `--format` | `-f` | `mp3` | 输出音频格式，可选: `mp3`, `wav`, `flac`, `aac`, `ogg`, `m4a`, `wma` |
| `--bitrate` | `-b` | `192k` | 音频比特率，例如 `128k`, `192k`, `320k` |
| `--jobs` | `-j` | `2` | 并行转换线程数，建议设置为 CPU 核心数 |

---

## 💡 高级实操示例

### 批量处理多个序列文件夹（Shell 循环）
如果你有多个编号文件夹（如 `001 Number block 01` 到 `08`），希望将所有视频转换为音频并统一提取到一个文件夹中：

**macOS / Linux (zsh/bash):**
```zsh
for i in {01..08}; do
  python3 video_to_audio.py "/Volumes/SAMSUNG/Movie/001 Number block $i" \
    -o "/Users/username/Desktop/numberblocks_mp3" \
    -j 8
done
```

### 导出为 FLAC 无损音频
```bash
python3 video_to_audio.py /Volumes/Media/Concerts -f flac -o /Volumes/Media/FLAC_Audio -j 4
```

---

## 📽️ 支持的视频格式

脚本默认扫描并处理以下扩展名的视频文件：
- `.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`
- `.flv`, `.webm`, `.m4v`, `.mpg`, `.mpeg`, `.3gp`

---

## ⚠️ 注意事项与 FAQ

1. **同名文件重名覆盖/跳过问题**：
   因为本工具会把子文件夹中的所有音频平铺输出到同一个目标文件夹，**请确保输入文件夹中不存在跨目录但文件名完全相同的视频**（如 `Folder1/01.mp4` 和 `Folder2/01.mp4`），否则后转换的文件会被判定为已存在而自动跳过。
2. **Mac/Linux 路径中的空格处理**：
   如果文件夹名称中包含空格，请务必在命令行中使用双引号 `""` 将路径括起来，例如：`"/Volumes/My Disk/Folder Name"`。
3. **权限问题**：
   在 macOS 处理外接移动硬盘时，若提示权限拒绝，请在 `系统设置 -> 隐私与安全性 -> 完全磁盘访问权限` 中为终端 (Terminal) 授予访问权限。