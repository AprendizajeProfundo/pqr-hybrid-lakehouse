from __future__ import annotations

import argparse
import csv
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

XML_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

# Regiones naturales (mapeo por codigo DANE de departamento)
REGION_BY_DEPARTMENT_CODE = {
    "05": "Andina",      # Antioquia
    "08": "Caribe",      # Atlantico
    "11": "Andina",      # Bogota D.C.
    "13": "Caribe",      # Bolivar
    "15": "Andina",      # Boyaca
    "17": "Andina",      # Caldas
    "18": "Amazonia",    # Caqueta
    "19": "Pacifica",    # Cauca
    "20": "Caribe",      # Cesar
    "23": "Caribe",      # Cordoba
    "25": "Andina",      # Cundinamarca
    "27": "Pacifica",    # Choco
    "41": "Andina",      # Huila
    "44": "Caribe",      # La Guajira
    "47": "Caribe",      # Magdalena
    "50": "Orinoquia",   # Meta
    "52": "Pacifica",    # Narino
    "54": "Andina",      # Norte de Santander
    "63": "Andina",      # Quindio
    "66": "Andina",      # Risaralda
    "68": "Andina",      # Santander
    "70": "Caribe",      # Sucre
    "73": "Andina",      # Tolima
    "76": "Pacifica",    # Valle del Cauca
    "81": "Orinoquia",   # Arauca
    "85": "Orinoquia",   # Casanare
    "86": "Amazonia",    # Putumayo
    "88": "Insular",     # San Andres
    "91": "Amazonia",    # Amazonas
    "94": "Amazonia",    # Guainia
    "95": "Amazonia",    # Guaviare
    "97": "Amazonia",    # Vaupes
    "99": "Orinoquia",   # Vichada
}


def _normalize_header(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def _cell_value(cell: ET.Element, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value_node = cell.find("x:v", XML_NS)
    if value_node is None or value_node.text is None:
        return ""

    raw = value_node.text
    if cell_type == "s":
        idx = int(raw)
        return shared[idx] if 0 <= idx < len(shared) else ""
    return raw


def _read_shared_strings(xlsx_zip: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in xlsx_zip.namelist():
        return []
    root = ET.fromstring(xlsx_zip.read("xl/sharedStrings.xml"))
    result: list[str] = []
    for si in root.findall("x:si", XML_NS):
        text = "".join((t.text or "") for t in si.findall(".//x:t", XML_NS))
        result.append(text)
    return result


def _first_sheet_path(xlsx_zip: zipfile.ZipFile) -> str:
    workbook = ET.fromstring(xlsx_zip.read("xl/workbook.xml"))
    first_sheet = workbook.find("x:sheets/x:sheet", XML_NS)
    if first_sheet is None:
        raise RuntimeError("No se encontro ninguna hoja en el archivo Excel.")

    rel_id = first_sheet.attrib.get(REL_NS)
    rels = ET.fromstring(xlsx_zip.read("xl/_rels/workbook.xml.rels"))
    for rel in rels:
        if rel.attrib.get("Id") == rel_id:
            target = rel.attrib["Target"]
            return target if target.startswith("xl/") else f"xl/{target}"
    raise RuntimeError("No se pudo resolver la hoja principal en workbook.xml.rels.")


def extract_rows(xlsx_path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(xlsx_path) as zf:
        shared = _read_shared_strings(zf)
        sheet_path = _first_sheet_path(zf)
        sheet = ET.fromstring(zf.read(sheet_path))
        rows = sheet.findall("x:sheetData/x:row", XML_NS)
        if not rows:
            return []

        header_cells = rows[0].findall("x:c", XML_NS)
        headers = [_normalize_header(_cell_value(cell, shared)) for cell in header_cells]
        header_map = {idx: header for idx, header in enumerate(headers)}

        data_rows: list[dict[str, str]] = []
        for row in rows[1:]:
            values = [_cell_value(cell, shared).strip() for cell in row.findall("x:c", XML_NS)]
            if not any(values):
                continue
            payload = {header_map[i]: values[i] if i < len(values) else "" for i in header_map}
            data_rows.append(payload)
        return data_rows


def transform_rows(raw_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    transformed: list[dict[str, str]] = []
    for row in raw_rows:
        dept_code = row.get("codigo_departamento", "").zfill(2)
        city_code = row.get("codigo_municipio", "").zfill(5)
        dept_name = row.get("nombre_departamento", "").strip()
        city_name = row.get("nombre_municipio", "").strip()
        lon = row.get("longitud", "").strip()
        lat = row.get("latitud", "").strip()

        if not dept_code or not city_code or not dept_name or not city_name:
            continue

        region = REGION_BY_DEPARTMENT_CODE.get(dept_code, "Sin_Region")
        transformed.append(
            {
                "region_name": region,
                "department_name": dept_name,
                "city_name": city_name,
                "dane_department_code": dept_code,
                "dane_city_code": city_code,
                "latitude": lat,
                "longitude": lon,
            }
        )
    return transformed


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "region_name",
        "department_name",
        "city_name",
        "dane_department_code",
        "dane_city_code",
        "latitude",
        "longitude",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Transforma DIVIPOLA_Municipios.xlsx a CSV listo para dim_geo.")
    parser.add_argument("--input", default="data/dane/DIVIPOLA_Municipios.xlsx")
    parser.add_argument("--output", default="data/dane/divipola_dim_geo.csv")
    args = parser.parse_args()

    raw_rows = extract_rows(Path(args.input))
    rows = transform_rows(raw_rows)
    write_csv(rows, Path(args.output))
    print(f"CSV generado: {args.output}")
    print(f"Filas: {len(rows)}")


if __name__ == "__main__":
    main()
