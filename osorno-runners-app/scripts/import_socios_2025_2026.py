from pathlib import Path

import pandas as pd


def pick_col(columns, *terms):
    for col in columns:
        norm = str(col).upper()
        if all(term in norm for term in terms):
            return col
    return None


def esc(value):
    return str(value or "").replace("'", "''")


root = Path(r"C:\xampp\htdocs\www\Cuotas_OR")
source = root / "Ejercicio_Cuotas.xlsx"
target = root / "osorno-runners-app" / "database" / "import_socios_2025_2026.sql"

df = pd.read_excel(source, sheet_name="BD_Pagos")
df = df.loc[:, ~df.columns.str.contains(r"^Unnamed")]

rut_col = pick_col(df.columns, "RUT")
nom_col = pick_col(df.columns, "INTEGRANTE")
anio_col = pick_col(df.columns, "A", "O")
sexo_col = pick_col(df.columns, "SEXO")
estado_col = pick_col(df.columns, "ESTADO")
fecha_col = pick_col(df.columns, "FECHA", "PAGO")

d = df[[rut_col, nom_col, anio_col, sexo_col, estado_col, fecha_col]].copy()
d.columns = ["rut", "nombre", "anio", "sexo", "estado", "fecha_pago"]
d = d[d["rut"].notna() & d["nombre"].notna()]
d["anio"] = pd.to_numeric(d["anio"], errors="coerce")
d = d[d["anio"].isin([2025, 2026])]
d["fecha_pago"] = pd.to_datetime(d["fecha_pago"], errors="coerce")

d["rut"] = (
    d["rut"]
    .astype(str)
    .str.upper()
    .str.replace(r"[^0-9K]", "", regex=True)
    .str.replace(r"\.0$", "", regex=True)
    .str.lstrip("0")
)
d["nombre"] = d["nombre"].astype(str).str.strip()
d = d[(d["rut"] != "") & (d["nombre"] != "")]
d = d.sort_values(["rut", "anio", "fecha_pago"])

latest = d.groupby("rut", as_index=False).tail(1).copy()
latest["anio"] = latest["anio"].astype(int)
latest = latest[["rut", "nombre", "anio", "sexo", "estado"]].sort_values("nombre")

lines = ["USE osorno_runners;"]
for row in latest.itertuples(index=False):
    lines.append(
        "INSERT INTO socios (rut,nombre,anio,sexo,estado) "
        f"VALUES ('{esc(row.rut)}','{esc(row.nombre)}',{int(row.anio)},'{esc(row.sexo)}','{esc(row.estado)}') "
        "ON DUPLICATE KEY UPDATE nombre=VALUES(nombre), anio=VALUES(anio), sexo=VALUES(sexo), estado=VALUES(estado);"
    )

target.write_text("\n".join(lines), encoding="utf-8")
print(f"generated {len(latest)} socios in {target}")
