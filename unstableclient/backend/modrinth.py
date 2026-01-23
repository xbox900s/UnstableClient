from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, Optional

import requests


class ModrinthClient:
    def __init__(self) -> None:
        self.base_url = "https://api.modrinth.com/v2"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "UnstableClient/1.0"})
        self.cache_projects: Dict[str, Dict[str, Any]] = {}
        self.cache_versions: Dict[str, Dict[str, Any]] = {}
        self.cache_hashes: Dict[str, Dict[str, Any]] = {}
        self.last_request = 0.0

    def _rate_limit(self) -> None:
        now = time.time()
        if now - self.last_request < 0.2:
            time.sleep(0.2)
        self.last_request = time.time()

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        self._rate_limit()
        resp = self.session.get(f"{self.base_url}{path}", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def search_projects(self, query: str, facets: Optional[list] = None) -> dict:
        params = {"query": query, "limit": 20}
        if facets:
            params["facets"] = facets
        return self._get("/search", params=params)

    def get_project(self, project_id: str) -> dict:
        if project_id in self.cache_projects:
            return self.cache_projects[project_id]
        data = self._get(f"/project/{project_id}")
        self.cache_projects[project_id] = data
        return data

    def get_version(self, version_id: str) -> dict:
        if version_id in self.cache_versions:
            return self.cache_versions[version_id]
        data = self._get(f"/version/{version_id}")
        self.cache_versions[version_id] = data
        return data

    def get_version_by_hash(self, sha1: str) -> Optional[dict]:
        if sha1 in self.cache_hashes:
            return self.cache_hashes[sha1]
        try:
            data = self._get(f"/version_file/{sha1}", params={"algorithm": "sha1"})
        except requests.HTTPError:
            return None
        self.cache_hashes[sha1] = data
        return data

    def download_file(self, url: str, dest_path) -> None:
        self._rate_limit()
        with self.session.get(url, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            temp_path = dest_path.with_suffix(".tmp")
            with temp_path.open("wb") as handle:
                for chunk in resp.iter_content(chunk_size=1024 * 64):
                    if chunk:
                        handle.write(chunk)
            temp_path.replace(dest_path)

    @staticmethod
    def sha1_for_file(path) -> str:
        digest = hashlib.sha1()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 64), b""):
                digest.update(chunk)
        return digest.hexdigest()
