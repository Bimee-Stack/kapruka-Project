"""
Tier 2: LONG-TERM MEMORY (RAG over the Kapruka catalog)
-------------------------------------------------------
Idea: turn every product into a list of numbers (an "embedding") that captures
its MEANING. Store them in Qdrant. To search, turn the question into numbers
too and ask Qdrant for the closest products. That is why "birthday chocolate
dessert" can find "Chocolate Truffle Cake" even without matching words.

We use Qdrant in LOCAL mode (saves to a folder, no Docker needed).
Note: local mode allows only ONE program at a time to open the folder.
"""

import json
from qdrant_client import QdrantClient
from qdrant_client.models import (Distance, VectorParams, PointStruct,
                                  Filter, FieldCondition, MatchValue)
from sentence_transformers import SentenceTransformer

COLLECTION = "kapruka_catalog"
MODEL_NAME = "all-MiniLM-L6-v2"      # small, free, runs on your laptop
VECTOR_SIZE = 384                    # output size of the model above


class LongTermMemory:
    def __init__(self, db_path="data/qdrant_db"):
        self.client = QdrantClient(path=db_path)
        self.model = SentenceTransformer(MODEL_NAME)

    def _embed(self, text):
        return self.model.encode(text).tolist()

    def build_from_catalog(self, catalog_path="data/catalog.json"):
        """Read catalog.json from Part 1 and load every product into Qdrant."""
        products = json.load(open(catalog_path, encoding="utf-8"))

        # start fresh each time so we never get duplicates
        if self.client.collection_exists(COLLECTION):
            self.client.delete_collection(COLLECTION)
        self.client.create_collection(
            COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE))

        points = []
        for i, p in enumerate(products):
            # The text we want to be searchable
            text = f"{p['name']}. {p.get('description', '')} Category: {p.get('category', '')}"
            points.append(PointStruct(id=i, vector=self._embed(text), payload=p))

        self.client.upsert(COLLECTION, points)
        print(f"Stored {len(points)} products in Qdrant.")
        return len(points)

    def search(self, query, limit=5, hide_out_of_stock=True):
        """Return the products closest in meaning to `query`."""
        query_filter = None
        if hide_out_of_stock:
            query_filter = Filter(must_not=[FieldCondition(
                key="availability", match=MatchValue(value="out_of_stock"))])

        result = self.client.query_points(
            COLLECTION, query=self._embed(query),
            query_filter=query_filter, limit=limit)

        return [{**hit.payload, "score": round(hit.score, 3)} for hit in result.points]
