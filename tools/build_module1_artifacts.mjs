import fs from "node:fs/promises";
import path from "node:path";
import {
  AlignmentType,
  BorderStyle,
  Document,
  Footer,
  HeadingLevel,
  LevelFormat,
  Packer,
  PageNumber,
  Paragraph,
  ShadingType,
  TextRun,
} from "docx";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [workspaceRoot, sourceWorkbook, manualMarkdown, outputDirectory] = process.argv.slice(2);
if (!workspaceRoot || !sourceWorkbook || !manualMarkdown || !outputDirectory) {
  throw new Error("Usage: node build_module1_artifacts.mjs <workspaceRoot> <sourceWorkbook> <manualMarkdown> <outputDirectory>");
}

await fs.mkdir(outputDirectory, { recursive: true });
const previewDirectory = path.join(workspaceRoot, ".codex_tmp", "xlsx_previews");
await fs.mkdir(previewDirectory, { recursive: true });

const input = await FileBlob.load(sourceWorkbook);
const workbook = await SpreadsheetFile.importXlsx(input);
const beforePreview = await workbook.render({
  sheetName: "Information文档信息",
  range: "A1:L43",
  scale: 1,
  format: "png",
});
await fs.writeFile(path.join(previewDirectory, "test_cases_before.png"), new Uint8Array(await beforePreview.arrayBuffer()));

const information = workbook.worksheets.getItem("Information文档信息");
const testCases = workbook.worksheets.getItem("Test Cases测试用例");
const beforeCasesPreview = await workbook.render({
  sheetName: "Test Cases测试用例",
  range: "A1:M8",
  scale: 1,
  format: "png",
});
await fs.writeFile(path.join(previewDirectory, "test_cases_detail_before.png"), new Uint8Array(await beforeCasesPreview.arrayBuffer()));

const commonPrecondition = "已安装 NumPy、PyTorch；可导入 vggt.utils.geometry；使用 CPU 张量；浮点比较容差 atol=1e-6。";
const testCaseRows = [
  [
    "M1-GEO-001",
    "depth_to_cam_coords_points",
    "单像素中心点反投影",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "depth_map=np.array([[2.0]]); intrinsic=np.array([[2,0,0],[0,4,0],[0,0,1]])",
    "1. 构造深度图和内参矩阵。\n2. 调用 depth_to_cam_coords_points。\n3. 检查形状、类型和坐标值。",
    "返回 shape=(1,1,3)、dtype=float32；唯一坐标为 [0,0,2]。",
    null,
    null,
    "等价类：有效单像素输入",
  ],
  [
    "M1-GEO-002",
    "depth_to_cam_coords_points",
    "主点位于右下角的 2×2 深度图",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "depth_map=np.ones((2,2)); intrinsic=np.array([[1,0,1],[0,1,1],[0,0,1]])",
    "调用函数并逐像素比较返回的三维相机坐标。",
    "返回 [[[-1,-1,1],[0,-1,1]],[[-1,0,1],[0,0,1]]]，shape=(2,2,3)。",
    null,
    null,
    "边界值：图像四个边角",
  ],
  [
    "M1-GEO-003",
    "depth_to_cam_coords_points",
    "全零深度图",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "depth_map=np.zeros((2,3)); intrinsic=np.eye(3)",
    "调用函数，检查全部输出元素及输出形状。",
    "返回 shape=(2,3,3) 的 float32 数组，所有坐标均为 [0,0,0]。",
    null,
    null,
    "边界值：深度下界 0",
  ],
  [
    "M1-GEO-004",
    "depth_to_cam_coords_points",
    "内参矩阵尺寸非法",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "depth_map=np.ones((1,1)); intrinsic=np.eye(2)",
    "调用函数并捕获异常。",
    "抛出 AssertionError，消息包含 'Intrinsic matrix must be 3x3'。",
    null,
    null,
    "等价类：无效矩阵尺寸",
  ],
  [
    "M1-GEO-005",
    "depth_to_cam_coords_points",
    "内参矩阵含非零偏斜项",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "depth_map=np.ones((1,1)); intrinsic=np.array([[1,0.1,0],[0,1,0],[0,0,1]])",
    "调用函数并捕获异常。",
    "抛出 AssertionError，消息包含 'Intrinsic matrix must have zero skew'。",
    null,
    null,
    "错误推测：不支持的非零 skew",
  ],
  [
    "M1-GEO-006",
    "closed_form_inverse_se3",
    "NumPy 单位 SE(3) 矩阵求逆",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "se3=np.eye(4)[None,:,:]",
    "调用 closed_form_inverse_se3，比较输入输出矩阵。",
    "返回 shape=(1,4,4) 的 NumPy 数组，结果等于 4×4 单位矩阵。",
    null,
    null,
    "等价类：单位变换",
  ],
  [
    "M1-GEO-007",
    "closed_form_inverse_se3",
    "NumPy 批量平移矩阵求逆",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "se3 包含两帧：I4；以及 [I3 | (1,2,3)^T] 的 3×4 矩阵（补齐为同形 4×4 批量）",
    "批量调用函数；分别校验两帧结果。",
    "第一帧仍为 I4；第二帧旋转仍为 I3，平移变为 (-1,-2,-3)，底行为 [0,0,0,1]。",
    null,
    null,
    "等价类：批量输入；组合覆盖",
  ],
  [
    "M1-GEO-008",
    "closed_form_inverse_se3",
    "绕 Z 轴 90°旋转矩阵求逆",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "se3=[[[0,-1,0,0],[1,0,0,0],[0,0,1,0]]]，shape=(1,3,4)",
    "调用函数并检查旋转块与齐次底行。",
    "旋转块为 [[0,1,0],[-1,0,0],[0,0,1]]；平移为 0；底行为 [0,0,0,1]。",
    null,
    null,
    "等价类：纯旋转；逆变换性质",
  ],
  [
    "M1-GEO-009",
    "closed_form_inverse_se3",
    "Torch float64 类型与设备保持",
    "中",
    "可自动化",
    "新增",
    commonPrecondition,
    "se3=torch.eye(4,dtype=torch.float64).unsqueeze(0)",
    "调用函数，检查数值、dtype、device 和 shape。",
    "结果等于单位矩阵；dtype 为 torch.float64；device 与输入一致；shape=(1,4,4)。",
    null,
    null,
    "等价类：Torch 输入；类型保持",
  ],
  [
    "M1-GEO-010",
    "closed_form_inverse_se3",
    "SE(3) 尾部尺寸非法",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "se3=np.zeros((1,4,3))",
    "调用函数并捕获异常。",
    "抛出 ValueError，消息说明 se3 必须为 (N,4,4) 或 (N,3,4)，并包含实际 shape。",
    null,
    null,
    "边界值：尾部矩阵尺寸",
  ],
  [
    "M1-GEO-011",
    "depth_to_world_coords_points",
    "深度图为 None",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "depth_map=None；extrinsic、intrinsic 可传任意占位值",
    "调用函数并检查三个返回值。",
    "返回 (None, None, None)，且不继续访问矩阵。",
    null,
    null,
    "等价类：空输入",
  ],
  [
    "M1-GEO-012",
    "depth_to_world_coords_points",
    "单位内外参下世界坐标等于相机坐标",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "depth_map=np.array([[1,2]]); intrinsic=I3; extrinsic=[I3|0]",
    "调用函数；比较 world_coords、cam_coords 和 point_mask。",
    "cam/world 坐标均为 [[[0,0,1],[2,0,2]]]；mask 为 [[True,True]]。",
    null,
    null,
    "等价类：单位坐标系",
  ],
  [
    "M1-GEO-013",
    "depth_to_world_coords_points",
    "含平移外参的相机到世界变换",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "depth_map=np.array([[2.0]]); intrinsic=I3; extrinsic=[I3|(1,2,3)^T]",
    "调用函数并检查相机坐标、世界坐标和有效掩码。",
    "cam=[0,0,2]；world=[-1,-2,-1]；mask=True。",
    null,
    null,
    "等价类：纯平移；逆变换",
  ],
  [
    "M1-GEO-014",
    "depth_to_world_coords_points",
    "默认 eps 附近的深度有效性",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "depth_map=np.array([[0,1e-8,1.1e-8,-1.0]]); intrinsic=I3; extrinsic=[I3|0]; eps=1e-8",
    "调用函数并只比较 point_mask 的四个布尔值。",
    "point_mask 等于 [[False,False,True,False]]；判断规则为 depth > eps。",
    null,
    null,
    "边界值：eps-、eps、eps+",
  ],
  [
    "M1-GEO-015",
    "depth_to_world_coords_points",
    "旋转外参下的世界坐标",
    "中",
    "可自动化",
    "新增",
    commonPrecondition,
    "depth_map=np.array([[0,1]]); intrinsic=I3; extrinsic 的旋转为绕 Z 轴 +90°，平移为 0",
    "调用函数并检查两个像素的世界坐标。",
    "第 0 个像素为 [0,0,0]；第 1 个像素相机坐标 [1,0,1]，世界坐标 [0,-1,1]。",
    null,
    null,
    "组合覆盖：深度与旋转",
  ],
  [
    "M1-GEO-016",
    "unproject_depth_map_to_point_map",
    "两帧深度图批量反投影",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "depth_map=np.array([[[1.0]],[[2.0]]]); 两帧 intrinsic=I3；两帧 extrinsic=[I3|0]",
    "调用函数并检查批量维度和两帧坐标。",
    "返回 shape=(2,1,1,3)；两帧坐标分别为 [0,0,1]、[0,0,2]。",
    null,
    null,
    "等价类：多帧批处理",
  ],
  [
    "M1-GEO-017",
    "unproject_depth_map_to_point_map",
    "带末尾单通道维度的深度图",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "depth_map=np.array([[[[1.0],[2.0]]]])，shape=(1,1,2,1)；intrinsic=I3；extrinsic=[I3|0]",
    "调用函数，确认 squeeze(-1) 后仍正确反投影。",
    "返回 shape=(1,1,2,3)，两个点为 [0,0,1] 和 [2,0,2]。",
    null,
    null,
    "等价类：文档允许的四维输入",
  ],
  [
    "M1-GEO-018",
    "unproject_depth_map_to_point_map",
    "Torch 输入自动转为 NumPy",
    "中",
    "可自动化",
    "新增",
    commonPrecondition,
    "depth=torch.tensor([[[3.0]]]); intrinsic=torch.eye(3)[None]; extrinsic=torch.cat([I3,0],dim=1)[None]",
    "调用函数并检查返回类型、shape 和数值。",
    "返回类型为 np.ndarray，shape=(1,1,1,3)，坐标为 [0,0,3]。",
    null,
    null,
    "等价类：Torch/NumPy 类型转换",
  ],
  [
    "M1-GEO-019",
    "unproject_depth_map_to_point_map",
    "深度帧数与外参数量不一致",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "depth shape=(2,1,1)；extrinsics shape=(1,3,4)；intrinsics shape=(2,3,3)",
    "调用函数并捕获第二帧访问外参时的异常。",
    "抛出 IndexError，不返回部分堆叠结果。",
    null,
    null,
    "错误推测：批量长度不一致",
  ],
  [
    "M1-GEO-020",
    "project_world_points_to_camera_points_batch",
    "单位外参批量投影到相机坐标",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "world_points shape=(1,1,1,2,3)，点为 [0,0,1]、[1,2,3]；extrinsic=[I3|0]",
    "调用函数，检查齐次扩展和矩阵乘法结果。",
    "返回 shape=(1,1,1,2,3)，两个相机点与输入世界点完全相同。",
    null,
    null,
    "等价类：单位外参",
  ],
  [
    "M1-GEO-021",
    "project_world_points_to_camera_points_batch",
    "平移外参批量投影",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "world_points=[0,0,1]，shape=(1,1,1,1,3)；extrinsic=[I3|(1,0,0)^T]",
    "调用函数并比较相机坐标。",
    "返回点 [1,0,1]，shape=(1,1,1,1,3)。",
    null,
    null,
    "等价类：纯平移",
  ],
  [
    "M1-GEO-022",
    "project_world_points_to_camera_points_batch",
    "不同帧外参的广播计算",
    "中",
    "可自动化",
    "新增",
    commonPrecondition,
    "B=1,S=2,H=W=1；两帧 world_points 均为 [1,1,1]；外参依次为 [I3|0]、[I3|(1,2,3)^T]",
    "调用函数并分别检查两帧输出及 shape。",
    "返回 shape=(1,2,1,1,3)；两帧结果依次为 [1,1,1]、[2,3,4]。",
    null,
    null,
    "组合覆盖：帧维度广播",
  ],
  [
    "M1-GEO-023",
    "img_from_cam",
    "单位内参的透视除法",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "K=I3；cam_points(B×3×N)=[[[2,-1],[4,1],[2,1]]]；distortion_params=None",
    "调用函数，检查两个点的像素坐标和输出排列。",
    "返回 shape=(1,2,2)，像素坐标依次为 [1,2]、[-1,1]。",
    null,
    null,
    "等价类：无畸变正常投影",
  ],
  [
    "M1-GEO-024",
    "img_from_cam",
    "自定义焦距和主点的像素投影",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "K=[[2,0,10],[0,3,20],[0,0,1]]；cam_point=[1,2,1]",
    "调用函数并按 u=fx·x/z+cx、v=fy·y/z+cy 复核。",
    "返回像素坐标 [12,26]，shape=(1,1,2)。",
    null,
    null,
    "等价类：非单位内参",
  ],
  [
    "M1-GEO-025",
    "img_from_cam",
    "Z 为零导致 NaN 时使用默认值",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "K=I3；cam_point=[0,0,0]；default=-9.0",
    "调用函数；允许底层产生除零警告；检查 nan_to_num 后的像素值。",
    "返回像素坐标 [-9,-9]，两个 NaN 均替换为 default。",
    null,
    null,
    "边界值：Z=0；错误推测",
  ],
  [
    "M1-GEO-026",
    "img_from_cam",
    "零畸变参数等价于无畸变",
    "中",
    "可自动化",
    "新增",
    commonPrecondition,
    "K=I3；cam_point=[1,2,2]；distortion_params=torch.tensor([[0.0]])",
    "分别以 distortion_params=None 和零参数调用函数，比较结果。",
    "两次均返回 [0.5,1.0]，差值在 atol=1e-6 内。",
    null,
    null,
    "等价类：可选参数 None/零值",
  ],
  [
    "M1-GEO-027",
    "project_world_points_to_cam",
    "单位内外参的世界点投影",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "world_points=[[0,0,1],[2,4,2]]；extrinsic=[I3|0]；intrinsic=I3",
    "调用函数，同时检查 image_points 与 cam_points。",
    "image_points=[[[0,0],[1,2]]]；cam_points shape=(1,3,2)，列向量分别为 [0,0,1]、[2,4,2]。",
    null,
    null,
    "等价类：端到端投影正常路径",
  ],
  [
    "M1-GEO-028",
    "project_world_points_to_cam",
    "平移外参与自定义内参组合投影",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "world_point=[0,0,1]；extrinsic=[I3|(1,2,0)^T]；K=[[2,0,10],[0,3,20],[0,0,1]]",
    "调用函数并分别校验相机坐标与像素坐标。",
    "cam_point=[1,2,1]；image_point=[12,26]。",
    null,
    null,
    "组合覆盖：外参平移×非单位内参",
  ],
  [
    "M1-GEO-029",
    "project_world_points_to_cam",
    "only_points_cam 跳过像素投影",
    "中",
    "可自动化",
    "新增",
    commonPrecondition,
    "world_point=[1,2,3]；extrinsic=[I3|(1,0,-1)^T]；cam_intrinsics=None；only_points_cam=True",
    "调用函数并检查两个返回值。",
    "image_points 为 None；cam_points shape=(1,3,1)，唯一列向量为 [2,2,2]。",
    null,
    null,
    "判定表：only_points_cam=True 分支",
  ],
  [
    "M1-GEO-030",
    "cam_from_img",
    "根据焦距和主点归一化像素轨迹",
    "高",
    "可自动化",
    "新增",
    commonPrecondition,
    "pred_tracks=[[[10,20],[12,26]]]；K=[[2,0,10],[0,3,20],[0,0,1]]；extra_params=None",
    "调用函数并逐点计算 (track-principal_point)/focal_length。",
    "返回 shape=(1,2,2)，归一化坐标依次为 [0,0]、[1,2]。",
    null,
    null,
    "等价类：无畸变归一化",
  ],
  [
    "M1-GEO-031",
    "cam_from_img",
    "不同内参的批量轨迹归一化",
    "中",
    "可自动化",
    "新增",
    commonPrecondition,
    "B=2,N=1；第1批 track=[2,4], fx=fy=2,cx=cy=0；第2批 track=[5,7], fx=4,fy=5,cx=1,cy=2",
    "批量调用函数并检查每个批次独立使用其内参。",
    "返回 shape=(2,1,2)；两批归一化坐标分别为 [1,2]、[1,1]。",
    null,
    null,
    "组合覆盖：批量内参差异",
  ],
  [
    "M1-GEO-032",
    "cam_from_img",
    "零畸变参数的反畸变分支",
    "中",
    "可自动化",
    "新增",
    commonPrecondition,
    "pred_tracks=[[[0.5,-0.25]]]；K=I3；extra_params=torch.tensor([[0.0]])",
    "分别以 extra_params=None 和零参数调用函数，比较返回值。",
    "两次均返回 [0.5,-0.25]，零畸变分支与无畸变结果在 atol=1e-6 内一致。",
    null,
    null,
    "判定表：extra_params 有/无；等价类",
  ],
];

testCases.getRange("A2:M33").values = testCaseRows;
testCases.getRange("A2:M33").format.verticalAlignment = "top";
testCases.getRange("A2:M33").format.wrapText = true;
testCases.getRange("A2:M33").format.rowHeight = 84;
testCases.getRange("A1:A33").format.columnWidth = 16;
testCases.getRange("B1:B33").format.columnWidth = 25;
testCases.getRange("C1:C33").format.columnWidth = 28;
testCases.getRange("D1:D33").format.columnWidth = 10;
testCases.getRange("E1:E33").format.columnWidth = 14;
testCases.getRange("F1:F33").format.columnWidth = 10;
testCases.getRange("G1:G33").format.columnWidth = 30;
testCases.getRange("H1:H33").format.columnWidth = 46;
testCases.getRange("I1:I33").format.columnWidth = 34;
testCases.getRange("J1:J33").format.columnWidth = 46;
testCases.getRange("K1:K33").format.columnWidth = 18;
testCases.getRange("L1:L33").format.columnWidth = 12;
testCases.getRange("M1:M33").format.columnWidth = 22;
testCases.freezePanes.freezeRows(1);
information.getRange("E13").formulas = [["=COUNTA('Test Cases测试用例'!A:A)-1"]];
information.getRange("E7").values = [["模块一（教师已许可 AI 参与）"]];
information.getRange("J7").values = [["课程作业"]];
information.getRange("E8").values = [["VGGT 几何坐标转换模块"]];
information.getRange("J8").values = [["【待填写：项目ID】"]];
information.getRange("E9").values = [["【待填写：拟制人】"]];
information.getRange("J9").values = [["【待填写：日期】"]];
information.getRange("E10").values = [["【待填写：评审人】"]];
information.getRange("J10").values = [["【待填写：日期】"]];
information.getRange("E11").values = [["【待填写：批准人】"]];
information.getRange("J11").values = [["【待填写：日期】"]];
information.getRange("B16").values = [["模块一坐标转换测试用例共 32 条。教师已明确许可 AI 参与用例设计；实际结果与状态仍须执行后据实填写。"]];
information.getRange("B20").values = [["2026.09.10"]];
information.getRange("C20").values = [["0.10"]];
information.getRange("D20").values = [["N/A"]];
information.getRange("E20").values = [["建立待人工填写副本；未生成计分测试用例"]];
information.getRange("K20").values = [["【待填写】"]];
information.getRange("B21").values = [["2026.09.10"]];
information.getRange("C21").values = [["0.20"]];
information.getRange("D21").values = [["0.10"]];
information.getRange("E21").values = [["教师许可 AI 参与后，新增 32 条坐标转换测试用例"]];
information.getRange("K21").values = [["【待填写】"]];

workbook.recalculate();
const afterPreview = await workbook.render({
  sheetName: "Information文档信息",
  range: "A1:L43",
  scale: 1,
  format: "png",
});
await fs.writeFile(path.join(previewDirectory, "test_cases_after.png"), new Uint8Array(await afterPreview.arrayBuffer()));

const afterCasesPreview = await workbook.render({
  sheetName: "Test Cases测试用例",
  range: "A1:M33",
  scale: 0.8,
  format: "png",
});
await fs.writeFile(path.join(previewDirectory, "test_cases_detail_after.png"), new Uint8Array(await afterCasesPreview.arrayBuffer()));

const outputWorkbook = await SpreadsheetFile.exportXlsx(workbook);
// Artifact Tool is useful for previews, but re-exporting this legacy course
// template drops Excel-specific package parts on some Office versions. Keep
// the generated workbook in the ignored preview directory and use native
// Excel when producing the final deliverable.
await outputWorkbook.save(path.join(previewDirectory, "test_cases_artifact_preview.xlsx"));
console.warn("Spreadsheet preview generated only; preserve the final template with native Excel.");

const inspectResult = await workbook.inspect({
  kind: "region",
  sheetId: "Test Cases测试用例",
  range: "A1:M33",
  maxChars: 12000,
  tableMaxRows: 35,
  tableMaxCols: 13,
});
console.log(inspectResult.ndjson);

const markdown = await fs.readFile(manualMarkdown, "utf8");
const lines = markdown.replace(/\r\n/g, "\n").split("\n");
const children = [];
let inCode = false;

for (const rawLine of lines) {
  const line = rawLine.trimEnd();
  if (line.startsWith("```")) {
    inCode = !inCode;
    continue;
  }
  if (inCode) {
    children.push(new Paragraph({
      spacing: { after: 0 },
      shading: { type: ShadingType.CLEAR, fill: "F3F4F6" },
      children: [new TextRun({ text: line || " ", font: "Consolas", size: 19 })],
    }));
    continue;
  }
  if (!line.trim()) {
    children.push(new Paragraph({ spacing: { after: 80 } }));
    continue;
  }
  if (line.startsWith("# ")) {
    children.push(new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun(line.slice(2))] }));
    continue;
  }
  if (line.startsWith("## ")) {
    children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(line.slice(3))] }));
    continue;
  }
  if (line.startsWith("### ")) {
    children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(line.slice(4))] }));
    continue;
  }
  if (/^- /.test(line)) {
    children.push(new Paragraph({
      numbering: { reference: "manual-bullets", level: 0 },
      children: [new TextRun(line.slice(2).replace(/`/g, ""))],
    }));
    continue;
  }
  const numbered = line.match(/^(\d+)\.\s+(.*)$/);
  if (numbered) {
    children.push(new Paragraph({
      numbering: { reference: "manual-numbers", level: 0 },
      children: [new TextRun(numbered[2].replace(/`/g, ""))],
    }));
    continue;
  }
  children.push(new Paragraph({ children: [new TextRun(line.replace(/`/g, ""))] }));
}

const thinRule = { style: BorderStyle.SINGLE, size: 4, color: "9CA3AF", space: 1 };
const document = new Document({
  styles: {
    default: { document: { run: { font: "Microsoft YaHei", size: 21, color: "1F2937" } } },
    paragraphStyles: [
      {
        id: "Title",
        name: "Title",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { font: "Microsoft YaHei", size: 38, bold: true, color: "111827" },
        paragraph: { spacing: { after: 360 }, alignment: AlignmentType.CENTER, outlineLevel: 0 },
      },
      {
        id: "Heading1",
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { font: "Microsoft YaHei", size: 29, bold: true, color: "1F4E78" },
        paragraph: { spacing: { before: 280, after: 140 }, border: { bottom: thinRule }, outlineLevel: 0 },
      },
      {
        id: "Heading2",
        name: "Heading 2",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { font: "Microsoft YaHei", size: 24, bold: true, color: "374151" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 },
      },
    ],
  },
  numbering: {
    config: [
      {
        reference: "manual-bullets",
        levels: [{
          level: 0,
          format: LevelFormat.BULLET,
          text: "•",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } },
        }],
      },
      {
        reference: "manual-numbers",
        levels: [{
          level: 0,
          format: LevelFormat.DECIMAL,
          text: "%1.",
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } },
        }],
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1134, right: 1134, bottom: 1134, left: 1134 },
      },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun("VGGT 模块一测试操作手册  ·  "), new TextRun({ children: [PageNumber.CURRENT] })],
        })],
      }),
    },
    children,
  }],
});

const buffer = await Packer.toBuffer(document);
await fs.writeFile(path.join(outputDirectory, "测试操作手册.docx"), buffer);
