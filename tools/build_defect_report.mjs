import fs from "node:fs/promises";
import path from "node:path";
import {
  AlignmentType,
  BorderStyle,
  Document,
  Footer,
  Header,
  HeadingLevel,
  PageBreak,
  PageNumber,
  Packer,
  Paragraph,
  ShadingType,
  Table,
  TableCell,
  TableRow,
  TextRun,
  VerticalAlign,
  WidthType,
} from "docx";

const [outputPath] = process.argv.slice(2);
if (!outputPath) {
  throw new Error("Usage: node build_defect_report.mjs <output.docx>");
}

const COLORS = {
  navy: "17365D",
  blue: "1F4E78",
  midBlue: "5B9BD5",
  lightBlue: "DDEBF7",
  paleBlue: "EAF2F8",
  grey: "E7E6E6",
  lightGrey: "F2F2F2",
  text: "222222",
  white: "FFFFFF",
  red: "C00000",
  orange: "F4B183",
};

const FONT = "Microsoft YaHei";
const border = { style: BorderStyle.SINGLE, size: 4, color: "A6A6A6" };
const tableBorders = { top: border, bottom: border, left: border, right: border, insideHorizontal: border, insideVertical: border };

function run(text, options = {}) {
  return new TextRun({ text, font: FONT, size: options.size ?? 21, bold: options.bold, color: options.color ?? COLORS.text, italics: options.italics });
}

function para(text = "", options = {}) {
  const children = Array.isArray(text) ? text : [run(text, options)];
  return new Paragraph({
    children,
    alignment: options.alignment,
    spacing: { before: options.before ?? 0, after: options.after ?? 120, line: options.line ?? 320 },
    indent: options.indent ? { firstLine: options.indent } : undefined,
    keepNext: options.keepNext,
  });
}

function heading(text, level = 1) {
  return new Paragraph({
    text,
    heading: level === 1 ? HeadingLevel.HEADING_1 : level === 2 ? HeadingLevel.HEADING_2 : HeadingLevel.HEADING_3,
    spacing: { before: level === 1 ? 260 : 180, after: 100 },
    keepNext: true,
  });
}

function cell(text = "", options = {}) {
  const content = Array.isArray(text) ? text : [para(text, { after: 0, line: 280, ...options })];
  return new TableCell({
    children: content,
    width: options.width ? { size: options.width, type: WidthType.DXA } : undefined,
    columnSpan: options.columnSpan,
    verticalAlign: options.verticalAlign ?? VerticalAlign.CENTER,
    shading: options.fill ? { fill: options.fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 90, bottom: 90, left: 110, right: 110 },
  });
}

function labelCell(text, width = 1700) {
  return cell([para([run(text, { bold: true, color: COLORS.navy })], { after: 0, line: 270 })], { fill: COLORS.lightBlue, width });
}

function blankCell(width) {
  return cell("", { width });
}

function keyValueTable(rows, widths = [1700, 3000, 1700, 3000]) {
  return new Table({
    width: { size: 9200, type: WidthType.DXA },
    columnWidths: widths,
    borders: tableBorders,
    rows: rows.map((r) => new TableRow({
      cantSplit: true,
      children: r.length === 2
        ? [labelCell(r[0], widths[0]), cell(r[1], { width: widths.slice(1).reduce((a, b) => a + b, 0), columnSpan: 3 })]
        : [labelCell(r[0], widths[0]), cell(r[1], { width: widths[1] }), labelCell(r[2], widths[2]), cell(r[3], { width: widths[3] })],
    })),
  });
}

function bullet(text) {
  return new Paragraph({
    children: [run(text)],
    bullet: { level: 0 },
    spacing: { after: 70, line: 310 },
  });
}

function statusBand() {
  return new Table({
    width: { size: 9200, type: WidthType.DXA },
    columnWidths: [2300, 2300, 2300, 2300],
    borders: tableBorders,
    rows: [new TableRow({ children: [
      cell([para([run("缺陷编号", { bold: true, color: COLORS.white })], { alignment: AlignmentType.CENTER, after: 0 })], { fill: COLORS.blue, width: 2300 }),
      cell([para([run("严重程度", { bold: true, color: COLORS.white })], { alignment: AlignmentType.CENTER, after: 0 })], { fill: COLORS.blue, width: 2300 }),
      cell([para([run("优先级", { bold: true, color: COLORS.white })], { alignment: AlignmentType.CENTER, after: 0 })], { fill: COLORS.blue, width: 2300 }),
      cell([para([run("当前状态", { bold: true, color: COLORS.white })], { alignment: AlignmentType.CENTER, after: 0 })], { fill: COLORS.blue, width: 2300 }),
    ] }), new TableRow({ children: [
      cell([para([run("DEF-M1-001", { bold: true })], { alignment: AlignmentType.CENTER, after: 0 })], { width: 2300 }),
      cell([para([run("高", { bold: true, color: COLORS.red })], { alignment: AlignmentType.CENTER, after: 0 })], { width: 2300, fill: "FCE4D6" }),
      cell([para([run("高", { bold: true, color: COLORS.red })], { alignment: AlignmentType.CENTER, after: 0 })], { width: 2300, fill: "FCE4D6" }),
      cell([para([run("已确认，待修复", { bold: true })], { alignment: AlignmentType.CENTER, after: 0 })], { width: 2300, fill: "FFF2CC" }),
    ] })],
  });
}

const body = [];

// Cover page
body.push(
  para("软件名称：VGGT（模块一：坐标转换模块）", { alignment: AlignmentType.CENTER, size: 24, before: 900, after: 560 }),
  para([run("VGGT 模块一", { size: 40, bold: true, color: COLORS.navy })], { alignment: AlignmentType.CENTER, after: 120 }),
  para([run("测试缺陷报告书", { size: 52, bold: true, color: COLORS.blue })], { alignment: AlignmentType.CENTER, after: 720 }),
  statusBand(),
  para("", { after: 620 }),
  new Table({
    width: { size: 7800, type: WidthType.DXA },
    alignment: AlignmentType.CENTER,
    columnWidths: [1600, 1400, 3200, 1600],
    borders: tableBorders,
    rows: [
      new TableRow({ children: [
        cell([para([run("日期", { bold: true, color: COLORS.white })], { alignment: AlignmentType.CENTER, after: 0 })], { fill: COLORS.blue, width: 1600 }),
        cell([para([run("版本", { bold: true, color: COLORS.white })], { alignment: AlignmentType.CENTER, after: 0 })], { fill: COLORS.blue, width: 1400 }),
        cell([para([run("修订说明", { bold: true, color: COLORS.white })], { alignment: AlignmentType.CENTER, after: 0 })], { fill: COLORS.blue, width: 3200 }),
        cell([para([run("编写人", { bold: true, color: COLORS.white })], { alignment: AlignmentType.CENTER, after: 0 })], { fill: COLORS.blue, width: 1600 }),
      ] }),
      new TableRow({ children: [
        cell("2026-09-10", { width: 1600 }), cell("V1.0", { width: 1400 }), cell("首次建立模块一缺陷报告", { width: 3200 }), blankCell(1600),
      ] }),
    ],
  }),
  para("说明：报告仅记录已实际复现的测试事实；人员、修复和复测信息未取得时保持空白。", { alignment: AlignmentType.CENTER, color: "666666", size: 18, before: 720, italics: true }),
  new Paragraph({ children: [new PageBreak()] }),
);

body.push(
  heading("1 引言", 1),
  heading("1.1 编写目的", 2),
  para("记录 VGGT 模块一坐标转换功能测试中发现并复现的缺陷，为开发定位、修复、回归测试和课程交付提供可追溯依据。", { indent: 420 }),
  heading("1.2 项目背景", 2),
  keyValueTable([
    ["被测软件", "VGGT（Visual Geometry Grounded Transformer）", "测试模块", "vggt.utils.geometry"],
    ["项目提出方", "", "开发方/小组", ""],
    ["预期用户/单位", "", "测试阶段", "模块一功能测试"],
  ]),
  heading("1.3 术语与定义", 2),
  keyValueTable([
    ["术语", "说明"],
    ["深度图", "每个像素记录场景深度值的二维数组；多帧输入可表示为 (S,H,W) 或 (S,H,W,1)。"],
    ["反投影", "依据深度、相机内参和外参，将图像像素转换为三维空间坐标。"],
    ["S / H / W", "分别表示帧数、图像高度和图像宽度。"],
  ], [1700, 7500, 0, 0]),
  heading("1.4 参考资料", 2),
  bullet("《附录2：缺陷报告模板》"),
  bullet("vggt-main/vggt/utils/geometry.py（Git 提交 4f092034a0673e4e9d257376d3513cfb629ca3f9）"),
  bullet("VGGT模块一测试用例清单_待人工填写.xlsx，测试用例 M1-GEO-016"),
  bullet("test_results/module1/DEF-M1-001_reproduction.txt"),
  heading("2 测试环境", 1),
  heading("2.1 硬件环境", 2),
  keyValueTable([
    ["处理器", "12th Gen Intel(R) Core(TM) i7-12700H", "内存", "31.8 GB"],
    ["显卡", "NVIDIA GeForce RTX 3070 Laptop GPU", "驱动版本", "32.0.16.1047"],
  ]),
  heading("2.2 软件环境", 2),
  keyValueTable([
    ["操作系统", "Windows 11 家庭中文版（10.0.26100）", "Conda 环境", "Pytorch_Vggt"],
    ["Python", "3.10.20", "NumPy", "2.2.6"],
    ["PyTorch", "2.8.0+cu128", "CUDA", "12.8"],
    ["被测文件", "vggt-main/vggt/utils/geometry.py", "测试时间", "2026-09-10 18:35:50 +08:00"],
  ]),
  new Paragraph({ children: [new PageBreak()] }),
);

body.push(
  heading("3 模块一坐标转换测试", 1),
  heading("3.1 被测软件", 2),
  para("本次测试对象为 VGGT 的坐标转换工具模块 vggt.utils.geometry，重点核对深度图反投影接口对其文档所声明输入形状的兼容性。", { indent: 420 }),
  heading("3.2 测试策略", 2),
  bullet("采用等价类方法覆盖文档声明的两类有效输入：(S,H,W) 与 (S,H,W,1)。"),
  bullet("采用最小尺寸和非单位宽度两组 (S,H,W) 输入，区分维度被误删与非法 squeeze 两种失败表现。"),
  bullet("使用相同内外参和四维输入执行对照，排除公共输入或矩阵计算错误。"),
  heading("3.3 测试步骤", 2),
  para("1. 在 Pytorch_Vggt 环境中导入 unproject_depth_map_to_point_map。\n2. 构造两帧单位内参、单位外参及 shape=(2,1,1) 的三维深度图。\n3. 调用函数并记录异常。\n4. 将宽度改为 2，构造 shape=(2,1,2) 的三维深度图，再次调用并记录异常。\n5. 在相同数据末尾增加通道维，构造 shape=(2,1,2,1) 的四维对照输入并校验返回形状和坐标值。"),
  heading("3.4 缺陷记录", 2),
  heading("3.4.1 unproject_depth_map_to_point_map", 3),
  statusBand(),
  para("", { after: 100 }),
  keyValueTable([
    ["测试人员", "", "测试时间", "2026-09-10 18:35:50 +08:00"],
    ["功能模块名称", "坐标转换模块", "功能编号", "geometry.unproject"],
    ["测试项编号", "M1-GEO-016", "关联用例", "M1-GEO-016"],
    ["测试需求", "函数应支持文档声明的 (S,H,W) 和 (S,H,W,1) 两种深度图输入。"],
    ["严重程度", "高", "优先级", "高"],
    ["缺陷状态", "已确认，待修复", "指派给", ""],
    ["抄送给", "", "发现版本", "4f092034a0673e4e9d257376d3513cfb629ca3f9"],
    ["缺陷标题", "unproject_depth_map_to_point_map 无法处理文档声明支持的 (S,H,W) 深度图"],
  ]),
  para("", { after: 80 }),
  keyValueTable([
    ["详细描述", "函数文档明确声明 depth_map 可为 (S,H,W,1) 或 (S,H,W)，但实现对每帧数据无条件执行 squeeze(-1)。三维输入下，W=1 时宽度维被删除，W>1 时 squeeze 直接抛出异常，因此文档声明的全部 (S,H,W) 输入都无法正常处理。"],
    ["复现步骤", "1. 构造 depth_map=np.ones((2,1,1))、两帧单位内参和单位外参。\n2. 调用 unproject_depth_map_to_point_map。\n3. 记录 ValueError。\n4. 将 depth_map 改为 np.ones((2,1,2))，再次调用并记录另一 ValueError。\n5. 将输入改为 np.ones((2,1,2,1)) 作为对照，函数成功返回。"],
    ["预期结果", "(S,H,W) 与 (S,H,W,1) 两种输入均应成功，返回 shape=(S,H,W,3) 的世界坐标点图；相同深度数据的两种表示应产生等价结果。"],
    ["实际结果", "shape=(2,1,1) 时抛出：ValueError: not enough values to unpack (expected 2, got 1)。\nshape=(2,1,2) 时抛出：ValueError: cannot select an axis to squeeze out which has size not equal to one。\nshape=(2,1,2,1) 的对照输入成功，返回 shape=(2,1,2,3)。"],
    ["附件", "test_results/module1/DEF-M1-001_reproduction.txt"],
    ["关联缺陷", ""],
    ["备注", "定位位置：geometry.py 中 depth_map[frame_idx].squeeze(-1)。临时规避方式：调用方为三维深度图补充末尾通道维，转换为 (S,H,W,1)。本次未修改被测源码。"],
  ]),
  new Paragraph({ children: [new PageBreak()] }),
);

body.push(
  heading("3.4.2 缺陷处理记录", 3),
  para("以下字段须在开发完成修复及测试人员完成回归测试后填写，本报告当前不作推定。", { color: "666666", italics: true }),
  keyValueTable([
    ["解决方案", "", "解决人员", ""],
    ["解决日期", "", "解决版本/构建", ""],
    ["详细解决方案", ""],
    ["关闭人员", "", "关闭/复测日期", ""],
    ["复测结果", ""],
  ]),
  heading("3.4.3 修复建议（非处理结果）", 3),
  para("仅在原始 depth_map 为四维且末尾通道数为 1 时删除通道维；三维输入应直接保留每帧二维 H×W 数据。同时建议增加输入维数、通道数、帧数及内外参数量一致性的显式校验，并为两种有效形状补充自动化回归测试。", { indent: 420 }),
  heading("3.5 测试结果分析与结论", 2),
  para("本次执行确认 1 个高严重度、高优先级缺陷。关联用例 M1-GEO-016 对文档声明的 (S,H,W) 输入执行失败，而四维 (S,H,W,1) 对照输入正常，说明问题集中在输入维度处理逻辑。当前该功能不能判定为通过；需完成代码修复后，重新执行两类有效输入、边界尺寸和多帧一致性回归测试，再填写处理记录并决定是否关闭缺陷。", { indent: 420 }),
  para("报告状态：已确认，待修复与复测。", { bold: true, color: COLORS.red, before: 180 }),
);

const doc = new Document({
  creator: "",
  title: "VGGT模块一测试缺陷报告_DEF-M1-001",
  description: "依据附录2缺陷报告模板编制的模块一缺陷报告",
  styles: {
    default: {
      document: { run: { font: FONT, size: 21, color: COLORS.text }, paragraph: { spacing: { line: 320 } } },
      title: { run: { font: FONT, size: 52, bold: true, color: COLORS.blue } },
      heading1: { run: { font: FONT, size: 30, bold: true, color: COLORS.navy }, paragraph: { spacing: { before: 260, after: 100 }, keepNext: true } },
      heading2: { run: { font: FONT, size: 26, bold: true, color: COLORS.blue }, paragraph: { spacing: { before: 180, after: 90 }, keepNext: true } },
      heading3: { run: { font: FONT, size: 23, bold: true, color: COLORS.blue }, paragraph: { spacing: { before: 140, after: 80 }, keepNext: true } },
    },
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1080, right: 1150, bottom: 1050, left: 1150, header: 500, footer: 500 },
      },
    },
    headers: { default: new Header({ children: [para("VGGT 模块一测试缺陷报告", { alignment: AlignmentType.RIGHT, color: "7F7F7F", size: 17, after: 0 })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [run("第 ", { size: 17, color: "7F7F7F" }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 17, color: "7F7F7F" }), run(" 页", { size: 17, color: "7F7F7F" })] })] }) },
    children: body,
  }],
});

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.writeFile(outputPath, await Packer.toBuffer(doc));
console.log(`Created ${outputPath}`);
