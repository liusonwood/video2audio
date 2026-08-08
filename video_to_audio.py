#!/usr/bin/env python3
"""
批量将文件夹中的视频文件转换为音频文件 (默认 MP3)
带有实时百分比、已用时间与预计剩余时间显示。
"""

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 支持的视频格式
VIDEO_EXTENSIONS = {
    ".mp4", ".avi", ".mkv", ".mov", ".wmv",
    ".flv", ".webm", ".m4v", ".mpg", ".mpeg", ".3gp",
}


def _codec_for(fmt: str) -> str:
    """根据输出格式返回对应的 ffmpeg 编码器"""
    mapping = {
        "mp3": "libmp3lame",
        "wav": "pcm_s16le",
        "flac": "flac",
        "aac": "aac",
        "ogg": "libvorbis",
        "m4a": "aac",
        "wma": "wmav2",
    }
    return mapping.get(fmt, "libmp3lame")


def format_time(seconds: float) -> str:
    """格式化秒数为 HH:MM:SS 或 MM:SS"""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def convert_video_to_audio(video_path: str, output_dir: str, audio_format: str = "mp3",
                           audio_bitrate: str = "192k") -> tuple[str, bool, str]:
    """将单个视频文件转换为音频文件"""
    video = Path(video_path)
    output_path = Path(output_dir) / f"{video.stem}.{audio_format}"

    # 断点恢复：检查输出文件是否已存在且非空
    if output_path.exists() and output_path.stat().st_size > 0:
        return str(output_path), True, "已跳过（文件已存在）"

    cmd = [
        "ffmpeg",
        "-i", str(video),
        "-vn",                          # 丢弃视频流
        "-acodec", _codec_for(audio_format),
        "-b:a", audio_bitrate,
        "-y",                          # 覆盖已有文件
        str(output_path),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=3600,
        )
        if result.returncode == 0:
            return str(output_path), True, "转换成功"
        else:
            err = result.stderr.strip().splitlines()[-1] if result.stderr else "未知错误"
            return str(output_path), False, err
    except FileNotFoundError:
        return str(output_path), False, "未找到 ffmpeg，请先安装"
    except subprocess.TimeoutExpired:
        return str(output_path), False, "转换超时"
    except Exception as e:
        return str(output_path), False, str(e)


def find_videos(folder: str) -> list[str]:
    """递归查找文件夹中所有视频文件"""
    videos = []
    for root, _, files in os.walk(folder):
        for f in sorted(files):
            if Path(f).suffix.lower() in VIDEO_EXTENSIONS:
                videos.append(os.path.join(root, f))
    return videos


def main():
    parser = argparse.ArgumentParser(
        description="将文件夹中的视频文件批量转换为音频文件"
    )
    parser.add_argument("input_dir",
                        help="输入文件夹路径")
    parser.add_argument("-o", "--output", default=None,
                        help="输出文件夹 (默认: <input_dir>/audio_output/)")
    parser.add_argument("-f", "--format", default="mp3",
                        choices=["mp3", "wav", "flac", "aac", "ogg", "m4a", "wma"],
                        help="输出音频格式 (默认: mp3)")
    parser.add_argument("-b", "--bitrate", default="192k",
                        help="音频比特率 (默认: 192k)")
    parser.add_argument("-j", "--jobs", type=int, default=2,
                        help="并行转换数量 (默认: 2)")

    args = parser.parse_args()

    # 校验输入目录
    input_dir = os.path.abspath(args.input_dir)
    if not os.path.isdir(input_dir):
        print(f"❌ 输入路径不是有效文件夹: {input_dir}")
        sys.exit(1)

    # 准备输出目录
    output_dir = args.output or os.path.join(input_dir, "audio_output")
    os.makedirs(output_dir, exist_ok=True)

    # 查找视频文件
    videos = find_videos(input_dir)
    if not videos:
        print(f"📂 在 {input_dir} 中未找到视频文件")
        sys.exit(0)

    total_videos = len(videos)
    print(f"🎬 找到 {total_videos} 个视频文件")
    print(f"🎵 输出格式: {args.format} @ {args.bitrate}")
    print(f"📁 输出目录: {output_dir}")
    print(f"⚙️  并行数:  {args.jobs}")
    print("-" * 65)

    # 并行转换
    success, fail, skipped = 0, 0, 0
    interrupted = False
    start_time = time.time()

    try:
        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            futures = {
                executor.submit(
                    convert_video_to_audio, v, output_dir, args.format, args.bitrate
                ): v
                for v in videos
            }
            for i, future in enumerate(as_completed(futures), 1):
                source = futures[future]
                out_path, ok, msg = future.result()
                name = Path(source).name

                # 计算百分比与剩余时间 (ETA)
                elapsed = time.time() - start_time
                avg_time_per_item = elapsed / i
                eta = avg_time_per_item * (total_videos - i)
                pct = (i / total_videos) * 100

                time_info = f"已用: {format_time(elapsed)} | 剩余: {format_time(eta)}"

                if ok:
                    success += 1
                    if "已跳过" in msg:
                        skipped += 1
                        print(f"  [{i}/{total_videos}] ({pct:5.1f}%) [{time_info}] ⏭️  {name} (跳过)")
                    else:
                        print(f"  [{i}/{total_videos}] ({pct:5.1f}%) [{time_info}] ✅ {name}")
                else:
                    fail += 1
                    print(f"  [{i}/{total_videos}] ({pct:5.1f}%) [{time_info}] ❌ {name}: {msg}")
    except KeyboardInterrupt:
        interrupted = False
        print("\n\n⚠️  用户中断 (Ctrl+C)，已完成的结果会保留，下次运行自动恢复")

    total_elapsed = time.time() - start_time
    print("-" * 65)
    new = success - skipped
    status_str = "已中断!" if interrupted else "完成!"
    print(f"🏁 {status_str} 新转换: {new}, 跳过: {skipped}, 失败: {fail}, 总计: {total_videos}")
    print(f"⏱️  总共耗时: {format_time(total_elapsed)}")


if __name__ == "__main__":
    main()