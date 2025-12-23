"""
memoQ XLIFF (.mqxliff/.xlf/.xliff) parser helpers (SAFE FOR STREAMLIT IMPORT)

This module intentionally DOES NOT:
- import torch / comet
- load models
- call input()
- do CLI main()

It only parses XLIFF and returns extracted rows.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _ns_uri(tag: str) -> str | None:
    """Return namespace URI from a tag like '{uri}name', else None."""
    if tag.startswith("{") and "}" in tag:
        return tag[1 : tag.index("}")]
    return None


def _local_name(tag: str) -> str:
    """Return local name from '{uri}name' or 'name'."""
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _text(elem: ET.Element | None) -> str:
    """Get full text including nested inline tags."""
    if elem is None:
        return ""
    return "".join(elem.itertext()).strip()


def parse_mqxliff(xliff_path: Path):
    """
    Parse memoQ XLIFF and extract only segments with mq:status="ManuallyConfirmed".

    Returns:
      extracted_data: list[dict] with keys:
        - trans_unit_id
        - segmentguid
        - mt_provider
        - source
        - mt
        - ref
      source_lang: str | None
      target_lang: str | None
    """
    xliff_path = Path(xliff_path)

    tree = ET.parse(xliff_path)
    root = tree.getroot()

    # Default XLIFF namespace (commonly: urn:oasis:names:tc:xliff:document:1.2)
    xliff_ns = _ns_uri(root.tag)

    # memoQ namespace usually fixed: xmlns:mq="MQXliff"
    mq_ns = "MQXliff"

    ns: dict[str, str] = {}
    if xliff_ns:
        ns["x"] = xliff_ns
    ns["mq"] = mq_ns

    # Language codes from <file>
    source_lang = None
    target_lang = None
    file_elem = root.find(".//x:file", ns) if xliff_ns else root.find(".//file")
    if file_elem is not None:
        source_lang = file_elem.get("source-language") or file_elem.get("source_language")
        target_lang = file_elem.get("target-language") or file_elem.get("target_language")

    # Collect trans-units
    trans_units = root.findall(".//x:trans-unit", ns) if xliff_ns else [
        e for e in root.iter() if _local_name(e.tag) == "trans-unit"
    ]

    extracted_data: list[dict[str, Any]] = []
    for tu in trans_units:
        status = tu.get(f"{{{mq_ns}}}status")
        if status != "ManuallyConfirmed":
            continue

        tu_id = tu.get("id", "")
        seg_guid = tu.get(f"{{{mq_ns}}}segmentguid", "")

        # source/ref from trans-unit
        src_elem = tu.find("x:source", ns) if xliff_ns else tu.find("source")
        ref_elem = tu.find("x:target", ns) if xliff_ns else tu.find("target")
        source_text = _text(src_elem)
        ref_text = _text(ref_elem)

        # MT from mq:insertedmatch
        mt_text = ""
        mt_provider = ""

        for m in tu.findall("mq:insertedmatch", ns):
            matchtype = m.get("matchtype")
            matchsrc = (m.get("source") or "").strip()

            # robust: "MT / ..." (case-insensitive)
            if matchtype == "1" and matchsrc.lower().startswith("mt /"):
                mt_provider = matchsrc
                mt_target = m.find("x:target", ns) if xliff_ns else m.find("target")
                mt_text = _text(mt_target)
                break

        if source_text and ref_text and mt_text:
            extracted_data.append(
                {
                    "trans_unit_id": tu_id,
                    "segmentguid": seg_guid,
                    "mt_provider": mt_provider,
                    "source": source_text,
                    "mt": mt_text,
                    "ref": ref_text,
                }
            )

    return extracted_data, source_lang, target_lang
