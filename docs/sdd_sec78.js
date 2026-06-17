// Sections 7 & 8: Build Order and Rules
module.exports = function(h) {
  const { gap, body, h2, bullet, code, mkCell, sectionBanner, noteBox,
    CONTENT_W, BLUE_DARK, BLUE_LIGHT,
    ORANGE_LIGHT, ORANGE_DARK,
    Table, TableRow, WidthType } = h;

  function sec7() {
    return [
      sectionBanner("SECTION 7: BUILD ORDER AND DEPENDENCIES"), gap(),
      h2("7.1  Strict Build Order"),
      body("Build and test each file completely before starting the next one. Do not build files out of order. Each file depends on the ones above it being correct."),
      gap(),
      new Table({
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [720, 3240, 2880, 2520],
        rows: [
          new TableRow({ children: [
            mkCell("Step", 720, true, BLUE_DARK), mkCell("File to Build", 3240, true, BLUE_DARK),
            mkCell("Depends On", 2880, true, BLUE_DARK), mkCell("Done When", 2520, true, BLUE_DARK),
          ]}),
          new TableRow({ children: [
            mkCell("1", 720, false, BLUE_LIGHT), mkCell("config.py", 3240),
            mkCell("Nothing", 2880), mkCell("All constants are importable without error", 2520),
          ]}),
          new TableRow({ children: [
            mkCell("2", 720, false, BLUE_LIGHT), mkCell("src/data_loader.py", 3240),
            mkCell("config.py, HuggingFace (public dataset)", 2880), mkCell("corpus.csv exists in data/raw/ with correct columns", 2520),
          ]}),
          new TableRow({ children: [
            mkCell("3", 720, false, BLUE_LIGHT), mkCell("src/taglish_filter.py", 3240),
            mkCell("data_loader.py, config.py", 2880), mkCell("Prints retained and discarded counts without error", 2520),
          ]}),
          new TableRow({ children: [
            mkCell("4", 720, false, BLUE_LIGHT), mkCell("src/preprocessor.py", 3240),
            mkCell("taglish_filter.py", 2880), mkCell("clean_text column is present and URLs/emojis are gone", 2520),
          ]}),
          new TableRow({ children: [
            mkCell("5", 720, false, BLUE_LIGHT), mkCell("src/feature_extractor.py", 3240),
            mkCell("preprocessor.py, config.py, transformers, torch", 2880), mkCell("features.csv has 775 columns plus label column", 2520),
          ]}),
          new TableRow({ children: [
            mkCell("6", 720, false, BLUE_LIGHT), mkCell("src/evaluator.py", 3240),
            mkCell("scikit-learn only", 2880), mkCell("Returns correct metric dict for a dummy input", 2520),
          ]}),
          new TableRow({ children: [
            mkCell("7", 720, false, BLUE_LIGHT), mkCell("src/trainer.py", 3240),
            mkCell("feature_extractor.py, evaluator.py, config.py", 2880), mkCell("hybrid_model.pkl exists, comparison table is printed", 2520),
          ]}),
          new TableRow({ children: [
            mkCell("8", 720, false, BLUE_LIGHT), mkCell("src/predictor.py", 3240),
            mkCell("preprocessor.py, feature_extractor.py, trainer.py output", 2880), mkCell("Returns valid dict for a single input string", 2520),
          ]}),
          new TableRow({ children: [
            mkCell("9", 720, false, BLUE_LIGHT), mkCell("api/schemas.py", 3240),
            mkCell("pydantic", 2880), mkCell("Schemas import without error", 2520),
          ]}),
          new TableRow({ children: [
            mkCell("10", 720, false, BLUE_LIGHT), mkCell("api/main.py", 3240),
            mkCell("predictor.py, schemas.py, fastapi, uvicorn", 2880), mkCell("GET /health returns 200, POST /predict returns correct JSON", 2520),
          ]}),
        ],
      }),
      gap(),
      h2("7.2  How to Run the Full Pipeline"),
      body("After all files are built, run the entire pipeline with one command:"),
      gap(),
      code("cd taglish-detector"),
      code("venv\\Scripts\\activate"),
      code("python run_pipeline.py"),
      gap(),
      body("Then start the API separately:"),
      code("uvicorn api.main:app --reload --port 8000"),
      gap(),
      body("Test it with curl or Postman:"),
      code('curl -X POST http://localhost:8000/predict -H "Content-Type: application/json"'),
      code('-d "{\\"text\\": \\"Grabe itong balita! Share agad bago matanggal NOW NA!\\"}"'),
      gap(),
      noteBox("IMPORTANT: Training Time Expectation on a Laptop CPU", "DistilBERT embedding extraction on the full corpus will take between 20 and 60 minutes on a laptop CPU with no GPU. This is expected and normal. Run it once, save the features.csv file, and never run embedding extraction again unless the dataset changes. Subsequent training runs load directly from features.csv and complete in under one minute.", ORANGE_LIGHT, ORANGE_DARK),
      gap(),
    ];
  }

  function sec8() {
    return [
      sectionBanner("SECTION 8: DEVELOPMENT RULES"), gap(),
      h2("8.1  Rules Every Team Member Must Follow"), gap(),
      bullet("Never hardcode a file path, model name, or threshold inside a module. Always import from config.py."),
      bullet("Never call backwards in the pipeline. Feature extractor does not call trainer. API does not call data loader."),
      bullet("Every function must have a docstring explaining its input, output, and what it does."),
      bullet("Every stage must print a status line when it starts and when it finishes. This makes debugging easy."),
      bullet("Run the full pipeline from run_pipeline.py only. Do not chain scripts manually."),
      bullet("Commit after each completed step in the Build Order table above. Use git with short, descriptive commit messages."),
      bullet("If a package version conflicts, pin the working version in requirements.txt immediately."),
      bullet("Do not store features.csv or model files in git. Add data/ and models/ to .gitignore."),
      gap(),
      h2("8.2  What to Do When Something Breaks"),
      bullet("Read the full error traceback from the bottom up. The last line usually tells you exactly what failed."),
      bullet("Check if the file path in config.py matches the actual location of the file on disk."),
      bullet("If a torch or transformers error appears, confirm your venv is activated before running anything."),
      bullet("If DistilBERT runs out of memory, reduce the batch size in feature_extractor.py from 32 to 8."),
      bullet("If the HuggingFace download fails, check your internet connection and try again. The dataset is cached after the first download."),
      gap(),
    ];
  }

  return { sec7, sec8 };
};
