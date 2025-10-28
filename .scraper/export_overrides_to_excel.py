import os
import json


def export_to_excel(json_path: str, out_path: str) -> None:
    try:
        from openpyxl import Workbook
    except Exception:
        print("Bitte zuerst installieren: pip install openpyxl")
        raise

    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Datei nicht gefunden: {json_path}")

    with open(json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh) or {}

    wb = Workbook()
    # Entferne die Default-Sheet
    wb.remove(wb.active)

    sections = [
        "sportangebote",
        "sportkurse",
        "kurs_termine",
        "unisport_locations",
    ]

    for section in sections:
        items = data.get(section) or []
        if not isinstance(items, list):
            items = []

        # Sammle alle Feld-Schlüssel (aus item["fields"]) für Spaltenkopf
        field_keys = set()
        for it in items:
            fields = it.get("fields") if isinstance(it, dict) else None
            if isinstance(fields, dict):
                field_keys.update(fields.keys())
        ordered_fields = sorted(field_keys)

        ws = wb.create_sheet(title=section[:31])  # Excel-Sheetname max 31 Zeichen
        headers = ["identifier", "ignore_valueerror"] + ordered_fields
        ws.append(headers)

        for it in items:
            if not isinstance(it, dict):
                continue
            identifier = (it.get("identifier") or "")
            ignore_value = it.get("ignore_valueerror")
            # Standardisiere auf bool/None
            if ignore_value is None:
                ignore_value = False
            fields = it.get("fields") if isinstance(it.get("fields"), dict) else {}

            row = [identifier, bool(ignore_value)]
            for k in ordered_fields:
                row.append(fields.get(k))
            ws.append(row)

    # Speichern
    wb.save(out_path)
    print(f"Excel geschrieben: {out_path}")


if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    json_path = os.path.join(base_dir, "missing_overrides.json")
    out_path = os.path.join(base_dir, "missing_overrides.xlsx")
    export_to_excel(json_path, out_path)


