#!/usr/bin/env python3
"""
批量将文件夹中的视频文件转换为音频文件 (默认 MP3)
带有实时百分比、已用时间与预计剩余时间显示。
默认动态调整并行数，尽量把 CPU 使用率顶到 95%+。
"""

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

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


def _run_fixed(videos, output_dir, audio_format, audio_bitrate, jobs):
    """固定并行数模式（用户指定了 -j）"""
    success = fail = skipped = 0
    interrupted = False
    total = len(videos)
    start_time = time.time()

    try:
        with ThreadPoolExecutor(max_workers=jobs) as executor:
            futures = {
                executor.submit(
                    convert_video_to_audio, v, output_dir, audio_format, audio_bitrate
                ): v
                for v in videos
            }
            for i, future in enumerate(as_completed(futures), 1):
                source = futures[future]
                _, ok, msg = future.result()
                name = Path(source).name

                elapsed = time.time() - start_time
                avg = elapsed / i
                eta = avg * (total - i)
                pct = (i / total) * 100
                time_info = f"已用: {format_time(elapsed)} | 剩余: {format_time(eta)}"

                if ok:
                    success += 1
                    if "已跳过" in msg:
                        skipped += 1
                        print(f"  [{i}/{total}] ({pct:5.1f}%) [{time_info}] ⏭️  {name} (跳过)")
                    else:
                        print(f"  [{i}/{total}] ({pct:5.1f}%) [{time_info}] ✅ {name}")
                else:
                    fail += 1
                    print(f"  [{i}/{total}] ({pct:5.1f}%) [{time_info}] ❌ {name}: {msg}")
    except KeyboardInterrupt:
        interrupted = True
        print("\n\n⚠️  用户中断 (Ctrl+C)，已完成的结果会保留，下次运行自动恢复")

    return success, fail, skipped, interrupted, time.time() - start_time


def _run_dynamic(videos, output_dir, audio_format, audio_bitrate):
    """动态并行模式：从 cpu_count 起步，逐步加进程直到 CPU ≥ 95% 或达到上限"""
    cpu_count = os.cpu_count() or 1
    hard_limit = cpu_count * 5
    initial = cpu_count
    target_cpu = 95.0
    check_interval = 2.5  # 秒

    success = fail = skipped = 0
    interrupted = False
    total = len(videos)
    start_time = time.time()
    completed = 0

    pending = list(videos)
    active = {}  # future -> video_path

    # 初始化 CPU 采样（第一次调用会返回 0）
    psutil.cpu_percent(interval=None)

    print(f"⚙️  动态模式启动：初始 {initial} 进程，上限 {hard_limit}，目标 CPU ≥ {target_cpu:.0f}%")

    try:
        with ThreadPoolExecutor(max_workers=hard_limit) as executor:
            # 提交初始批次
            for _ in range(min(initial, len(pending))):
                v = pending.pop(0)
                fut = executor.submit(
                    convert_video_to_audio, v, output_dir, audio_format, audio_bitrate
                )
                active[fut] = v

            while active:
                done, _ = wait(
                    active.keys(),
                    timeout=check_interval,
                    return_when=FIRST_COMPLETED,
                )

                # 处理已完成的任务
                for fut in done:
                    source = active.pop(fut)
                    _, ok, msg = fut.result()
                    name = Path(source).name
                    completed += 1

                    elapsed = time.time() - start_time
                    avg = elapsed / completed
                    eta = avg * (total - completed)
                    pct = (completed / total) * 100
                    time_info = f"已用: {format_time(elapsed)} | 剩余: {format_time(eta)}"

                    if ok:
                        success += 1
                        if "已跳过" in msg:
                            skipped += 1
                            print(f"  [{completed}/{total}] ({pct:5.1f}%) [{time_info}] ⏭️  {name} (跳过)")
                        else:
                            print(f"  [{completed}/{total}] ({pct:5.1f}%) [{time_info}] ✅ {name}")
                    else:
                        fail += 1
                        print(f"  [{completed}/{total}] ({pct:5.1f}%) [{time_info}] ❌ {name}: {msg}")

                # 尝试增加进程（只增不减）
                current_cpu = psutil.cpu_percent(interval=None)
                added = 0
                while pending and len(active) < hard_limit:
                    if current_cpu >= target_cpu:
                        break
                    v = pending.pop(0)
                    fut = executor.submit(
                        convert_video_to_audio, v, output_dir, audio_format, audio_bitrate
                    )
                    active[fut] = v
                    added += 1
                    # 每加一个后重新采样，避免一次加太多
                    current_cpu = psutil.cpu_percent(interval=None)

                if added > 0:
                    print(f"  📈 动态加进程 +{added} → 当前并发 {len(active)} | CPU {current_cpu:.0f}%")

    except KeyboardInterrupt:
        interrupted = True
        print("\n\n⚠️  用户中断 (Ctrl+C)，已完成的结果会保留，下次运行自动恢复")

    return success, fail, skipped, interrupted, time.time() - start_time


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
    parser.add_argument("-j", "--jobs", type=int, default=0,
                        help="并行转换数量。默认 0 = 动态模式（自动加进程直到 CPU ≥ 95%%）；"
                             "指定正整数则固定该并发数")

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

    use_dynamic = args.jobs <= 0

    if use_dynamic:
        if not HAS_PSUTIL:
            print("⚠️  未安装 psutil，无法使用动态模式，回退到静态核心数模式")
            print("   安装方法: pip install psutil")
            jobs = os.cpu_count() or 1
            print(f"⚙️  并行数:  {jobs} (静态)")
            print("-" * 65)
            success, fail, skipped, interrupted, total_elapsed = _run_fixed(
                videos, output_dir, args.format, args.bitrate, jobs
            )
        else:
            print("-" * 65)
            success, fail, skipped, interrupted, total_elapsed = _run_dynamic(
                videos, output_dir, args.format, args.bitrate
            )
    else:
        print(f"⚙️  并行数:  {args.jobs} (用户指定，固定)")
        print("-" * 65)
        success, fail, skipped, interrupted, total_elapsed = _run_fixed(
            videos, output_dir, args.format, args.bitrate, args.jobs
        )

    print("-" * 65)
    new = success - skipped
    status_str = "已中断!" if interrupted else "完成!"
    print(f"🏁 {status_str} 新转换: {new}, 跳过: {skipped}, 失败: {fail}, 总计: {total_videos}")
    print(f"⏱️  总共耗时: {format_time(total_elapsed)}")


if __name__ == "__main__":
    main()
