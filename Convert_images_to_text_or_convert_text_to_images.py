"""
steganography_ultra.py
======================

本模块在先前版本的基础上进一步提高隐写容量，力求在尽可能小的 PNG 图像
中隐藏尽可能多的文本信息。主要改进如下：

1. **自适应压缩算法**：为了减少需要嵌入的比特数，本程序尝试使用
   Python 标准库提供的三种压缩算法：`zlib`、`bz2` 和 `lzma`，计算
   出的压缩结果中选择体积最小的一个，并将压缩算法编号存储在头部字节中。
   这样当原始数据可压缩时能够显著减小嵌入长度，而对于不可压缩的输入则
   不会出现算法退化。研究表明，选择合适的压缩算法可以有效减少嵌入负载
   并且不会影响解码正确性。

2. **利用 RGBA 的第四通道**：在 8 位深度的图像中，每个像素通常包含
   3 个颜色通道 (RGB)，每通道 1 字节，合计 24 位。根据 Glasswall 的
   研究，若使用包含透明度信息的 alpha 通道，即 RGBA 图像，可以将
   每像素可用的最低有效位容量从 3 提升到 4【219713493358829†L833-L845】。
   在我们的场景中使用随机噪声作为载体，可以不受视觉约束直接利用每个
   通道的全部 8 位来存储数据，因此每个像素可容纳整整 4 字节，比传统
   三通道隐写多出 33% 的容量。这样相同数据只需更少的像素，PNG 文件
   体积随之减小。

3. **随机像素顺序和密码控制**：与前一版本类似，嵌入顺序可以由密码控
   制的伪随机数生成器 (PRNG) 确定。没有密码时使用固定种子 0；提供密
   码时根据密码生成整数种子，从而打乱嵌入顺序。这不仅增加安全性，还能
   分散数据位于整幅图像中的分布。

4. **头部信息**：为了正确解码，嵌入的消息前缀包含 1 字节压缩算法编
   号和 4 字节无符号整数表示的压缩数据长度 (大端字节序)。

使用本模块，可以通过命令行调用将文本文件嵌入 PNG 图像，也可以在代
码中调用 ``encode_file_to_png`` 和 ``decode_png_to_text`` 函数自定义
参数。
"""

from __future__ import annotations

import os
import math
import random
import struct
import zlib
import bz2
import lzma
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from PIL import Image

# 定义压缩算法集合：键为算法编号，值为 (名称, 压缩函数, 解压函数)。
_COMPRESSION_ALGOS: Dict[int, Tuple[str, Callable[[bytes], bytes], Callable[[bytes], bytes]]] = {
    0: ("none", lambda b: b, lambda b: b),
    1: ("zlib", zlib.compress, zlib.decompress),
    2: ("bz2", bz2.compress, bz2.decompress),
    3: ("lzma", lzma.compress, lzma.decompress),
}


def _compute_dimensions(num_pixels: int) -> Tuple[int, int]:
    """根据像素数量计算接近正方形的宽度和高度。"""
    side = int(math.sqrt(num_pixels))
    width = side
    height = side
    while width * height < num_pixels:
        width += 1
        if width * height < num_pixels:
            height += 1
    return width, height


def _generate_noise_image(width: int, height: int) -> Image.Image:
    """生成随机 RGBA 噪声图像，所有像素透明度默认为完全不透明 (alpha=255)。"""
    rng = random.Random(0)
    data = bytearray()
    for _ in range(width * height):
        # 随机 RGB，每个通道 0-255；alpha 固定为 255 以保证不透明
        data.append(rng.randrange(0, 256))  # R
        data.append(rng.randrange(0, 256))  # G
        data.append(rng.randrange(0, 256))  # B
        data.append(255)  # A
    return Image.frombytes('RGBA', (width, height), bytes(data))


def _choose_best_compression(data: bytes) -> Tuple[int, bytes]:
    """尝试多种压缩算法，返回最小的压缩结果及对应算法编号。"""
    best_id = 0
    best_data = data
    best_len = len(data)
    for algo_id, (name, compress_fn, _) in _COMPRESSION_ALGOS.items():
        if algo_id == 0:
            # 不压缩的情况已初始化
            continue
        try:
            comp = compress_fn(data)
        except Exception:
            # 某些算法在内存不足或数据过大时可能失败，忽略失败算法
            continue
        if len(comp) < best_len:
            best_id = algo_id
            best_data = comp
            best_len = len(comp)
    return best_id, best_data


def encode_file_to_png(
    text_path: str,
    output_path: str,
    cover_path: Optional[str] = None,
    password: Optional[str] = None,
    compress: bool = True,
) -> None:
    """将文本文件内容嵌入 PNG 图像。

    Parameters
    ----------
    text_path: 输入文本文件路径。
    output_path: 保存 stego 图像的路径。
    cover_path: 可选，作为载体的现有图像路径。若提供，将忽略其像素内容，
                仅使用其尺寸；如果尺寸不足以容纳数据，则抛出异常。
    password: 可选，密码字符串，用于控制伪随机嵌入顺序。
    compress: 是否启用压缩。默认为 True。
    """
    if not os.path.isfile(text_path):
        raise FileNotFoundError(f"未找到文本文件: {text_path}")
    with open(text_path, 'rb') as f:
        original = f.read()

    # 选择压缩算法
    if compress:
        algo_id, compressed = _choose_best_compression(original)
    else:
        algo_id, compressed = 0, original
    # 构建 payload：算法编号 (1 字节) + 长度 (4 字节) + 压缩数据
    if algo_id > 255:
        raise ValueError("算法编号必须小于 256")
    header = struct.pack('>BI', algo_id, len(compressed))
    payload = header + compressed

    # 每像素 4 字节容量
    required_pixels = math.ceil(len(payload) / 4.0)

    # 准备载体图像，如果提供封面，只检查尺寸，不保留内容
    if cover_path:
        if not os.path.isfile(cover_path):
            raise FileNotFoundError(f"未找到封面图像: {cover_path}")
        cover_img = Image.open(cover_path)
        # 将封面转换为 RGBA 以提供四通道
        if cover_img.mode not in ('RGB', 'RGBA'):
            raise ValueError(f"封面图像模式需为 RGB 或 RGBA, 当前模式: {cover_img.mode}")
        width, height = cover_img.size
        total_pixels = width * height
        if total_pixels < required_pixels:
            raise ValueError(
                f"封面图像尺寸不足: 需要 {required_pixels} 像素, 实际 {total_pixels}"
            )
        # 无论封面像素如何，生成新的 RGBA 图像来保存数据
        cover = Image.new('RGBA', (width, height), (0, 0, 0, 255))
    else:
        width, height = _compute_dimensions(required_pixels)
        cover = _generate_noise_image(width, height)

    pixels: List[Tuple[int, int, int, int]] = list(cover.getdata())
    total_pixels = len(pixels)
    indices = list(range(total_pixels))
    rng = random.Random()
    # 生成种子
    seed = 0
    if password:
        seed = sum((i + 1) * ord(ch) for i, ch in enumerate(password))
    rng.seed(seed)
    rng.shuffle(indices)

    # 将 payload 按 4 字节填入像素 RGBA
    data_iter = iter(payload)
    new_pixels = list(pixels)
    for idx in indices:
        try:
            r = next(data_iter)
        except StopIteration:
            break
        try:
            g = next(data_iter)
        except StopIteration:
            g = None
        try:
            b = next(data_iter)
        except StopIteration:
            b = None
        try:
            a = next(data_iter)
        except StopIteration:
            a = None
        orig_r, orig_g, orig_b, orig_a = new_pixels[idx]
        new_r = r
        new_g = g if g is not None else orig_g
        new_b = b if b is not None else orig_b
        new_a = a if a is not None else orig_a
        new_pixels[idx] = (new_r, new_g, new_b, new_a)

    stego = Image.new('RGBA', cover.size)
    stego.putdata(new_pixels)
    # 保存 PNG，使用较高的压缩等级减小文件尺寸
    stego.save(output_path, format='PNG', compress_level=9)


def decode_png_to_text(
    stego_path: str,
    password: Optional[str] = None,
) -> bytes:
    """从 stego PNG 图像中提取原始文本内容。

    Parameters
    ----------
    stego_path: 包含隐藏文本的 PNG 图像路径。
    password: 解码时使用的密码（若编码时提供了密码）。

    Returns
    -------
    bytes
        解码得到的原始文本字节序列。
    """
    if not os.path.isfile(stego_path):
        raise FileNotFoundError(f"未找到 stego 图像: {stego_path}")
    im = Image.open(stego_path)
    if im.mode != 'RGBA':
        # 若图像不是 RGBA 模式，则尝试转换，但仍然可能不能解码完整数据
        im = im.convert('RGBA')
    pixels = list(im.getdata())
    total_pixels = len(pixels)
    indices = list(range(total_pixels))
    rng = random.Random()
    seed = 0
    if password:
        seed = sum((i + 1) * ord(ch) for i, ch in enumerate(password))
    rng.seed(seed)
    rng.shuffle(indices)

    # 提取所有嵌入字节（按随机顺序）
    extracted_bytes: List[int] = []
    for idx in indices:
        r, g, b, a = pixels[idx]
        extracted_bytes.extend([r, g, b, a])

    if len(extracted_bytes) < 5:
        raise ValueError("stego 图像数据不足，无法解析头部信息")
    # 第一个字节是压缩算法编号
    algo_id = extracted_bytes[0]
    if algo_id not in _COMPRESSION_ALGOS:
        raise ValueError(f"未知的压缩算法编号: {algo_id}")
    # 接下来的 4 个字节表示压缩数据长度
    length_header = bytes(extracted_bytes[1:5])
    comp_len = struct.unpack('>I', length_header)[0]
    total_len = 1 + 4 + comp_len
    if total_len > len(extracted_bytes):
        raise ValueError("stego 图像中的数据长度不足，可能密码错误或文件损坏")
    data_bytes = bytes(extracted_bytes[5:total_len])
    # 根据算法编号解压
    _, _, decompress_fn = _COMPRESSION_ALGOS[algo_id]
    try:
        original = decompress_fn(data_bytes)
    except Exception as e:
        raise ValueError(f"解压失败: {e}")
    return original


if __name__ == '__main__':
    """命令行接口提供编码和解码两种模式。

    用法示例：

    - 编码，将文本文件嵌入 PNG：
        python steganography_ultra.py encode input.txt output.png [--cover cover.png] [--password pwd] [--no-compress]

    - 解码，从 stego PNG 提取文本到文件：
        python steganography_ultra.py decode stego.png recovered.txt [--password pwd]
    """
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "终极隐写：支持编码和解码，采用多种压缩算法并使用 RGBA 四通道以提高嵌入容量。"
        )
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # 编码子命令
    encode_parser = subparsers.add_parser('encode', help='将文本文件隐写到 PNG 图像')
    encode_parser.add_argument('text_path', help='要隐藏的文本文件路径')
    encode_parser.add_argument('output_path', help='输出的 PNG 图像路径')
    encode_parser.add_argument(
        '-c', '--cover', dest='cover_path', default=None,
        help='可选：封面图像路径，只用于提供尺寸'
    )
    encode_parser.add_argument(
        '-p', '--password', dest='password', default=None,
        help='可选：用于随机打散嵌入顺序的密码'
    )
    encode_parser.add_argument(
        '--no-compress', dest='compress', action='store_false',
        help='禁用压缩，直接嵌入原始数据'
    )

    # 解码子命令
    decode_parser = subparsers.add_parser('decode', help='从 PNG 图像中提取隐藏的文本')
    decode_parser.add_argument('stego_path', help='包含隐藏文本的 PNG 图像路径')
    decode_parser.add_argument('output_path', help='提取出的文本保存路径')
    decode_parser.add_argument(
        '-p', '--password', dest='password', default=None,
        help='可选：解码时使用的密码（必须与编码时一致）'
    )

    args = parser.parse_args()

    if args.command == 'encode':
        encode_file_to_png(
            text_path=args.text_path,
            output_path=args.output_path,
            cover_path=args.cover_path,
            password=args.password,
            compress=args.compress,
        )
    elif args.command == 'decode':
        # 执行解码并保存到指定文本文件
        data = decode_png_to_text(args.stego_path, password=args.password)
        with open(args.output_path, 'wb') as f:
            f.write(data)