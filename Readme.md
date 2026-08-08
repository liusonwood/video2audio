# 🎬 Video2Audio - 批量视频转音频工具

一个基于 **Python 3** 和 **FFmpeg** 的高效批量视频转音频 CLI 工具。支持递归搜索、多线程并行加速、断点续传（自动跳过已转换文件）、自定义音质格式，并提供实时的转换进度与剩余时间预测（ETA）。

**默认开启动态并行**：从 CPU 核心数起步，运行中自动增加进程，尽量把系统 CPU 使用率顶到 95% 以上。

---

## ✨ 核心特性

- ⚡ **动态并行加速**：默认从 CPU 核心数开始，每隔约 2.5 秒检测 CPU 使用率，若低于 95% 就继续加进程（只增不减），上限为核心数 × 5，尽量把处理器跑满。
- ⏯️ **智能断点续传**：自动识别已转换且非空的目标文件，重复运行命令自动跳过，无需重复等待。
- 📊 **实时进度与倒计时**：输出带有完成百分比、已用时间与动态计算的**预计剩余时间（ETA）**。
- 🎵 **丰富格式支持**：支持导出 MP3, WAV, FLAC, AAC, OGG, M4A, WMA 等多种音频格式，并可自定义比特率（如 192k, 320k）。
- 📂 **全目录递归查找**：能够自动递归扫描输入文件夹下的所有子目录中的视频文件。
- 📁 **扁平化高效输出**：将不同目录搜索到的视频统一输出到指定单层文件夹，方便音频播放器集中管理。
- 🛡️ **安全中断恢复**：随时可通过 `Ctrl + C` 安全中断，已转换完成的文件完好保留。

---

## 🛠️ 前置依赖

### 1. FFmpeg（必须）

本工具依赖系统中的 **FFmpeg** 媒体处理工具，运行前请确保已安装：

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

### 2. psutil（推荐，动态模式需要）

动态并行模式需要 `psutil` 来读取实时 CPU 使用率：

```bash
pip install psutil
```

如果未安装，会自动回退到「按核心数」的静态模式，并提示你安装。

---

## 🚀 快速开始

### 1. 最简用法（推荐，动态模式）

转换指定文件夹下的所有视频为 MP3（默认输出到 `<输入目录>/audio_output/`）：

```bash
python3 video_to_audio.py /path/to/your/videos
```

脚本会：
1. 先开 `CPU 核心数` 个进程
2. 运行中持续监测 CPU，若使用率 < 95% 就继续加进程
3. 最多加到 `核心数 × 5`

### 2. 指定输出文件夹与高音质

```bash
python3 video_to_audio.py /path/to/videos -o /path/to/output_dir -b 320k
```

### 3. 手动固定并行数（关闭动态）

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
| `input_dir` | *(位置)* | **(必填)** | 包含视频文件的源文件夹路径（会自动递归搜索子文件夹） |
| `--output` | `-o` | `<输入目录>/audio_output` | 音频输出文件夹路径 |
| `--format` | `-f` | `mp3` | 输出音频格式，可选: `mp3`, `wav`, `flac`, `aac`, `ogg`, `m4a`, `wma` |
| `--bitrate` | `-b` | `192k` | 音频比特率，例如 `128k`, `192k`, `320k` |
| `--jobs` | `-j` | `0`（动态） | `0` 或负数 = **动态模式**（自动加进程直到 CPU ≥ 95%）；正整数 = 固定该并发数 |

---

## 💡 高级实操示例

### 批量处理多个序列文件夹（Shell 循环）

```zsh
for i in {01..08}; do
  python3 video_to_audio.py "/Volumes/SAMSUNG/Movie/001 Number block $i" \
    -o "/Users/username/Desktop/numberblocks_mp3"
done
```

### 导出为 FLAC 无损音频

```bash
python3 video_to_audio.py /Volumes/Media/Concerts -f flac -o /Volumes/Media/FLAC_Audio
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
4. **动态模式依赖**：
   需要 `psutil`。未安装时会回退到静态核心数模式。安装：`pip install psutil`。
