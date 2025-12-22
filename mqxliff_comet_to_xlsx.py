"""
COMET MT Evaluation Script for memoQ XLIFF (.mqxliff/.xlf/.xliff)

Extracts:
- src: <source> inside <trans-unit>
- ref: <target> inside <trans-unit> when mq:status="ManuallyConfirmed"
- mt : <target> inside <mq:insertedmatch matchtype="1" source="MT / ...">

Then computes COMET scores (wmt22-comet-da) and exports an .xlsx
to the same folder as the input file.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd
from comet import download_model, load_from_checkpoint  # type: ignore


# Optional .env support (HF_TOKEN)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


COMET_MODEL_NAME = "Unbabel/wmt22-comet-da"


def _ns_uri(tag: str) -> str | None:
    """Return namespace URI from a tag like '{uri}name', else None."""
    if tag.startswith("{") and "}" in tag:
        return tag[1:tag.index("}")]
    return None


def _local_name(tag: str) -> str:
    """Return local name from '{uri}name' or 'name'."""
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _text(elem: ET.Element | None) -> str:
    """Get full text including nested inline tags."""
    if elem is None:
        return ""
    return "".join(elem.itertext()).strip()


def load_comet_model():
    print(f"Loading COMET model: {COMET_MODEL_NAME}")
    if os.getenv("HF_TOKEN"):
        print("  - Using HF_TOKEN from environment/.env")
    else:
        print("  - Tip: run 'hf auth login' OR set HF_TOKEN in a .env file")

    model_path = download_model(COMET_MODEL_NAME)
    model = load_from_checkpoint(model_path)
    print("Model loaded successfully.\n")
    return model


def parse_mqxliff(xliff_path: Path):
    """
    Returns:
      extracted_data: list[dict] with keys: source, mt, ref, trans_unit_id, segmentguid, mt_provider
      source_lang, target_lang
    """
    print(f"Parsing: {xliff_path}")

    tree = ET.parse(xliff_path)
    root = tree.getroot()

    # Default XLIFF namespace (your file uses: urn:oasis:names:tc:xliff:document:1.2)
    xliff_ns = _ns_uri(root.tag)

    # memoQ namespace is fixed in your file: xmlns:mq="MQXliff"
    mq_ns = "MQXliff"

    ns = {}
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

    print(f"  - XLIFF ns: {xliff_ns}")
    print(f"  - memoQ ns: {mq_ns}")
    print(f"  - trans-units found: {len(trans_units)}")

    extracted_data = []
    skipped_status = 0
    skipped_missing = 0

    for tu in trans_units:
        status = tu.get(f"{{{mq_ns}}}status")
        if status != "ManuallyConfirmed":
            skipped_status += 1
            continue

        tu_id = tu.get("id", "")
        seg_guid = tu.get(f"{{{mq_ns}}}segmentguid", "")

        # source/ref from trans-unit (MUST use XLIFF namespace)
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
            extracted_data.append({
                "trans_unit_id": tu_id,
                "segmentguid": seg_guid,
                "mt_provider": mt_provider,
                "source": source_text,
                "mt": mt_text,
                "ref": ref_text,
            })
        else:
            skipped_missing += 1

    print(f"  - Extracted rows: {len(extracted_data)}")
    print(f"  - Skipped (status != ManuallyConfirmed): {skipped_status}")
    print(f"  - Skipped (missing source/ref/mt): {skipped_missing}\n")

    return extracted_data, source_lang, target_lang


def score_and_export(model, xliff_path: Path):
    extracted_data, source_lang, target_lang = parse_mqxliff(xliff_path)

    output_path = xliff_path.parent / f"{xliff_path.stem}_comet_scores.xlsx"

    # Always write an output (even if empty) for debugging
    if not extracted_data:
        df_empty = pd.DataFrame(columns=[
            "trans_unit_id", "segmentguid", "mt_provider",
            "source", "mt", "ref",
            "source_language", "target_language",
            "comet_score"
        ])
        df_empty.to_excel(output_path, index=False)
        print(f"No valid rows extracted. Saved empty Excel: {output_path}")
        return

    df = pd.DataFrame(extracted_data)
    if source_lang:
        df["source_language"] = source_lang
    if target_lang:
        df["target_language"] = target_lang

    data = [{"src": r["source"], "mt": r["mt"], "ref": r["ref"]} for r in df.to_dict("records")]

    print(f"Computing COMET scores for {len(data)} segments...")
    model_output = model.predict(data, batch_size=8, gpus=0)
    df["comet_score"] = model_output["scores"]

    df.to_excel(output_path, index=False)
    print(f"Saved: {output_path}\n")


def main():
    print("=" * 60)
    print("memoQ XLIFF → COMET → XLSX")
    print("=" * 60)

    # Ask user for input file path
    xliff_input = input(
        "\nPaste FULL path to the mqxliff / xlf / xliff file and press Enter:\n> "
    ).strip().strip('"')

    if not xliff_input:
        print("❌ No file path provided. Exiting.")
        input("Press Enter to close...")
        return

    xliff_path = Path(xliff_input).expanduser().resolve()
    print(f"\nResolved path: {xliff_path}")

    if not xliff_path.exists():
        print("❌ File does NOT exist.")
        input("Press Enter to close...")
        return

    if xliff_path.suffix.lower() not in [".mqxliff", ".xlf", ".xliff"]:
        print("⚠️ Warning: file extension is not typical XLIFF")

    # Load COMET model (once)
    model = load_comet_model()

    # Process file
    try:
        score_and_export(model, xliff_path)
    except Exception as e:
        print("\n❌ ERROR during processing:")
        print(e)
        import traceback
        traceback.print_exc()

    print("\n✅ Done.")
    input("Press Enter to close...")



if __name__ == "__main__":
    main()
