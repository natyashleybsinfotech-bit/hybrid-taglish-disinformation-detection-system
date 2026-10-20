// Section 3: Folder Structure
module.exports = function(h) {
  const { gap, body, h2, sectionBanner, folderRow,
    CONTENT_W, BLUE_DARK,
    Table, TableRow, WidthType } = h;

  function sec3() {
    return [
      sectionBanner("SECTION 3: PROJECT FOLDER STRUCTURE"), gap(),
      h2("3.1  Complete Folder Layout"),
      body("Create this exact folder and file structure before writing any code. Every file listed here has a declared purpose. Do not create files outside this structure without updating this document."),
      gap(),
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [3600, 5760],
        rows: [
          new TableRow({ children: [
            h.mkCell("Path", 3600, true, BLUE_DARK),
            h.mkCell("Purpose", 5760, true, BLUE_DARK),
          ]}),
          folderRow("taglish-detector/", "Root project directory", true),
          folderRow("taglish-detector/data/", "All raw and processed data files", true),
          folderRow("  data/raw/", "Original corpus CSV saved after first download", true),
          folderRow("  data/processed/", "Cleaned, filtered, and feature-extracted CSVs", true),
          folderRow("taglish-detector/src/", "All Python source files", true),
          folderRow("  src/data_loader.py", "Downloads corpus from HuggingFace, saves to data/raw/"),
          folderRow("  src/taglish_filter.py", "Applies Taglish detection logic, returns filtered DataFrame"),
          folderRow("  src/preprocessor.py", "Cleans text: removes URLs, emojis, duplicates, lowercases"),
          folderRow("  src/feature_extractor.py", "Runs Track A (DistilBERT) and Track B (rules), concatenates 775-dim vector"),
          folderRow("  src/trainer.py", "Splits data, trains 3 models, evaluates, saves best model"),
          folderRow("  src/evaluator.py", "Computes accuracy, precision, recall, F1, confusion matrix, inference time"),
          folderRow("  src/predictor.py", "Standalone prediction function used by FastAPI and by testing"),
          folderRow("taglish-detector/models/", "Serialized model artifacts", true),
          folderRow("  models/hybrid_model.pkl", "Best trained Logistic Regression model saved by joblib"),
          folderRow("  models/distilbert_embedder/", "Saved DistilBERT tokenizer and weights (save_pretrained)", true),
          folderRow("taglish-detector/api/", "FastAPI application files", true),
          folderRow("  api/main.py", "FastAPI app: defines POST /predict endpoint"),
          folderRow("  api/schemas.py", "Pydantic request and response models"),
          folderRow("taglish-detector/notebooks/", "Jupyter notebooks for exploration only (not production code)", true),
          folderRow("  notebooks/exploration.ipynb", "Dataset exploration, feature distribution analysis"),
          folderRow("taglish-detector/tests/", "Manual test scripts", true),
          folderRow("  tests/test_pipeline.py", "End-to-end smoke test: feeds sample text, checks JSON output"),
          folderRow("taglish-detector/config.py", "Central config: paths, model name, thresholds, feature lists"),
          folderRow("taglish-detector/requirements.txt", "Pinned package versions"),
          folderRow("taglish-detector/run_pipeline.py", "Single entry point: runs all stages in order from CLI"),
          folderRow("taglish-detector/README.md", "Setup and run instructions"),
        ],
      }),
      gap(),
    ];
  }

  return { sec3 };
};
