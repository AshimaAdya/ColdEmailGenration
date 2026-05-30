import hashlib
import pandas as pd
import chromadb
import uuid

class Portfolio:
    def __init__(self, file_path="app/resources/my_portfolio.csv"):
        self.file_path = file_path
        self.data = pd.read_csv(file_path)
        # Drop any duplicate header rows
        self.data = self.data[self.data["Techstack"] != "Techstack"].reset_index(drop=True)
        self.chroma_client = chromadb.PersistentClient('coldemailvectorstore')
        self.collection = self.chroma_client.get_or_create_collection(name="portfolio")

    def _file_hash(self) -> str:
        with open(self.file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def load_portfolio(self):
        current_hash = self._file_hash()
        stored_hash = self.collection.metadata.get("csv_hash") if self.collection.metadata else None

        if stored_hash == current_hash and self.collection.count():
            return  # CSV unchanged, vector store is current

        # CSV changed or collection is empty — rebuild
        self.chroma_client.delete_collection("portfolio")
        self.collection = self.chroma_client.get_or_create_collection(
            name="portfolio",
            metadata={"csv_hash": current_hash}
        )
        for _, row in self.data.iterrows():
            self.collection.add(
                documents=row["Techstack"],
                metadatas={"links": row["Links"]},
                ids=[str(uuid.uuid4())]
            )

    def force_reload(self):
        self.data = pd.read_csv(self.file_path)
        self.data = self.data[self.data["Techstack"] != "Techstack"].reset_index(drop=True)
        self.chroma_client.delete_collection("portfolio")
        current_hash = self._file_hash()
        self.collection = self.chroma_client.get_or_create_collection(
            name="portfolio",
            metadata={"csv_hash": current_hash}
        )
        for _, row in self.data.iterrows():
            self.collection.add(
                documents=row["Techstack"],
                metadatas={"links": row["Links"]},
                ids=[str(uuid.uuid4())]
            )

    def _fallback_links(self, n: int = 2) -> list[str]:
        """Return the first n links from the CSV when semantic search yields nothing."""
        return self.data["Links"].dropna().head(n).tolist()

    def query_links(self, skills) -> list[str]:
        # Always ensure the collection is loaded before querying
        if self.collection.count() == 0:
            self.load_portfolio()

        query = [skills] if isinstance(skills, str) else (skills or [])
        if not query:
            return self._fallback_links()

        raw = self.collection.query(query_texts=query, n_results=2).get('metadatas', [])
        # Flatten [[{"links": "url"}, ...], ...] → deduplicated list of URL strings
        seen = set()
        urls = []
        for group in raw:
            for item in group:
                url = item.get("links", "") if isinstance(item, dict) else ""
                if url and url not in seen:
                    seen.add(url)
                    urls.append(url)

        # Fall back to first CSV entries if semantic search returned nothing
        return urls if urls else self._fallback_links()
