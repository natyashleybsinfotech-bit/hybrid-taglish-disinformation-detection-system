// Sections 5 & 6: API Contract and Feature Lists
module.exports = function(h) {
  const { gap, h2, h3, body, mkCell, sectionBanner, code,
    FONT, MONO, CONTENT_W, BLUE_DARK, GREY_LIGHT, GREY_MID, RED_LIGHT,
    Paragraph, TextRun, Table, TableRow, TableCell,
    AlignmentType, BorderStyle, WidthType, ShadingType } = h;

  function sec5() {
    return [
      sectionBanner("SECTION 5: API CONTRACT"), gap(),
      h2("5.1  Endpoint: POST /predict"), gap(),
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2160, 7200],
        rows: [
          new TableRow({ children: [ mkCell("Field", 2160, true, BLUE_DARK), mkCell("Value", 7200, true, BLUE_DARK) ]}),
          new TableRow({ children: [ mkCell("Method", 2160, false, GREY_LIGHT), mkCell("POST", 7200) ]}),
          new TableRow({ children: [ mkCell("URL", 2160, false, GREY_LIGHT), mkCell("http://localhost:8000/predict", 7200, false, null, true) ]}),
          new TableRow({ children: [ mkCell("Content-Type", 2160, false, GREY_LIGHT), mkCell("application/json", 7200) ]}),
          new TableRow({ children: [ mkCell("Auth", 2160, false, GREY_LIGHT), mkCell("None (local prototype)", 7200) ]}),
        ],
      }),
      gap(),
      h3("Request Body"),
      code('{ "text": "Grabe itong balita, share agad bago matanggal! NOW NA!" }'),
      gap(),
      h3("Response Body (200 OK)"),
      code('{'),
      code('  "label": "Disinformation",'),
      code('  "confidence": 0.87,'),
      code('  "features": {'),
      code('    "code_switch_ratio": 0.43,'),
      code('    "particle_count": 2,'),
      code('    "punct_intensity": 0.08,'),
      code('    "caps_ratio": 0.25,'),
      code('    "repeat_char_count": 0,'),
      code('    "emotional_count": 1,'),
      code('    "urgency_count": 2'),
      code('  }'),
      code('}'),
      gap(),
      h3("Error Responses"),
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [1440, 3600, 4320],
        rows: [
          new TableRow({ children: [ mkCell("Status", 1440, true, BLUE_DARK), mkCell("Condition", 3600, true, BLUE_DARK), mkCell("Response Body", 4320, true, BLUE_DARK) ]}),
          new TableRow({ children: [ mkCell("422", 1440, false, RED_LIGHT), mkCell("Request body missing 'text' field or wrong type", 3600), mkCell('{"detail": "validation error"}', 4320, false, null, true) ]}),
          new TableRow({ children: [ mkCell("500", 1440, false, RED_LIGHT), mkCell("Model not loaded or pipeline error", 3600), mkCell('{"detail": "prediction failed"}', 4320, false, null, true) ]}),
        ],
      }),
      gap(),
      h2("5.2  Endpoint: GET /health"),
      code('GET http://localhost:8000/health'),
      code('Response: { "status": "ok", "model_loaded": true }'),
      gap(),
    ];
  }

  function monoBlock(text) {
    const border = { style: BorderStyle.SINGLE, size: 2, color: GREY_MID };
    return new Table({
      width: { size: CONTENT_W, type: WidthType.DXA },
      columnWidths: [CONTENT_W],
      rows: [
        new TableRow({ children: [
          new TableCell({
            borders: { top: border, bottom: border, left: border, right: border },
            shading: { fill: GREY_LIGHT, type: ShadingType.CLEAR },
            margins: { top: 100, bottom: 100, left: 160, right: 160 },
            width: { size: CONTENT_W, type: WidthType.DXA },
            children: [
              new Paragraph({
                children: [new TextRun({ text, font: MONO, size: 19 })],
              }),
            ],
          }),
        ]}),
      ],
    });
  }

  function sec6() {
    return [
      sectionBanner("SECTION 6: DECLARED FEATURE LISTS"), gap(),
      h2("6.1  Filipino Particles"),
      body("These are the tokens the filter and feature extractor treat as Filipino-language markers. Expand this list as needed, but update config.py first."),
      gap(),
      monoBlock("ba, kasi, naman, nga, pa, na, daw, raw, lang, po, ate, kuya, pala, eh, talaga, sobra, grabe, ay, hay, nako, sana, kung, bakit, hindi, pero, at, ng, ang, mga, yung, ito, iyon, siya, kami, tayo, nila"),
      gap(),
      h2("6.2  Urgency Phrases"),
      monoBlock("share agad, now na, bago matanggal, breaking, grabe ito, pakishere, i-share na, urgent, bilisan, asap, huwag palampasin, pinakamahalagang, tandaan ninyo, hindi dapat malaman, itago, huwag tanggalin"),
      gap(),
      h2("6.3  Emotional Words"),
      monoBlock("galit, takot, kawawa, nakakalungkot, nakakatakot, nakakainis, nakakagulat, nakakaawa, nakakatuwa, nakakaloka, baliw, gago, putangina, hayop, mahal, masakit, nasaktan, iyak, luha, saya, masaya, malungkot, galit na galit, nagagalit, natatakot, naiinis, nagulat, nagulantang"),
      gap(),
    ];
  }

  return { sec5, sec6 };
};
