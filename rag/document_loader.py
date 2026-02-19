import yaml
from pathlib import Path


def load_knowledge_base(knowledge_dir: str) -> list[dict]:
    docs = []
    path = Path(knowledge_dir)
    for file in sorted(path.glob("*.yaml")):
        with open(file, "r", encoding="utf-8") as f:
            items = yaml.safe_load(f)
        for item in items:
            docs.append({
                "id": item["id"],
                "text": item["text"].strip(),
                "metadata": item.get("metadata", {})
            })
    return docs
