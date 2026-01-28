import os
import sys

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from advanced_rag_system import AdvancedRAGSystem


def main() -> None:
    rag = AdvancedRAGSystem()
    vector = rag._encode_text("你好，今天天气怎么样。")
    if vector is None:
        raise RuntimeError("embedding returned None")
    if not isinstance(vector, np.ndarray):
        raise TypeError(f"embedding type unexpected: {type(vector)}")
    print(f"embedding_dim={vector.shape[0]}")
    print(f"embedding_preview={vector[:2].tolist()}")


if __name__ == "__main__":
    main()
