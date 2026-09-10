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
testCases.getRange("A2:A4").clear({ applyTo: "contents" });
information.getRange("E13").formulas = [["=COUNTA('Test Cases测试用例'!A:A)-1"]];
information.getRange("E7").values = [["模块一（待小组确认）"]];
information.getRange("J7").values = [["课程作业"]];
information.getRange("E8").values = [["VGGT 几何坐标转换模块"]];
information.getRange("J8").values = [["【待填写：项目ID】"]];
information.getRange("E9").values = [["【待填写：拟制人】"]];
information.getRange("J9").values = [["【待填写：日期】"]];
information.getRange("E10").values = [["【待填写：评审人】"]];
information.getRange("J10").values = [["【待填写：日期】"]];
information.getRange("E11").values = [["【待填写：批准人】"]];
information.getRange("J11").values = [["【待填写：日期】"]];
information.getRange("B16").values = [["模块一填报副本。具体测试用例、输入、预期结果、实际结果与状态须由小组成员人工完成并据实填写。"]];
information.getRange("B20").values = [["2026.09.10"]];
information.getRange("C20").values = [["0.10"]];
information.getRange("D20").values = [["N/A"]];
information.getRange("E20").values = [["建立待人工填写副本；未生成计分测试用例"]];
information.getRange("K20").values = [["【待填写】"]];

workbook.recalculate();
const afterPreview = await workbook.render({
  sheetName: "Information文档信息",
  range: "A1:L43",
  scale: 1,
  format: "png",
});
await fs.writeFile(path.join(previewDirectory, "test_cases_after.png"), new Uint8Array(await afterPreview.arrayBuffer()));

const outputWorkbook = await SpreadsheetFile.exportXlsx(workbook);
await outputWorkbook.save(path.join(outputDirectory, "VGGT模块一测试用例清单_待人工填写.xlsx"));

const inspectResult = await workbook.inspect({
  kind: "region",
  sheetId: "Information文档信息",
  range: "B6:L20",
  maxChars: 6000,
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
