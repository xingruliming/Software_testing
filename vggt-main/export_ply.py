"""将 predictions.npz 导出为 PLY 点云文件"""
import numpy as np
import trimesh
import argparse
import os

def export_ply(npz_path, output_path=None, conf_thres=50.0, mode="pointmap"):
    """
    Args:
        npz_path: predictions.npz 文件路径
        output_path: 输出 PLY 路径，默认与 npz 同目录同名 .ply
        conf_thres: 置信度过滤百分比 (0-100)，越低保留越多点
        mode: "pointmap" 使用世界点云分支 / "depth" 使用深度图分支
    """
    data = np.load(npz_path, allow_pickle=True)

    if mode == "pointmap" and "world_points" in data:
        print("使用 Pointmap Branch 的世界坐标")
        points = data["world_points"]
        conf = data.get("world_points_conf", np.ones_like(points[..., 0]))
    else:
        print("使用 Depthmap Branch 的世界坐标")
        points = data["world_points_from_depth"]
        conf = data.get("depth_conf", np.ones_like(points[..., 0]))

    # 获取颜色
    images = data["images"]
    if images.ndim == 4 and images.shape[1] == 3:
        colors = np.transpose(images, (0, 2, 3, 1))
    else:
        colors = images

    # 展平
    S, H, W, _ = points.shape
    vertices = points.reshape(-1, 3)
    colors_rgb = (colors.reshape(-1, 3) * 255).astype(np.uint8)
    conf_flat = conf.reshape(-1)

    # 置信度过滤
    threshold = np.percentile(conf_flat, conf_thres) if conf_thres > 0 else 0.0
    mask = (conf_flat >= threshold) & (conf_flat > 1e-5)
    vertices = vertices[mask]
    colors_rgb = colors_rgb[mask]

    print(f"原始点数: {len(conf_flat):,}, 过滤后: {len(vertices):,} (conf_thres={conf_thres}%)")

    # 导出 PLY
    if output_path is None:
        output_path = npz_path.replace(".npz", ".ply")

    pcd = trimesh.PointCloud(vertices=vertices, colors=colors_rgb)
    pcd.export(output_path)
    print(f"已导出: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VGGT predictions.npz → PLY")
    parser.add_argument("npz_path", help="predictions.npz 文件路径")
    parser.add_argument("-o", "--output", default=None, help="输出 PLY 路径（默认同名 .ply）")
    parser.add_argument("-c", "--conf", type=float, default=50.0, help="置信度阈值百分比 (0-100)，默认 50")
    parser.add_argument("-m", "--mode", choices=["pointmap", "depth"], default="pointmap",
                        help="预测分支: pointmap(默认) / depth")
    args = parser.parse_args()
    export_ply(args.npz_path, args.output, args.conf, args.mode)
