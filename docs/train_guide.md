# YOLO 模型训练操作手册

> 训练 YOLOv8n 4分类目标检测模型，用于识别灵虚界传送门（紫/金/红）和占点圈。

---

## 目录

- [环境准备](#环境准备)
- [Step 1: 游戏内截图采集](#step-1-游戏内截图采集)
- [Step 2: 数据标注（LabelImg）](#step-2-数据标注labelimg)
- [Step 3: 数据增强（Roboflow）](#step-3-数据增强roboflow)
- [Step 4: 训练数据集目录结构](#step-4-训练数据集目录结构)
- [Step 5: 训练模型](#step-5-训练模型)
- [Step 6: 验证与评估](#step-6-验证与评估)
- [Step 7: 部署到项目](#step-7-部署到项目)
- [常见问题](#常见问题)

---

## 环境准备

```bash
pip install ultralytics labelImg
```

| 工具 | 版本要求 | 用途 |
|------|---------|------|
| ultralytics | >= 8.1.0 | YOLOv8 训练与推理 |
| labelImg | >= 1.8.6 | 数据标注 |
| Roboflow | 在线平台（免费账号） | 数据增强（可选） |

---

## Step 1: 游戏内截图采集

### 目标数量

| 类别 ID | 类别名称 | 说明 | 建议原始数量 |
|---------|---------|------|------------|
| 0 | `portal_purple` | 紫色传送门（1-3关入口） | 80-100张 |
| 1 | `portal_gold` | 金色传送门（商店关入口） | 80-100张 |
| 2 | `portal_red` | 红色传送门（Boss关入口） | 80-100张 |
| 3 | `capture_zone` | 占点圈（占点模式地图中的圆形区域） | 100-150张 |

### 采集要求

采集时需要覆盖多种视角和距离：
- **多角度**：正面、左侧约30°、右侧约30°、仰视、俯视
- **多距离**：远（传送门较小）、中（传送门中等大小）、近（传送门占画面较大）
- **不同光照/背景**：不同关卡地图背景，有其他物体遮挡等情况

### 使用自动截图脚本采集

在游戏内移动绕圈的同时，运行以下命令自动截图保存：

```bash
cd naraka_lingxu
python tools/collect_screenshots.py --class portal_purple --interval 1.0
```

**手动脚本（无需额外文件）**：

```python
import mss
import cv2
import time
import os

save_dir = "assets/portals/purple"  # 改为对应目录: purple/gold/red, 或 capture_zone
os.makedirs(save_dir, exist_ok=True)

with mss.mss() as sct:
    monitor = sct.monitors[1]  # 主显示器
    count = 0
    print("开始截图，按 Ctrl+C 停止")
    while True:
        img = sct.grab(monitor)
        frame = cv2.cvtColor(__import__('numpy').array(img), cv2.COLOR_BGRA2BGR)
        filename = f"{save_dir}/frame_{count:04d}.png"
        cv2.imwrite(filename, frame)
        count += 1
        print(f"已保存: {filename}")
        time.sleep(1.0)
```

> 采集完成后人工筛选，删除画面中不含目标物体的帧，或目标模糊、遮挡严重的帧。

---

## Step 2: 数据标注（LabelImg）

### 2.1 启动 LabelImg

```bash
labelImg
```

### 2.2 配置标注格式

1. 打开 LabelImg 后，点击菜单 **View → Auto Save Mode**（启用自动保存）
2. 点击菜单 **Change Save Dir** → 选择图片所在目录
3. **重要**：在左侧工具栏切换格式为 **YOLO**（默认是 Pascal VOC，需手动切换）

### 2.3 类别文件配置

在图片目录下创建 `classes.txt` 文件：

```
portal_purple
portal_gold
portal_red
capture_zone
```

### 2.4 标注操作步骤

1. 点击 **Open Dir** 选择截图目录
2. 对每张图片：
   - 按 `W` 创建矩形框
   - 拖拽框住目标物体（传送门/占点圈）
   - 在弹出的标签框中选择对应类别
   - 按 `D` 进入下一张

### 2.5 标注要点

| 注意项 | 说明 |
|--------|------|
| 框的范围 | 尽量贴合目标边缘，不要过大或过小 |
| 部分遮挡 | 若目标被部分遮挡（>50%可见），仍需标注 |
| 多个目标 | 一张图中可标注多个目标框（例如画面中同时出现2个传送门） |
| 类别准确 | 紫色=0, 金色=1, 红色=2, 圈=3，确保颜色区分准确 |

### 2.6 标注结果

每张 `.png` 图片对应一个同名 `.txt` 文件，格式：

```
class_id cx cy width height
0 0.512 0.445 0.124 0.238
```

> 所有坐标均为归一化值（0-1之间），基于图片宽高。

---

## Step 3: 数据增强（Roboflow）

数据增强可以显著提升模型泛化性，建议使用 Roboflow 在线平台。

### 3.1 使用 Roboflow（推荐）

1. 访问 [https://roboflow.com](https://roboflow.com) 并创建免费账号
2. 创建新项目，选择 **Object Detection**
3. 上传标注好的数据集（图片 + YOLO格式txt文件）
4. 设置 Augmentation（数据增强）：
   - ✅ **Horizontal Flip**（水平翻转）
   - ✅ **Brightness** ±20%（亮度变化）
   - ✅ **Exposure** ±15%（曝光变化）
   - ✅ **Blur** 0-1.5px（模糊，模拟远距离）
   - ✅ **Random Crop** 0-20%（随机裁剪）
5. 按 8:1:1 比例划分 Train/Valid/Test
6. 导出为 **YOLOv8 格式**，下载到本地

### 3.2 手动增强（备选）

```python
import cv2
import numpy as np
import os

def augment_image(img_path, label_path, save_dir, count=3):
    img = cv2.imread(img_path)
    # 读取 label
    with open(label_path) as f:
        labels = f.read()

    for i in range(count):
        aug = img.copy()
        # 亮度调整
        alpha = np.random.uniform(0.7, 1.3)
        aug = np.clip(aug * alpha, 0, 255).astype(np.uint8)
        # 水平翻转（同时需要翻转bbox的cx: new_cx = 1 - cx）
        if np.random.rand() > 0.5:
            aug = cv2.flip(aug, 1)
            new_labels = []
            for line in labels.strip().split('\n'):
                parts = line.split()
                parts[1] = str(1.0 - float(parts[1]))
                new_labels.append(' '.join(parts))
            save_labels = '\n'.join(new_labels)
        else:
            save_labels = labels

        base = os.path.splitext(os.path.basename(img_path))[0]
        cv2.imwrite(f"{save_dir}/{base}_aug{i}.png", aug)
        with open(f"{save_dir}/{base}_aug{i}.txt", 'w') as f:
            f.write(save_labels)
```

---

## Step 4: 训练数据集目录结构

```
datasets/
├── naraka.yaml                # 数据集配置文件
├── train/
│   ├── images/                # 训练集图片
│   │   ├── frame_0001.png
│   │   └── ...
│   └── labels/                # 训练集标签
│       ├── frame_0001.txt
│       └── ...
├── valid/
│   ├── images/
│   └── labels/
└── test/
    ├── images/
    └── labels/
```

### naraka.yaml 内容

```yaml
# datasets/naraka.yaml
path: ./datasets          # 数据集根路径（相对于运行目录）
train: train/images
val: valid/images
test: test/images

nc: 4                     # 类别数量
names:
  - portal_purple
  - portal_gold
  - portal_red
  - capture_zone
```

---

## Step 5: 训练模型

```bash
cd naraka_lingxu

# 训练 YOLOv8n（nano版，速度最快，适合实时推理）
yolo detect train \
  model=yolov8n.pt \
  data=datasets/naraka.yaml \
  epochs=100 \
  imgsz=1280 \
  batch=8 \
  project=models \
  name=naraka_v1 \
  patience=20 \
  device=mps
```

### 参数说明

| 参数 | 值 | 说明 |
|------|-----|------|
| `model` | yolov8n.pt | 使用 nano 版预训练模型（首次运行自动下载） |
| `data` | datasets/naraka.yaml | 数据集配置文件 |
| `epochs` | 100 | 训练轮数 |
| `imgsz` | 1280 | 输入图像尺寸（游戏画面较大，推荐1280） |
| `batch` | 8 | 批量大小（根据内存调整，M系列Mac可用16） |
| `patience` | 20 | 早停轮数（20轮无提升则停止） |
| `device` | mps | Apple Silicon GPU（Intel Mac 改为 cpu） |

### 训练输出

```
models/naraka_v1/
├── weights/
│   ├── best.pt           # 最佳权重（部署用）
│   └── last.pt           # 最后一轮权重
├── results.png           # 训练曲线图
├── confusion_matrix.png  # 混淆矩阵
└── args.yaml             # 训练参数记录
```

---

## Step 6: 验证与评估

```bash
# 在验证集上评估模型性能
yolo detect val \
  model=models/naraka_v1/weights/best.pt \
  data=datasets/naraka.yaml

# 在测试图片上可视化检测结果
yolo detect predict \
  model=models/naraka_v1/weights/best.pt \
  source=datasets/test/images/ \
  conf=0.6 \
  save=True
```

### 合格标准

| 指标 | 最低要求 | 理想值 |
|------|---------|-------|
| mAP50 | > 0.80 | > 0.90 |
| mAP50-95 | > 0.60 | > 0.75 |
| 各类别 Precision | > 0.75 | > 0.85 |
| 各类别 Recall | > 0.75 | > 0.85 |

> 如果某个类别效果差，需要补充该类别的训练数据后重新训练。

### 推理速度验证

```python
from ultralytics import YOLO
import cv2, time

model = YOLO("models/naraka_v1/weights/best.pt")
img = cv2.imread("datasets/test/images/frame_0001.png")

# 预热
model(img, verbose=False)

# 计时
start = time.time()
for _ in range(10):
    results = model(img, conf=0.6, verbose=False)
avg_ms = (time.time() - start) / 10 * 1000
print(f"平均推理时间: {avg_ms:.1f}ms（要求 < 500ms）")
```

---

## Step 7: 部署到项目

```bash
# 将训练好的权重复制到项目 models 目录
cp models/naraka_v1/weights/best.pt models/naraka_v1/weights/best.pt
```

确认 `config.yaml` 中模型路径配置正确：

```yaml
models:
  detector: "models/naraka_v1/weights/best.pt"
```

运行程序时若检测到模型文件存在，YOLO 会自动加载。

---

## 常见问题

### Q: 训练数据太少，mAP 很低？
**A:** 每类至少需要 50 张原始标注图片，配合增强后达到 200+。建议在不同关卡、不同时间段多次采集。

### Q: Apple Silicon Mac 训练速度？
**A:** M系列芯片使用 `device=mps`，100epochs约需要20-40分钟（取决于数据量）。

### Q: 某个类别总是漏检？
**A:** 检查该类别的训练数据是否足够，以及标注是否准确。可以专门针对该类别补充数据。

### Q: 模型文件太大？
**A:** YOLOv8n 的 best.pt 约 6MB，可以正常使用。如果需要更小，可改用 `yolov8n-cls.pt` 或导出为 ONNX 格式。

### Q: 传送门在不同地图背景下检测效果差？
**A:** 采集时需要覆盖所有5个关卡的地图背景。重点确保各关卡地图下的传送门都有截图。