import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}  # BCB rejeita requisições sem User-Agent


def get_json(url, data=None, timeout=300, tries=4):
    """GET/POST JSON com novas tentativas: BCB e SIOP devolvem 502 esporádicos."""
    req = urllib.request.Request(url, data=data, headers=UA)
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip" or body[:2] == b"\x1f\x8b":
                    body = gzip.decompress(body)  # API de malhas do IBGE responde gzip sempre
                return json.loads(body)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            transient = not isinstance(e, urllib.error.HTTPError) or e.code >= 500
            if not transient or attempt == tries - 1:
                raise
            time.sleep(5 * (attempt + 1))


def sparql(endpoint, query):
    """Executa uma consulta SPARQL e devolve as linhas como dicts de strings."""
    body = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    rows = get_json(endpoint, data=body)["results"]["bindings"]
    return [{k: v["value"] for k, v in r.items()} for r in rows]
