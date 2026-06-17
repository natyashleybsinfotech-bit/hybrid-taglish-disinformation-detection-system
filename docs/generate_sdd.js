const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType,
  LevelFormat, VerticalAlign, PageBreak
} = require('docx');
const fs = require('fs');

const FONT = "Calibri";
const CONTENT_W = 9360;
const MONO = "Courier New";
const BLUE_DARK  = "1B3A5C";
const BLUE_MID   = "2E6DA4";
const BLUE_LIGHT = "D6E8F7";
const GREY_LIGHT = "F4F6F8";
const GREY_MID   = "D0D7DE";
const GREEN_DARK = "1A5C3A";
const GREEN_LIGHT= "D6F0E0";
const ORANGE_DARK= "7A3B00";
const ORANGE_LIGHT="FFF0D6";
const RED_LIGHT  = "FDE8E8";
const RED_DARK   = "7A0000";

function gap(sz = 120) {
  return new Paragraph({ spacing: { after: sz }, children: [new TextRun("")] });
}
function hrule() {
  return new Paragraph({
    spacing: { before: 160, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: BLUE_MID, space: 1 } },
    children: [new TextRun("")],
  });
}
function body(text, centered = false) {
  return new Paragraph({
    alignment: centered ? AlignmentType.CENTER : AlignmentType.BOTH,
    spacing: { after: 140, line: 340 },
    children: [new TextRun({ text, font: FONT, size: 22 })],
  });
}
function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 480, after: 200 },
    children: [new TextRun({ text, font: FONT, size: 32, bold: true, color: BLUE_DARK })],
  });
}
function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 320, after: 160 },
    children: [new TextRun({ text, font: FONT, size: 26, bold: true, color: BLUE_MID })],
  });
}
function h3(text) {
  return new Paragraph({
    spacing: { before: 240, after: 100 },
    children: [new TextRun({ text, font: FONT, size: 23, bold: true, color: BLUE_DARK })],
  });
}
function bullet(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 80 },
    children: [new TextRun({ text, font: FONT, size: 22 })],
  });
}
function subbullet(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 1 },
    spacing: { after: 60 },
    children: [new TextRun({ text, font: FONT, size: 21 })],
  });
}
function code(text) {
  return new Paragraph({
    spacing: { after: 60 },
    indent: { left: 720 },
    children: [new TextRun({ text, font: MONO, size: 18, color: "2D6A2D" })],
  });
}
function mkCell(text, w, isHeader = false, fillColor = null, mono = false) {
  const border = { style: BorderStyle.SINGLE, size: 1, color: GREY_MID };
  return new TableCell({
    borders: { top: border, bottom: border, left: border, right: border },
    width: { size: w, type: WidthType.DXA },
    shading: fillColor ? { fill: fillColor, type: ShadingType.CLEAR } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    verticalAlign: VerticalAlign.TOP,
    children: [
      new Paragraph({
        alignment: AlignmentType.LEFT,
        children: [new TextRun({
          text, bold: isHeader,
          font: mono ? MONO : FONT,
          size: mono ? 18 : 21,
          color: isHeader ? "FFFFFF" : "000000",
        })],
      }),
    ],
  });
}
function sectionBanner(label) {
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [CONTENT_W],
    rows: [
      new TableRow({
        children: [
          new TableCell({
            borders: {
              top: { style: BorderStyle.SINGLE, size: 12, color: BLUE_MID },
              bottom: { style: BorderStyle.SINGLE, size: 12, color: BLUE_MID },
              left: { style: BorderStyle.SINGLE, size: 12, color: BLUE_MID },
              right: { style: BorderStyle.SINGLE, size: 12, color: BLUE_MID },
            },
            shading: { fill: BLUE_DARK, type: ShadingType.CLEAR },
            margins: { top: 120, bottom: 120, left: 200, right: 200 },
            width: { size: CONTENT_W, type: WidthType.DXA },
            children: [
              new Paragraph({
                alignment: AlignmentType.CENTER,
                children: [new TextRun({ text: label, font: FONT, size: 26, bold: true, color: "FFFFFF" })],
              }),
            ],
          }),
        ],
      }),
    ],
  });
}
function noteBox(title, text, fill, titleColor) {
  const border = { style: BorderStyle.SINGLE, size: 4, color: titleColor };
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [CONTENT_W],
    rows: [
      new TableRow({
        children: [
          new TableCell({
            borders: { top: border, bottom: border, left: border, right: border },
            shading: { fill, type: ShadingType.CLEAR },
            margins: { top: 100, bottom: 100, left: 160, right: 160 },
            width: { size: CONTENT_W, type: WidthType.DXA },
            children: [
              new Paragraph({
                spacing: { after: 60 },
                children: [new TextRun({ text: title, font: FONT, size: 22, bold: true, color: titleColor })],
              }),
              new Paragraph({
                alignment: AlignmentType.BOTH,
                children: [new TextRun({ text, font: FONT, size: 21 })],
              }),
            ],
          }),
        ],
      }),
    ],
  });
}
function folderRow(path, desc, isFolder = false) {
  return new TableRow({
    children: [
      mkCell(path, 3600, false, isFolder ? BLUE_LIGHT : null, true),
      mkCell(desc, 5760, false, isFolder ? BLUE_LIGHT : null),
    ],
  });
}

// Load section modules
const sections = require('./sdd_sections.js');

const doc = new Document({
  numbering: {
    config: [{
      reference: "bullets",
      levels: [
        { level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "\u25E6", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1080, hanging: 360 } } } },
      ],
    }],
  },
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 32, bold: true, font: FONT, color: BLUE_DARK }, paragraph: { spacing: { before: 480, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 26, bold: true, font: FONT, color: BLUE_MID }, paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 1 } },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1260, bottom: 1440, left: 1260 },
      },
    },
    children: sections.buildAll({
      gap, hrule, body, h1, h2, h3, bullet, subbullet, code,
      mkCell, sectionBanner, noteBox, folderRow,
      FONT, MONO, CONTENT_W, BLUE_DARK, BLUE_MID, BLUE_LIGHT,
      GREY_LIGHT, GREY_MID, GREEN_DARK, GREEN_LIGHT,
      ORANGE_DARK, ORANGE_LIGHT, RED_LIGHT, RED_DARK,
      Paragraph, TextRun, Table, TableRow, TableCell,
      AlignmentType, BorderStyle, WidthType, ShadingType, PageBreak,
    }),
  }],
});

Packer.toBuffer(doc).then(buf => {
  const outPath = require('path').join(__dirname, 'sdd.docx');
  fs.writeFileSync(outPath, buf);
  console.log("Done: " + outPath);
});
