"""
Minimal FAISS compatibility shim.

Used when `faiss`/`faiss-cpu` isn't available (common on Python 3.13).
Implements the small subset this project uses: IndexFlatIP + read/write.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Tuple

import numpy as np


@dataclass
class IndexFlatIP:
    d: int

    def __post_init__(self) -> None:
        self._vectors = np.empty((0, self.d), dtype=np.float32)

    @property
    def ntotal(self) -> int:
        return int(self._vectors.shape[0])

    def add(self, vectors: np.ndarray) -> None:
        vectors = np.asarray(vectors, dtype=np.float32)
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        if vectors.shape[1] != self.d:
            raise ValueError(f"Vector dimension mismatch: expected {self.d}, got {vectors.shape[1]}")
        self._vectors = np.concatenate([self._vectors, vectors], axis=0)

    def search(self, queries: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        queries = np.asarray(queries, dtype=np.float32)
        if queries.ndim == 1:
            queries = queries.reshape(1, -1)
        if queries.shape[1] != self.d:
            raise ValueError(f"Query dimension mismatch: expected {self.d}, got {queries.shape[1]}")

        if self.ntotal == 0 or k <= 0:
            sims = np.zeros((queries.shape[0], max(k, 0)), dtype=np.float32)
            idx = -np.ones((queries.shape[0], max(k, 0)), dtype=np.int64)
            return sims, idx

        sims = queries @ self._vectors.T
        k = min(k, self.ntotal)
        topk_idx = np.argpartition(-sims, kth=k - 1, axis=1)[:, :k]
        topk_sims = np.take_along_axis(sims, topk_idx, axis=1)
        order = np.argsort(-topk_sims, axis=1)
        sorted_idx = np.take_along_axis(topk_idx, order, axis=1).astype(np.int64)
        sorted_sims = np.take_along_axis(topk_sims, order, axis=1).astype(np.float32)
        return sorted_sims, sorted_idx

    def reconstruct(self, i: int) -> np.ndarray:
        return np.asarray(self._vectors[int(i)], dtype=np.float32)


def write_index(index: IndexFlatIP, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as f:
        np.savez_compressed(f, d=np.array([index.d], dtype=np.int32), vectors=index._vectors)


def read_index(path: str) -> IndexFlatIP:
    with open(path, "rb") as f:
        data = np.load(f, allow_pickle=False)
    d = int(np.asarray(data["d"]).reshape(-1)[0])
    index = IndexFlatIP(d)
    vectors = np.asarray(data["vectors"], dtype=np.float32)
    if vectors.size:
        index.add(vectors)
    return index

