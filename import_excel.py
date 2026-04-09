"""
Script de importación del Excel original de avisos a la base de datos.

Uso:
    python import_excel.py ruta/al/archivo.xlsx

El Excel debe tener las columnas (en orden):
    A: Aviso (Nº)
    B: Fecha de solicitud
    C: Generador OT
    D: Generador Aviso
    E: E.S.M.
    F: Descripción de la OT

Columnas opcionales (si existen):
    G: Estado
    H: Coordinador (nombre)
    I: Enlace Drive
    J: Material necesario
    K: Fecha cierre
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import re
from datetime import datetime
from pathlib import Path

from database.db import init_db, get_connection


def extract_sede(esm: str) -> str:
    if not esm or pd.isna(esm):
        return ""
    m = re.search(r"OBRA CIVIL\s+(.+)$", str(esm).strip(), re.IGNORECASE)
    return m.group(1).strip() if m else str(esm).strip()


def parse_fecha(val) -> str:
    """Convierte varios formatos de fecha a 'YYYY-MM-DD'."""
    if pd.isna(val) or val is None or str(val).strip() == "":
        return str(datetime.today().date())
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s


def import_excel(filepath: str, sheet_name: int | str = 0, skip_rows: int = 0):
    print(f"\n📂 Leyendo: {filepath}")
    init_db()

    df = pd.read_excel(filepath, sheet_name=sheet_name, skiprows=skip_rows, header=0)
    print(f"   {len(df)} filas, {len(df.columns)} columnas")
    print(f"   Columnas detectadas: {list(df.columns)}")

    conn = get_connection()
    c    = conn.cursor()

    imported = 0
    skipped  = 0
    errors   = 0

    for idx, row in df.iterrows():
        try:
            vals = row.tolist()
            # Mapeo por posición (columnas A-F son las obligatorias)
            num_aviso       = vals[0] if len(vals) > 0 else None
            fecha_str       = vals[1] if len(vals) > 1 else None
            generador_ot    = str(vals[2]).strip() if len(vals) > 2 and not pd.isna(vals[2]) else ""
            generador_aviso = str(vals[3]).strip() if len(vals) > 3 and not pd.isna(vals[3]) else ""
            esm             = str(vals[4]).strip() if len(vals) > 4 and not pd.isna(vals[4]) else ""
            descripcion     = str(vals[5]).strip() if len(vals) > 5 and not pd.isna(vals[5]) else ""

            # Columnas opcionales
            estado          = str(vals[6]).strip() if len(vals) > 6 and not pd.isna(vals[6]) else "En proceso"
            enlace_drive    = str(vals[8]).strip() if len(vals) > 8 and not pd.isna(vals[8]) else ""
            material        = str(vals[9]).strip() if len(vals) > 9 and not pd.isna(vals[9]) else ""
            fecha_cierre    = parse_fecha(vals[10]) if len(vals) > 10 and not pd.isna(vals[10]) else None

            # Validar número de aviso
            if pd.isna(num_aviso) or str(num_aviso).strip() in ("", "nan", "Aviso"):
                skipped += 1
                continue

            num_aviso_int = int(float(str(num_aviso)))
            fecha         = parse_fecha(fecha_str)
            sede          = extract_sede(esm)

            # Validar estado
            if estado not in ("En proceso", "Acabado", "Falta material"):
                estado = "En proceso"

            # Insertar (ignorar duplicados)
            existing = c.execute(
                "SELECT id FROM avisos WHERE num_aviso=?", (num_aviso_int,)
            ).fetchone()
            if existing:
                print(f"   ⏭️  Aviso #{num_aviso_int} ya existe — omitido")
                skipped += 1
                continue

            c.execute("""
                INSERT INTO avisos
                    (num_aviso, fecha_solicitud, generador_ot, generador_aviso,
                     esm, sede, descripcion, estado, enlace_drive,
                     material_necesario, fecha_cierre)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                num_aviso_int, fecha, generador_ot, generador_aviso,
                esm, sede, descripcion, estado, enlace_drive,
                material or None, fecha_cierre,
            ))
            imported += 1

        except Exception as e:
            print(f"   ❌ Error en fila {idx+2}: {e}")
            errors += 1

    conn.commit()
    conn.close()

    print(f"\n✅ Importación completada:")
    print(f"   Importados : {imported}")
    print(f"   Omitidos   : {skipped}")
    print(f"   Errores    : {errors}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    import_excel(sys.argv[1])
