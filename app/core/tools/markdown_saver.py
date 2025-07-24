import os

class MarkdownSaver:
    def __init__(self, save_dir="output"):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

    def save(self, content: str, filename: str = "article.md") -> str:
        path = os.path.join(self.save_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path 