// Section 2: System Architecture
module.exports = function(h) {
  const { gap, body, h2, mkCell, sectionBanner, noteBox,
    CONTENT_W, BLUE_DARK, BLUE_LIGHT, GREY_LIGHT,
    Table, TableRow, WidthType, ORANGE_LIGHT, ORANGE_DARK } = h;

  function sec2() {
    return [
      sectionBanner("SECTION 2: SYSTEM ARCHITECTURE"), gap(),
      h2("2.1  Three-Layer Architecture"),
      body("The system is divided into three completely separate layers. Each layer has one job. No layer should reach into another layer's internal logic. Communication between layers happens only through defined inputs and outputs."),
      gap(),
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [2160, 2400, 4800],
        rows: [
          new TableRow({ children: [
            mkCell("Layer", 2160, true, BLUE_DARK),
            mkCell("Name", 2400, true, BLUE_DARK),
            mkCell("Responsibility", 4800, true, BLUE_DARK),
          ]}),
          new TableRow({ children: [
            mkCell("Layer 1", 2160, false, BLUE_LIGHT),
            mkCell("Data and Feature Layer", 2400),
            mkCell("Load corpus, filter for Taglish, clean text, extract DistilBERT embeddings and 7 linguistic features, fuse into 775-dim vector, split dataset.", 4800),
          ]}),
          new TableRow({ children: [
            mkCell("Layer 2", 2160, false, BLUE_LIGHT),
            mkCell("Machine Learning Layer", 2400),
            mkCell("Train three model configurations on the fused vectors, evaluate using all declared metrics, serialize the best model to disk.", 4800),
          ]}),
          new TableRow({ children: [
            mkCell("Layer 3", 2160, false, BLUE_LIGHT),
            mkCell("API Layer", 2400),
            mkCell("Load the serialized model, expose a POST /predict endpoint, receive raw text, run the full pipeline, return a JSON result.", 4800),
          ]}),
        ],
      }),
      gap(),
      h2("2.2  Full Data Flow (End to End)"),
      body("Follow this flow exactly. Each arrow represents a defined handoff between components."),
      gap(),
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [3600, 720, 5040],
        rows: [
          new TableRow({ children: [
            mkCell("FROM", 3600, true, BLUE_DARK),
            mkCell("", 720, true, BLUE_DARK),
            mkCell("TO", 5040, true, BLUE_DARK),
          ]}),
          new TableRow({ children: [
            mkCell("HuggingFace Hub (jcblaise/fake_news_filipino)", 3600, false, GREY_LIGHT),
            mkCell("->", 720, false, GREY_LIGHT),
            mkCell("data_loader.py: loads raw DataFrame with text and label columns", 5040),
          ]}),
          new TableRow({ children: [
            mkCell("data_loader.py: raw DataFrame", 3600, false, GREY_LIGHT),
            mkCell("->", 720, false, GREY_LIGHT),
            mkCell("taglish_filter.py: retains only rows with both English and Filipino tokens", 5040),
          ]}),
          new TableRow({ children: [
            mkCell("taglish_filter.py: filtered DataFrame", 3600, false, GREY_LIGHT),
            mkCell("->", 720, false, GREY_LIGHT),
            mkCell("preprocessor.py: removes URLs, emojis, duplicates, lowercases text", 5040),
          ]}),
          new TableRow({ children: [
            mkCell("preprocessor.py: clean text column", 3600, false, GREY_LIGHT),
            mkCell("->", 720, false, GREY_LIGHT),
            mkCell("feature_extractor.py (Track A): DistilBERT tokenizer and model produce 768-dim CLS vector", 5040),
          ]}),
          new TableRow({ children: [
            mkCell("preprocessor.py: clean text column", 3600, false, GREY_LIGHT),
            mkCell("->", 720, false, GREY_LIGHT),
            mkCell("feature_extractor.py (Track B): regex and rule functions produce 7 scalar values", 5040),
          ]}),
          new TableRow({ children: [
            mkCell("Track A (768-dim) + Track B (7-dim)", 3600, false, GREY_LIGHT),
            mkCell("->", 720, false, GREY_LIGHT),
            mkCell("feature_extractor.py: numpy.concatenate produces single 775-dim vector per sample", 5040),
          ]}),
          new TableRow({ children: [
            mkCell("775-dim matrix + labels", 3600, false, GREY_LIGHT),
            mkCell("->", 720, false, GREY_LIGHT),
            mkCell("trainer.py: stratified 70/15/15 split, trains 3 model configs, evaluates, saves best", 5040),
          ]}),
          new TableRow({ children: [
            mkCell("trainer.py: saved model artifact (.pkl via joblib)", 3600, false, GREY_LIGHT),
            mkCell("->", 720, false, GREY_LIGHT),
            mkCell("main.py (FastAPI): loads artifact at startup, serves POST /predict endpoint", 5040),
          ]}),
          new TableRow({ children: [
            mkCell("POST /predict receives raw Taglish text", 3600, false, GREY_LIGHT),
            mkCell("->", 720, false, GREY_LIGHT),
            mkCell("preprocessor + feature_extractor run inline, model returns JSON response", 5040),
          ]}),
        ],
      }),
      gap(),
      noteBox("CRITICAL RULE: One-Way Data Flow", "Data always moves forward through this pipeline. The API layer calls the feature extractor. The feature extractor calls the preprocessor. The preprocessor calls the data loader. No module calls backwards. This keeps the system testable and each component replaceable without breaking the others.", ORANGE_LIGHT, ORANGE_DARK),
      gap(),
    ];
  }

  return { sec2 };
};
