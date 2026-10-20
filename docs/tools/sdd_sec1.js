// Section 1 & Cover Page
module.exports = function(h) {
  const { gap, hrule, body, h2, bullet, sectionBanner, noteBox,
    FONT, BLUE_DARK, BLUE_MID,
    Paragraph, TextRun, PageBreak } = h;

  function coverPage() {
    return [
      gap(1440),
      new Paragraph({
        alignment: h.AlignmentType.CENTER, spacing: { after: 80 },
        children: [new TextRun({ text: "SYSTEM DESIGN DOCUMENT", font: FONT, size: 48, bold: true, color: BLUE_DARK })],
      }),
      new Paragraph({
        alignment: h.AlignmentType.CENTER, spacing: { after: 120 },
        children: [new TextRun({ text: "Version 1.0  |  Pre-Development Blueprint", font: FONT, size: 24, color: BLUE_MID })],
      }),
      hrule(), gap(80),
      new Paragraph({
        alignment: h.AlignmentType.CENTER, spacing: { after: 60 },
        children: [new TextRun({ text: "A Hybrid DistilBERT-Logistic Regression Model", font: FONT, size: 28, bold: true, color: BLUE_DARK })],
      }),
      new Paragraph({
        alignment: h.AlignmentType.CENTER, spacing: { after: 60 },
        children: [new TextRun({ text: "for Taglish Disinformation Detection", font: FONT, size: 28, bold: true, color: BLUE_DARK })],
      }),
      new Paragraph({
        alignment: h.AlignmentType.CENTER, spacing: { after: 60 },
        children: [new TextRun({ text: "Using Linguistic and Contextual Features", font: FONT, size: 28, bold: true, color: BLUE_DARK })],
      }),
      gap(160),
      new Paragraph({
        alignment: h.AlignmentType.CENTER, spacing: { after: 60 },
        children: [new TextRun({ text: "Kamilan, Diana F.  |  Naty, Ashley B.  |  Gagarin, Matt Dwayne S.  |  Villanueva, Aaron Zeke R.", font: FONT, size: 22 })],
      }),
      new Paragraph({
        alignment: h.AlignmentType.CENTER, spacing: { after: 60 },
        children: [new TextRun({ text: "BSINFOTECH 3C  |  Capstone Project 1  |  May 2026", font: FONT, size: 22 })],
      }),
      gap(1440),
      new Paragraph({ children: [new PageBreak()] }),
    ];
  }

  function sec1() {
    return [
      sectionBanner("SECTION 1: DOCUMENT PURPOSE AND SCOPE"), gap(),
      h2("1.1  What This Document Is"),
      body("This System Design Document (SDD) is the authoritative blueprint for the Taglish Disinformation Detector. It defines every component of the system before a single line of code is written. Every team member must read this document in full before touching the codebase. Any deviation from this design during development must be discussed and updated here first."),
      gap(),
      h2("1.2  Current Development Scope"),
      noteBox("SCOPE FOR THIS PHASE", "This phase uses ONLY the Fake News Filipino corpus (jcblaise/fake_news_filipino from HuggingFace). Manual scraping, CalamanCy, and the Chrome Extension are deferred. The goal is to demonstrate that DistilBERT and Logistic Regression function correctly as a hybrid classification pipeline. Everything built here will be the foundation that the full system extends.", h.GREEN_LIGHT, h.GREEN_DARK),
      gap(),
      h2("1.3  What This Phase Produces"),
      bullet("A cleaned and Taglish-filtered version of the Fake News Filipino dataset"),
      bullet("Seven extracted linguistic and stylistic feature values per text sample"),
      bullet("A 768-dimensional DistilBERT CLS embedding per text sample"),
      bullet("A fused 775-dimensional feature vector per text sample"),
      bullet("Three trained and evaluated models: TF-IDF + LR, DistilBERT-only, Hybrid"),
      bullet("A serialized hybrid model saved to disk using joblib"),
      bullet("A FastAPI backend with a working POST /predict endpoint"),
      bullet("A JSON response containing: label, confidence score, and 7 feature values"),
      gap(),
    ];
  }

  return { coverPage, sec1 };
};
