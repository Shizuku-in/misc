from pathlib import Path
import subprocess
import tempfile

import cv2
import numpy as np
import soundfile as sf

# 输入文件
IMAGE_PATH = Path("mark.jpg")
AUDIO_PATH = Path("孤独の海.mp3")

# 输出文件
MASK_IMAGE_PATH = Path("watermark_mask.png")
WATERMARK_AUDIO_PATH = Path("mark.mp3")
OUTPUT_AUDIO_PATH = Path("孤独の海_marked.mp3")

# 音频参数
SAMPLE_RATE = 48_000
CHANNELS = 2
MP3_BITRATE = "320k"

# 水印位置
START_SECONDS = 145.0

# 频率位置配置
# FREQUENCY_MODE = "range"  : 使用 FREQ_MIN / FREQ_MAX 直接指定频率范围
# FREQUENCY_MODE = "center" : 使用 FREQ_CENTER / FREQ_BANDWIDTH 指定中心频率和带宽
#
# 示例：
#   range  模式：8000 Hz 到 16000 Hz
#   center 模式：中心 12000 Hz，带宽 8000 Hz，也等价于 8000 Hz 到 16000 Hz
FREQUENCY_MODE = "center"
FREQ_MIN = 8_000
FREQ_MAX = 16_000
FREQ_CENTER = 12_000
FREQ_BANDWIDTH = 8_000

# 声谱图参数
# n_fft 越大，频率方向越细；hop_length 越小，水印在时间上越短、越密。
N_FFT = 4096
HOP_LENGTH = 256

# 水印强度
# MARK_PEAK 控制单独生成的 mark.mp3 音量。
# MIX_GAIN 控制混入原曲时的强度，太大更清楚但更容易听见。
MARK_PEAK = 0.34
MIX_GAIN = 0.18

# 叠加模式
# "add"          : 直接叠加，最简单
# "fade_add"     : 叠加时给水印加淡入淡出，减少突兀感
# "adaptive_add" : 根据原曲当前片段响度自动调整水印强度
# "replace"      : 用水印替换原曲对应片段，适合调试声谱图，不适合听感
# "none"         : 不嵌入原曲，只导出 mark.mp3
OVERLAY_MODE = "fade_add"
OVERLAY_FADE_SECONDS = 0.25
ADAPTIVE_TARGET_RATIO = 0.35

# 图片转线稿参数
IMAGE_PREVIEW_HEIGHT = 1200
MIN_LINE_AREA = 10
MASK_GAMMA = 1.20


def get_frequency_range():
    nyquist = SAMPLE_RATE / 2

    if FREQUENCY_MODE == "range":
        freq_min = FREQ_MIN
        freq_max = FREQ_MAX
    elif FREQUENCY_MODE == "center":
        freq_min = FREQ_CENTER - FREQ_BANDWIDTH / 2
        freq_max = FREQ_CENTER + FREQ_BANDWIDTH / 2
    else:
        raise ValueError('FREQUENCY_MODE must be "range" or "center".')

    if freq_min < 0:
        raise ValueError("Frequency minimum cannot be below 0 Hz.")
    if freq_max > nyquist:
        raise ValueError(f"Frequency maximum cannot exceed Nyquist frequency: {nyquist:.0f} Hz.")
    if freq_max <= freq_min:
        raise ValueError("Frequency maximum must be greater than frequency minimum.")

    return float(freq_min), float(freq_max)

def run_ffmpeg(args):
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args],
        check=True,
    )


def decode_audio_to_wav(audio_path):
    tmp = tempfile.TemporaryDirectory()
    wav_path = Path(tmp.name) / "decoded.wav"
    run_ffmpeg([
        "-i", str(audio_path),
        "-ar", str(SAMPLE_RATE),
        "-ac", str(CHANNELS),
        str(wav_path),
    ])
    audio, sr = sf.read(wav_path, dtype="float32", always_2d=True)
    tmp.cleanup()
    if sr != SAMPLE_RATE:
        raise RuntimeError(f"Unexpected sample rate: {sr}")
    return audio


def write_mp3(audio, output_path):
    if output_path.exists():
        try:
            output_path.unlink()
        except PermissionError:
            stem = output_path.stem
            suffix = output_path.suffix
            for index in range(1, 100):
                fallback = output_path.with_name(f"{stem}_{index}{suffix}")
                if not fallback.exists():
                    output_path = fallback
                    break
            else:
                raise PermissionError(f"Cannot find available output name near {output_path}")

    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / "temp.wav"
        sf.write(wav_path, audio, SAMPLE_RATE)
        run_ffmpeg([
            "-i", str(wav_path),
            "-codec:a", "libmp3lame",
            "-b:a", MP3_BITRATE,
            str(output_path),
        ])
    return output_path


def resize_to_height(image, target_height):
    height, width = image.shape[:2]
    target_width = round(width * target_height / height)
    return cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_AREA)


def remove_small_components(binary, min_area):
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
    cleaned = np.zeros_like(binary)
    for index in range(1, count):
        if stats[index, cv2.CC_STAT_AREA] >= min_area:
            cleaned[labels == index] = 255
    return cleaned

def image_to_mask(image_path, target_height, target_width):
    bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(image_path)

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgb = resize_to_height(rgb, IMAGE_PREVIEW_HEIGHT)

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)

    smooth = cv2.bilateralFilter(gray, 7, 48, 48)
    median = float(np.median(smooth))

    edge_gray = cv2.Canny(
        smooth,
        int(max(18, 0.55 * median)),
        int(min(150, 1.25 * median)),
        L2gradient=True,
    )
    edge_sat = cv2.Canny(cv2.GaussianBlur(hsv[:, :, 1], (3, 3), 0), 28, 92, L2gradient=True)
    edge_a = cv2.Canny(cv2.GaussianBlur(lab[:, :, 1], (3, 3), 0), 18, 62, L2gradient=True)
    edge_b = cv2.Canny(cv2.GaussianBlur(lab[:, :, 2], (3, 3), 0), 18, 62, L2gradient=True)

    laplacian = cv2.Laplacian(cv2.GaussianBlur(smooth, (3, 3), 0), cv2.CV_16S, ksize=3)
    laplacian = cv2.convertScaleAbs(laplacian)
    _, edge_laplacian = cv2.threshold(laplacian, 24, 255, cv2.THRESH_BINARY)

    adaptive = cv2.adaptiveThreshold(
        smooth,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        23,
        6,
    )
    gradient = cv2.morphologyEx(smooth, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
    _, gradient_mask = cv2.threshold(gradient, 12, 255, cv2.THRESH_BINARY)
    adaptive_lines = cv2.bitwise_and(adaptive, gradient_mask)

    mask = edge_gray
    for layer in [edge_sat, edge_a, edge_b, edge_laplacian, adaptive_lines]:
        mask = cv2.bitwise_or(mask, layer)

    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8), iterations=1)
    mask = remove_small_components(mask, MIN_LINE_AREA)
    mask = cv2.GaussianBlur(mask, (3, 3), 0)
    mask = cv2.normalize(mask, None, 0, 1, cv2.NORM_MINMAX).astype(np.float32)
    mask = np.power(mask, MASK_GAMMA)

    mask = cv2.resize(mask, (target_width, target_height), interpolation=cv2.INTER_AREA)
    mask = cv2.normalize(mask, None, 0, 1, cv2.NORM_MINMAX).astype(np.float32)

    mask = np.flipud(mask) # 上下翻转

    # 左右淡入淡出
    fade_len = max(1, target_width // 12)
    fade = np.ones(target_width, dtype=np.float32)
    fade[:fade_len] = np.linspace(0, 1, fade_len)
    fade[-fade_len:] = np.linspace(1, 0, fade_len)
    return mask * fade[None, :]

def mask_to_watermark_audio(mask, freq_start, freq_end):
    bins = N_FFT // 2 + 1
    frames = mask.shape[1]
    output_len = (frames - 1) * HOP_LENGTH + N_FFT

    output = np.zeros(output_len, dtype=np.float64)
    window_sum = np.zeros(output_len, dtype=np.float64)
    window = np.hanning(N_FFT)
    rng = np.random.default_rng(20260531)

    for frame in range(frames):
        spectrum = np.zeros(bins, dtype=np.complex128)
        magnitude = mask[:, frame] ** 1.25
        phase = rng.uniform(0, 2 * np.pi, size=freq_end - freq_start)
        spectrum[freq_start:freq_end] = magnitude * np.exp(1j * phase)

        chunk = np.fft.irfft(spectrum, n=N_FFT) * window
        start = frame * HOP_LENGTH
        end = start + N_FFT
        output[start:end] += chunk
        window_sum[start:end] += window ** 2

    valid = window_sum > 1e-8
    output[valid] /= window_sum[valid]
    output -= np.mean(output)

    peak = np.max(np.abs(output))
    if peak > 0:
        output = output / peak * MARK_PEAK

    return output.astype(np.float32)

def rms(audio):
    return float(np.sqrt(np.mean(np.square(audio)) + 1e-12))


def make_fade_envelope(length):
    envelope = np.ones(length, dtype=np.float32)
    fade_len = min(length // 2, int(OVERLAY_FADE_SECONDS * SAMPLE_RATE))
    if fade_len > 0:
        envelope[:fade_len] = np.linspace(0, 1, fade_len)
        envelope[-fade_len:] = np.linspace(1, 0, fade_len)
    return envelope[:, None]


def prepare_overlay(original_segment, watermark_segment):
    mode = OVERLAY_MODE.lower()
    overlay = watermark_segment.copy()

    if mode in {"fade_add", "adaptive_add", "replace"}:
        overlay *= make_fade_envelope(len(overlay))

    if mode == "adaptive_add":
        original_rms = rms(original_segment)
        watermark_rms = rms(overlay)
        if watermark_rms > 0:
            adaptive_gain = original_rms * ADAPTIVE_TARGET_RATIO / watermark_rms
            overlay *= adaptive_gain
        return overlay

    return overlay * MIX_GAIN


def embed_watermark(original_audio, watermark_mono):
    watermark = np.column_stack([watermark_mono] * CHANNELS)
    start = int(START_SECONDS * SAMPLE_RATE)
    end = min(start + len(watermark), len(original_audio))
    length = end - start

    marked = original_audio.copy()
    original_segment = original_audio[start:end]
    watermark_segment = watermark[:length]
    overlay = prepare_overlay(original_segment, watermark_segment)

    mode = OVERLAY_MODE.lower()
    if mode in {"add", "fade_add", "adaptive_add"}:
        marked[start:end] = original_segment + overlay
    elif mode == "replace":
        marked[start:end] = overlay
    elif mode == "none":
        return marked, watermark
    else:
        raise ValueError(
            'OVERLAY_MODE must be "add", "fade_add", "adaptive_add", "replace", or "none".'
        )

    peak = np.max(np.abs(marked))
    if peak > 0.98:
        marked = marked / peak * 0.98

    return marked, watermark


def main():
    if not AUDIO_PATH.exists():
        raise FileNotFoundError(AUDIO_PATH)
    if not IMAGE_PATH.exists():
        raise FileNotFoundError(IMAGE_PATH)

    freq_min, freq_max = get_frequency_range()
    freqs = np.fft.rfftfreq(N_FFT, d=1 / SAMPLE_RATE)
    freq_start = int(np.searchsorted(freqs, freq_min))
    freq_end = int(np.searchsorted(freqs, freq_max))
    target_height = freq_end - freq_start

    bgr = cv2.imread(str(IMAGE_PATH), cv2.IMREAD_COLOR)
    image_height, image_width = bgr.shape[:2]
    image_ratio = image_width / image_height
    target_width = round(target_height * image_ratio)

    mask = image_to_mask(IMAGE_PATH, target_height, target_width)
    cv2.imwrite(str(MASK_IMAGE_PATH), (np.flipud(mask) * 255).astype(np.uint8))

    watermark_mono = mask_to_watermark_audio(mask, freq_start, freq_end)
    original_audio = decode_audio_to_wav(AUDIO_PATH)
    marked_audio, watermark_stereo = embed_watermark(original_audio, watermark_mono)

    watermark_output = write_mp3(watermark_stereo, WATERMARK_AUDIO_PATH)
    marked_output = write_mp3(marked_audio, OUTPUT_AUDIO_PATH)

    duration = len(watermark_mono) / SAMPLE_RATE
    print("Done")
    print(f"Mask image: {MASK_IMAGE_PATH.resolve()}")
    print(f"Watermark audio: {watermark_output.resolve()}")
    print(f"Marked audio: {marked_output.resolve()}")
    print(f"Watermark duration: {duration:.2f}s")
    print(f"Frequency range: {freq_min:.0f} Hz - {freq_max:.0f} Hz")
    print(f"Overlay mode: {OVERLAY_MODE}")
    print(f"Mask size: {target_width} frames x {target_height} frequency bins")


if __name__ == "__main__":
    main()
