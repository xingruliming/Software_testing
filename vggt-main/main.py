import torch
from vggt.models.vggt import VGGT
from vggt.utils.load_fn import load_and_preprocess_images

device = "cuda" if torch.cuda.is_available() else "cpu"
# bfloat16在Ampere GPU（计算能力8.0+）上支持
dtype = torch.bfloat16 if torch.cuda.get_device_capability()[0] >= 8 else torch.float16

# 初始化模型并加载本地预训练权重
model = VGGT()
model.load_state_dict(torch.load(r"E:\0_work\vggt\model.pt", map_location=device))
model.eval()
model = model.to(device)

# 加载并预处理示例图像（替换为你的图像路径）
image_names = ["examples/kitchen/images/00.png", "examples/kitchen/images/01.png", "examples/kitchen/images/02.png"]
images = load_and_preprocess_images(image_names).to(device)

with torch.no_grad():
    with torch.amp.autocast("cuda",dtype=dtype):
        # 预测包括相机、深度图和点图在内的属性
        predictions = model(images)