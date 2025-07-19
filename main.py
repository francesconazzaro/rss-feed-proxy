from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
import os
from io import BytesIO
import requests
from lxml import etree

app = FastAPI()
PREFIX = os.getenv("PREFIX", "")


@app.get("/")
async def rewrite_feed(request: Request):
    feed_url = request.query_params.get("url")

    if not feed_url:
        raise HTTPException(status_code=400, detail="Missing ?url parameter")

    try:
        r = requests.get(feed_url)
        r.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching feed: {e}")

    # Parsing
    parser = etree.XMLParser(recover=True)
    tree = etree.parse(BytesIO(r.content), parser)
    root = tree.getroot()

    # Detect namespace if present
    nsmap = root.nsmap.copy()
    if None in nsmap:
        nsmap["default"] = nsmap.pop(None)  # Rename default namespace to a PREFIX
    elif not nsmap:
        nsmap = {}  # No namespaces

    # 1. <link> con testo (es. RSS 2.0)
    for elem in tree.xpath("//link", namespaces=nsmap):
        if elem.text and elem.text.strip().startswith("http"):
            print(f"Rewriting link to: {PREFIX + elem.text.strip()}")
            elem.text = PREFIX + elem.text.strip()

    # 2. <link href="..."> (es. Atom)
    for elem in tree.xpath("//link[@href]", namespaces=nsmap):
        href = elem.get("href")
        if href and href.startswith("http"):
            print(f"Rewriting link href: {PREFIX + href}")
            elem.set("href", PREFIX + href)

    # Output
    xml_output = etree.tostring(tree, encoding="utf-8", xml_declaration=True)
    return Response(content=xml_output, media_type="application/rss+xml")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5000)
