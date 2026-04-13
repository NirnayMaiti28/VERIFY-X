import os

# Root project name
root = "text_verification"

# Folder structure
folders = [
    f"{root}/api",
    f"{root}/pipeline",
    f"{root}/claim_processing",
    f"{root}/retrieval",
    f"{root}/verdict",
    f"{root}/models/embeddings",
    f"{root}/models/verifier",
    f"{root}/config",
    f"{root}/utils"
]

# Files to create
files = [
    f"{root}/main.py",

    f"{root}/api/verify_route.py",

    f"{root}/pipeline/verify_pipeline.py",

    f"{root}/claim_processing/cleaner.py",
    f"{root}/claim_processing/entity_extractor.py",
    f"{root}/claim_processing/embedding.py",

    f"{root}/retrieval/news_api.py",
    f"{root}/retrieval/wikipedia_api.py",
    f"{root}/retrieval/vector_search.py",
    f"{root}/retrieval/ranker.py",

    f"{root}/verdict/verdict_generator.py",

    f"{root}/config/settings.py",

    f"{root}/utils/logger.py",
    f"{root}/utils/cache.py",
    f"{root}/utils/explanation_generator.py",
    f"{root}/utils/source_credibility.py",
    f"{root}/utils/claim_normalizer.py"
]

# Create folders
for folder in folders:
    os.makedirs(folder, exist_ok=True)

# Create files
for file in files:
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            pass

print("✅ Project structure created successfully!")