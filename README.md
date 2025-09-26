steganography_ultra 高容量隐写工具
项目简介
steganography_ultra.py是一个用于将文本内容隐藏在 PNG 图像中的隐写工具。在传统 LSB（LeastSignificantBit，最低有效位）算法的基础上，它结合了自适应压缩、随机像素顺序和利用 RGBA 四通道提升容量等多种技术，使得在保持隐写效果的同时显著提高每个像素可以承载的字节数。
图像隐写技术通过改变数字图像中像素的某些位值来隐藏信息。根据 GeeksforGeeks 的介绍，隐写术的核心思想是隐藏数据存在的事实[1]。在图像领域，最常用的是 LSB 隐写法，即改变像素值最低位的 1bit，因为它对颜色影响极小[1]。传统 RGB 图像每像素只有 3 个字节，通过修改每个字节的 LSB，只能每像素隐藏3bit 信息，而本项目通过使用包含透明度信息的 RGBA 图像，使得像素拥有 4个字节，从而将可隐藏的 LSB 数量从3bit扩展至4bit。这意味着同样长度的信息所需的像素数量减少了三分之一[2]。
项目的主要特色包括：
自适应压缩：在嵌入前尝试 zlib、bz2、lzma 等多种压缩算法，选择压缩后体积最小的一种，并在头部存储算法编号。这一设计借鉴了动态选择压缩技术以减少嵌入长度的思路[3]。
利用 RGBA 四通道：采用四通道图像，使每个像素可存储 4字节信息，相比传统 24位 RGB 图像多出一整字节容量[2]。根据色彩像素格式的文档，RGBa8 图像每个像素需要4个字节，而 RGB8 只有3字节[4]。
随机嵌入顺序和密码控制：通过伪随机数生成器（PRNG）对像素顺序进行打乱，可提供轻量级防分析能力。用户可以指定密码作为种子，不提供密码时使用默认种子 0。
可选择封面图像或随机噪声载体：既支持在现有 PNG 图像中嵌入，也可以自动生成随机噪声作为载体，从而避免真实图像受到修改痕迹。
命令行接口与 API：提供易用的 CLI 命令，支持编码和解码；同时暴露 encode_file_to_png 与 decode_png_to_text 函数供其他 Python 项目调用。
本工具不仅适用于教学、研究和合法的隐藏通信，也可以作为了解隐写技术基本原理的示范。请遵守各国法律法规，切勿将其用于任何违法目的。

背景知识与理论概述
隐写术与 LSB 隐写
隐写术（Steganography）是一种通过在载体中隐藏秘密信息而不引起怀疑的技术。与加密不同，隐写术的重点在于隐蔽性，而不是信息内容的加密。根据介绍，隐写术在图像、音频、视频等多种媒介中均可实现，其主要目标是在不引起人眼注意的情况下隐藏数据[1]。
最常用的图像隐写方法是 LSB 隐写。该方法利用像素中最低有效位对颜色影响极小的特点，将每个字节的最低一位替换为秘密数据。GeeksforGeeks 指出，当修改像素的最后一位时，颜色变化几乎不可见[1]。例如，在 8位灰度图像中，0 表示纯黑，改变最低位后数值变为1，但对肉眼而言几乎没有变化。
RGBA 字节结构示意图

如上图所示，RGBA 图像每个像素包含 4 个字节，分别对应 R、G、B 和 A（Alpha）通道。每个字节包含 8个二进制位，最低有效位（LSB）通常位于右端。本工具直接利用每个字节的全部 8位存储数据，因为载体可以是随机噪声，不必保持颜色视觉一致性。因此相比传统 LSB 方法在每像素仅可存储几位信息，本工具可以在每像素嵌入完整的 4字节文本。
RGBA 通道带来的容量提升
传统 24位 RGB 图像每个像素包含红、绿、蓝三个通道，各占 1字节（共 3字节），使用 LSB 隐写时只能利用 3个位。RGBA 图像则增加了 Alpha 透明度通道，当值为 255 时像素完全不透明。Glasswall 的研究指出，添加 Alpha 通道将像素中可操作的最低有效位数从3扩展为4[2]。以 42×42 像素的图像为例，RGB 图像仅能提供 611字节隐藏容量，而 RGBA 图像可提升至 882字节[5]。
硬件文档也证明，RGBa8 图像中每个像素需要 4字节，而 RGB8 图像仅需 3字节[4]。因此使用 RGBA 不仅让单个像素的可用字节数增加了约 33%，在本项目的随机噪声载体中甚至可以利用 4字节的完整字节位存储信息，从而大幅降低所需像素数量。
自适应压缩算法的重要性
隐藏文本时，消息长度直接决定了嵌入载体所需的像素数量。为了提高效率，本工具在嵌入前会尝试多种无损压缩算法 (zlib、bz2、lzma) 并选择最小的压缩结果。这种 动态选择压缩算法 的思想在相关研究中被证明能显著减少隐写所需的空间[3]。不同的算法在速度、压缩比、内存占用等方面各有优劣：
zlib/Deflate：压缩速度最快、内存占用低，但压缩率相对较低[6]。
bzip2：比 zlib 能产生约 15% 更小的文件，但压缩和解压速度较慢[6]。
LZMA：压缩率最高，接近 bzip2 甚至更优，但压缩速度慢、内存消耗大，解压速度则介于 gzip 和 bzip2 之间[6]。
本工具会在不压缩的情况下初始化，然后尝试所有压缩算法并比较结果，自动选择最优方案，既兼顾压缩比，又保证解码可行。选中的算法编号会被嵌入到图像头部，解码时据此解压还原原始文本。
隐写安全性与密码控制
隐写的安全性既依赖于算法的隐蔽性，也依赖于随机性和密钥控制。本工具通过以下方式提升抵抗分析的能力：
随机像素顺序：在嵌入数据时并非按从左到右、从上到下的顺序填充，而是使用伪随机数生成器 (PRNG) 随机打乱像素索引，使数据分布更均匀，不易被局部分析。
密码种子：用户可以提供任意长度的密码，该密码经简单哈希（对每个字符取 ASCII 值乘以其位置索引求和）得到整数作为随机种子。解码时必须提供相同的密码才能正确恢复索引顺序。若不提供密码，则使用默认种子 0。
随机噪声载体：当未指定封面图像时，程序会生成随机 RGBA 噪声。由于噪声本身没有视觉结构，对任何像素的修改都不会产生可见差异，这降低了被肉眼或简单直方图分析识别的概率。
需要注意的是，本工具并未对嵌入数据进行加密，任何人若获知使用的算法及密码即可解码。为了加强保密性，建议配合加密算法 (如 AES) 对文本进行预加密后再嵌入。此外，LSB 隐写仍然可能被高级统计分析（如 χ² 检测、Steganalysis）识别，因此在高安全需求场景下应谨慎使用。

功能特性
以下为 steganography_ultra 提供的主要功能：
1. 自适应压缩策略
在编码过程中，可选择是否启用压缩（默认启用）。当启用时程序会依次尝试三个算法：
算法编号
算法名称
优点
缺点

0
none (不压缩)
无计算开销，适用于不可压缩数据
数据较长，隐写载体需求增加

1
zlib (Deflate)
压缩速度快，内存占用低；被广泛支持
压缩率较低[6]

2
bz2 (Bzip2)
压缩比约比 zlib 提高 15%[6]
压缩解压速度较慢，占用更多内存

3
lzma (LZMA)
压缩率最高，生成最小的文件[6]
压缩慢，内存要求高，解压速度介于 zlib 和 bzip2 之间

程序会捕获压缩异常（如内存不足）并跳过失败的算法，最终选择压缩后字节数最少的结果。压缩算法编号通过 1字节存入头部，后续 4字节表示压缩数据长度（大端字节序）。如果关闭压缩，则直接嵌入原始数据，算法编号设为0。
2. RGBA 四通道嵌入
每个像素包含四个通道 (R、G、B、A)，程序完全控制所有 4字节以存储数据，每像素容量达4字节。这种方法利用了 Alpha 通道增加的空间，并突破了传统 LSB 限制[2]。在随机噪声载体的情况下，由于不存在视觉约束，可以直接替换每个通道 8位而不是仅修改最低位，从而大幅提升隐藏容量。
在使用现有封面图像时，程序会忽略其原始像素内容，仅使用其尺寸来确定随机噪声图像的大小。封面图像必须为 RGB 或 RGBA 模式，否则会抛出异常。若封面大小不足以容纳数据则提示用户扩容或关闭压缩。
3. 随机顺序与密码控制
程序通过伪随机数生成器生成 0 到 total_pixels - 1 的索引数组，然后根据密码产生的整数作为种子进行随机打乱。若无密码，则使用固定种子 0。这一顺序决定了嵌入数据的像素顺序。解码时必须使用相同的密码，否则提取出的顺序将不一致，导致解码失败。
4. 命令行界面 (CLI)
脚本内置命令行接口，支持 encode 和 decode 两个子命令：
python steganography_ultra.py encode input.txt output.png [--cover cover.png] [--password pwd] [--no-compress]

# 说明：
#  input.txt    - 要隐藏的文本文件路径
#  output.png   - 输出 PNG 图像路径
#  --cover      - （可选）作为载体的现有图像路径，仅提供尺寸
#  --password   - （可选）随机种子的密码
#  --no-compress - （可选）关闭压缩，直接嵌入原始数据

python steganography_ultra.py decode stego.png recovered.txt [--password pwd]
# stego.png     - 包含隐藏文本的 PNG 图像路径
# recovered.txt - 解码后保存文本的路径
# --password    - （可选）解码时使用的密码（需与编码时一致）
5. Python API
除命令行外，可以在其他 Python 程序中直接调用以下函数：
from steganography_ultra import encode_file_to_png, decode_png_to_text

# 将文本嵌入 PNG
encode_file_to_png(
    text_path='secret.txt',
    output_path='stego.png',
    cover_path=None,    # 可指定封面图像
    password='mypwd',   # 可指定密码
    compress=True       # 启用或禁用压缩
)

# 从 stego PNG 提取文本
data_bytes = decode_png_to_text('stego.png', password='mypwd')
with open('recovered.txt', 'wb') as f:
    f.write(data_bytes)
所有异常均会抛出 Python 异常，如文件不存在、封面尺寸不足、压缩失败、解压失败等。应在调用时适当处理异常。

实现细节解析
以下内容解读代码内部逻辑，帮助理解其工作原理和设计考量。
1. 计算图像尺寸
为了确定能够容纳所有待嵌入字节的最小图像尺寸，函数 _compute_dimensions(num_pixels) 会计算接近正方形的宽度和高度。步骤如下：
计算 side = floor(sqrt(num_pixels))，初始宽度和高度均为 side。
如果 width * height < num_pixels，先增加宽度，再检查是否仍然不足；如果仍不足再增加高度。
返回 (width, height)。
这种策略能生成接近正方形的图片，使图片整体尺寸最小化，便于保存和传输。
2. 生成随机噪声图像
当没有提供封面图像时，程序通过 _generate_noise_image 创建随机噪声作为载体：
使用固定种子0 的 random.Random 实例生成伪随机数，保证每次生成的噪声相同，便于调试。
对于每个像素随机生成三个通道的值 (0–255)，Alpha 通道固定为 255（完全不透明）。
利用 Image.frombytes('RGBA', (width, height), bytes(data)) 构建 Pillow 图像对象。
随机噪声载体避免了真实图像中纹理和颜色分布的依赖，使得每个像素都可以安全地替换成任意值，并提供了最大的嵌入自由度。
3. 选择最佳压缩结果
函数 _choose_best_compression 遍历压缩算法字典 _COMPRESSION_ALGOS：
best_id = 0
best_data = data
best_len = len(data)
for algo_id, (name, compress_fn, _) in _COMPRESSION_ALGOS.items():
    if algo_id == 0:
        continue  # 不压缩情况已初始化
    try:
        comp = compress_fn(data)
    except Exception:
        continue  # 某些算法可能在内存不足时失败
    if len(comp) < best_len:
        best_id = algo_id
        best_data = comp
        best_len = len(comp)
return best_id, best_data
该函数忽略压缩失败的算法，确保返回的始终可用。若所有压缩后的数据均不比原始短，则保持算法编号为0（不压缩）。
4. 构建嵌入数据包
编码时，程序构建如下的数据包（payload）：
算法编号 (1字节)：取值0–255，对应 _COMPRESSION_ALGOS 中定义的算法。
压缩数据长度 (4字节)：无符号整数，采用大端字节序 (struct.pack('>BI', algo_id, len(comp)))。
压缩后的数据：真实的文本字节数据，若关闭压缩则与原始文本一致。
整个数据包大小为 1 + 4 + len(comp) 字节，程序据此计算所需像素数量：required_pixels = ceil(payload_length / 4)，因为每像素可存储 4字节。
5. 嵌入过程
准备载体：
若提供封面图像，程序使用 Pillow 打开并转换为 RGBA 模式，仅保留尺寸信息。程序会检查像素总数是否足够容纳数据，不够则抛出异常。
若未提供封面，则调用 _compute_dimensions 计算合适的宽高，随后生成随机噪声图像。
生成随机索引顺序：
生成长度为 total_pixels 的索引列表 [0,1,2,...]。
根据密码字符串计算种子：seed = sum((i + 1) * ord(ch) for i, ch in enumerate(password))。
使用此种子初始化 Python 内置的 random.Random，随后调用 shuffle(indices) 打乱索引顺序。
填充像素：使用 iter(payload) 将数据包分组，每次读取 4字节对应 RGBA 顺序，在随机索引数组中定位像素并替换其四个通道值。若不足四字节，则保留原有通道值。程序未对剩余像素作特殊处理。
保存 PNG：生成新的 Image 对象并写入像素数组，使用 compress_level=9 保存为 PNG，可减小文件体积。
6. 解码过程
读取 stego 图像：使用 Pillow 打开 PNG 文件并确保模式为 RGBA。
重建随机索引：与编码时一致，根据相同密码和像素数量重新生成并打乱索引数组。
提取字节：按照随机顺序收集每个像素四个通道的字节序列，得到 extracted_bytes。
解析头部：读取第一字节得到压缩算法编号，接下来的 4字节读取压缩数据长度 (comp_len)；如果提取的总字节数不足，则抛出错误。
解压缩：根据算法编号从 _COMPRESSION_ALGOS 中取出解压函数，对提取出的压缩数据进行解压。如果压缩编号为0，则直接返回原始数据。
返回结果：返回原始文本的字节序列，用户可以自行解码为字符串或写入文件。
解码过程必须与编码使用相同的密码，否则索引顺序不同将导致提取的数据包和解压缩失败。同时如果图像受到篡改、尺寸变化或压缩损坏，解码过程也可能失败。
7. 时间与空间复杂度
时间复杂度：主要由读取/写入图像像素和压缩算法所决定。嵌入或提取操作需要遍历所有像素，时间复杂度约为ON （其中N 为像素数）。压缩算法的复杂度取决于数据长度及算法本身，一般可视为 On 。
空间复杂度：程序需存储完整的像素数组和数据包，因此空间复杂度约为ON 。压缩期间可能需要额外内存 (特别是 LZMA)。
8. 可能的改进方向
错误更正与冗余编码：添加简单的校验和或错误更正码，以处理随机噪声或传输损坏导致的解码失败。
加密集成：将加密算法融入隐写流程，在嵌入前对数据进行加密，以提升安全性。
更复杂的载体使用：在真实图片中采用视觉感知模型，避开高频区域，减少修改造成的统计异常；或使用变换域 (如 DCT、DWT) 隐写。
改进压缩算法：集成更多压缩算法，例如 Brotli、Zstandard 或 xz，以得到更好的压缩率；但应注意算法解码的普遍性和性能。

使用示例
以下示例展示如何使用本工具生成 stego 图像并恢复其中的文本。
创建一个示例文本文件：
echo "隐写术是一项既古老又现代的艺术，它隐藏的不只是信息，还有信息存在的事实。" > secret.txt
将文本嵌入 PNG 图像：
python steganography_ultra.py encode secret.txt secret_stego.png --password 12345
执行该命令后，将在当前目录生成 secret_stego.png，可通过普通的图片查看器打开，不会显示任何异常。文件大小取决于压缩后文本长度和所选封面尺寸。
解码隐藏信息：
python steganography_ultra.py decode secret_stego.png recovered.txt --password 12345
cat recovered.txt
# 输出：
# 隐写术是一项既古老又现代的艺术，它隐藏的不只是信息，还有信息存在的事实。

安全与法律声明
隐写术被广泛应用于隐私保护、数字版权保护以及信息安全研究领域。然而，某些组织也可能将其用于非法用途。使用本工具前，请务必了解并遵守所在地的法律法规。作者及贡献者对于任何滥用行为不承担责任。

参考文献
LSB 隐写理论：介绍隐写术基本概念及 LSB 方法[1]。
Alpha 通道提升容量：Glasswall 研究指出，RGBA 图像比 RGB 图像多一字节的 LSB 容量，可在相同像素数量下存储更多数据[2]。
像素格式区别：硬件文档说明，RGB8 每像素占用 3字节，而 RGBa8 每像素占用 4字节[4]。
动态压缩算法选择：研究提出使用动态排名算法根据消息特性选择最佳压缩算法，以减少嵌入空间[3]。
压缩算法性能比较：LZMA 基准测试表明，gzip 压缩速度最快、内存占用低；bzip2 压缩率比 gzip 高 15% 左右，但速度较慢；lzma 提供最高压缩率但压缩慢，解压速度介于 gzip 和 bzip2 之间[6]。

感谢您使用 steganography_ultra。如果有疑问或改进建议，欢迎反馈。

[1] LSB based Image steganography using MATLAB - GeeksforGeeks
https://www.geeksforgeeks.org/computer-graphics/lsb-based-image-steganography-using-matlab/
[2] [5] Steganography: smudging the invisible ink
https://docs.glasswall.com/docs/steganography-smudging-the-invisible-ink
[3] (PDF) Optimal Secret Text Compression Technique for Steganographic Encoding by Dynamic Ranking Algorithm
https://www.researchgate.net/publication/338350347_Optimal_Secret_Text_Compression_Technique_for_Steganographic_Encoding_by_Dynamic_Ranking_Algorithm
[4] Color pixel formats
https://www.1stvision.com/cameras/IDS/IDS-manuals/en/basics-color-pixel-formats.html
[6] A Quick Benchmark: Gzip vs. Bzip2 vs. LZMA
https://tukaani.org/lzma/benchmarks.html
