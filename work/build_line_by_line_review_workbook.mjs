import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(".");
const reviewDir = path.join(root, "outputs", "qa", "line_by_line_jp_cn_review");
const inputJson = path.join(reviewDir, "review_rows.json");
const outputXlsx = path.join(reviewDir, "MuvLuv_TDA01-03_JP_CN_逐条核对_进行中.xlsx");

const headers = [
  "id",
  "jp字段",
  "cn字段",
  "是否正确",
  "如果否，打算怎么修改",
  "理由",
  "章节",
  "序号",
  "脚本文件",
  "审计提示",
];

function rowsForSheet(allRows, title) {
  return allRows
    .filter((row) => row.title === title)
    .map((row) => [
      row.id ?? "",
      row.jp ?? "",
      row.cn ?? "",
      row["是否正确"] ?? "",
      row["如果否，打算怎么修改"] ?? "",
      row["理由"] ?? "",
      row.title ?? "",
      row.seq ?? "",
      row["脚本文件"] ?? "",
      row["审计提示"] ?? "",
    ]);
}

function buildSummaryRows(allRows) {
  const titles = ["TDA01", "TDA02", "TDA03"];
  const rows = [["章节", "总行数", "已判定是", "已判定否", "待核对", "有审计提示"]];
  for (const title of titles) {
    const subset = allRows.filter((row) => row.title === title);
    rows.push([
      title,
      subset.length,
      subset.filter((row) => row["是否正确"] === "是").length,
      subset.filter((row) => row["是否正确"] === "否").length,
      subset.filter((row) => row["是否正确"] === "待核对").length,
      subset.filter((row) => row["审计提示"]).length,
    ]);
  }
  return rows;
}

function styleSheet(sheet, rowCount) {
  sheet.freezePanes.freezeRows(1);
  sheet.getRange("A1:J1").format = {
    fill: "#1F4E78",
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
  };
  sheet.getRange(`A1:J${rowCount}`).format = {
    borders: { preset: "all", style: "thin", color: "#D9E2F3" },
    wrapText: true,
  };
  const widths = [130, 520, 520, 90, 320, 360, 80, 70, 340, 360];
  widths.forEach((width, index) => {
    sheet.getRangeByIndexes(0, index, rowCount, 1).format.columnWidthPx = width;
  });
}

const data = JSON.parse(await fs.readFile(inputJson, "utf8"));
await fs.mkdir(reviewDir, { recursive: true });
console.log(`loaded rows=${data.length}`);

const workbook = Workbook.create();

const summary = workbook.worksheets.add("说明与进度");
const summaryRows = [
  ["Muv-Luv TDA01-03 JP/CN 逐条核对表（进行中）"],
  ["规则"],
  ["只以 jp 字段为准核对 cn 字段；不使用英文作为参考。jp 为空时 cn 必须为空。jp 是语气/标点时 cn 也必须对应语气/标点。正常台词需语义对应、术语固定、语言通顺。"],
  ["状态说明"],
  ["“待核对”表示该行还没有完成逐条人工语义判断，不是最终结论。最终版会把每行都改成“是”或“否”。"],
  [""],
  ...buildSummaryRows(data),
];
summary.getRangeByIndexes(0, 0, summaryRows.length, 6).values = summaryRows.map((row) => {
  const padded = [...row];
  while (padded.length < 6) padded.push("");
  return padded;
});
summary.getRange("A1:F1").merge();
summary.getRange("A1").format = { fill: "#1F4E78", font: { bold: true, color: "#FFFFFF" } };
summary.getRange("A2:F5").format = { wrapText: true };
summary.getRange("A7:F7").format = { fill: "#D9EAF7", font: { bold: true } };
summary.getRange("A1:F10").format = {
  borders: { preset: "all", style: "thin", color: "#D9E2F3" },
  wrapText: true,
};
[180, 100, 100, 100, 100, 120].forEach((width, index) => {
  summary.getRangeByIndexes(0, index, 10, 1).format.columnWidthPx = width;
});

for (const title of ["TDA01", "TDA02", "TDA03"]) {
  const rows = rowsForSheet(data, title);
  const sheet = workbook.worksheets.add(title);
  sheet.getRangeByIndexes(0, 0, rows.length + 1, headers.length).values = [headers, ...rows];
  styleSheet(sheet, rows.length + 1);
}

for (const sheetName of ["说明与进度", "TDA01", "TDA02", "TDA03"]) {
  console.log(`render preview ${sheetName}`);
  const preview = await workbook.render({
    sheetName,
    range: sheetName === "说明与进度" ? "A1:F12" : "A1:F30",
    scale: 1,
    format: "png",
  });
  await fs.writeFile(
    path.join(reviewDir, `${sheetName}_preview.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

console.log("export xlsx");
const output = await SpreadsheetFile.exportXlsx(workbook);
console.log("save xlsx");
await output.save(outputXlsx);
console.log(outputXlsx);
