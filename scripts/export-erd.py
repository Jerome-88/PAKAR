"""Export ERD sources from SQLAlchemy metadata without starting the application.

Run: python scripts/export-erd.py
Render the DOT files with Graphviz, or the MMD files with Mermaid.
"""
from __future__ import annotations

import html
import importlib.util
import json
from pathlib import Path
import sys
import types

from sqlalchemy.dialects import postgresql


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "database"


def load_metadata():
    # Avoid app/__init__.py and its API/provider imports; no database connection.
    for name, path in (("erd_schema", ROOT / "backend/app"),
                       ("erd_schema.business", ROOT / "backend/app/business")):
        package = types.ModuleType(name)
        package.__path__ = [str(path)]
        sys.modules[name] = package
    for name, path in (("erd_schema.database", ROOT / "backend/app/database.py"),
                       ("erd_schema.business.tables", ROOT / "backend/app/business/tables.py")):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules["erd_schema.database"].metadata


def category(name):
    if name.startswith("business_"):
        return "Bisnis PAKAR", "#126B62", "#EAF6F2"
    if name.startswith("provider_spend_") or name in {"users", "sessions", "jobs", "job_attempts", "pilot_contacts"}:
        return "Akses dan infrastruktur", "#365D8D", "#EDF3FA"
    return "Simulasi kebijakan", "#7A5932", "#FAF3E8"


def esc(value):
    return html.escape(str(value), quote=True) or "&#32;"


def unique_column(column):
    table = column.table
    return (column.primary_key and len(table.primary_key.columns) == 1) or bool(column.unique) or any(
        i.unique and len(i.columns) == 1 and column.name in i.columns
        and i.dialect_options["postgresql"].get("where") is None
        for i in table.indexes
    )


def export(metadata, stem, title, names, compact=False):
    names = sorted(names)
    selected = set(names)
    edges = []
    dot = ["digraph ERD {", 'graph [rankdir=LR, bgcolor="#F8FAFC", pad="0.6", nodesep="0.45", ranksep="1.1", splines=polyline, outputorder=edgesfirst, fontname="Arial", fontsize=24, fontcolor="#152E41", labelloc=t, labeljust=l,',
           f'label="{title}\\nPostgreSQL | dari definisi SQLAlchemy | 09 November 2026\\nPK = primary key   FK = foreign key   ? = nullable   UQ = unik satu kolom\\nGaris: FK fisik; lingkaran = opsional; kaki tiga = banyak"];',
           'node [shape=plain, fontname="Arial"];',
           'edge [color="#607C90", penwidth=1.1, arrowsize=0.9, dir=both, fontname="Arial", fontsize=9];']
    mermaid = ["erDiagram", "    direction LR"]
    for name in names:
        table = metadata.tables[name]
        _, color, background = category(name)
        rows = [f'<TR><TD COLSPAN="3" BGCOLOR="{color}" ALIGN="LEFT" CELLPADDING="10"><FONT COLOR="white" POINT-SIZE="14"><B>{esc(name)}</B></FONT></TD></TR>']
        mermaid.append(f"    {name} {{")
        for column in table.columns:
            flags = []
            if column.primary_key:
                flags.append("PK")
            if column.foreign_keys:
                flags.append("FK")
            if unique_column(column) and not column.primary_key:
                flags.append("UQ")
            data_type = str(column.type.compile(dialect=postgresql.dialect()))
            if not compact or flags:
                rows.append(f'<TR><TD PORT="{column.name}_in" ALIGN="LEFT" BGCOLOR="{background}" CELLPADDING="5"><FONT POINT-SIZE="10" COLOR="{color}">{esc(" ".join(flags))}</FONT></TD><TD ALIGN="LEFT" CELLPADDING="5"><FONT POINT-SIZE="11">{esc(column.name)}{" ?" if column.nullable else ""}</FONT></TD><TD PORT="{column.name}_out" ALIGN="LEFT" CELLPADDING="5"><FONT POINT-SIZE="10" COLOR="#63788A">{esc(data_type)}</FONT></TD></TR>')
            mtype = data_type.lower().replace(" ", "_").replace(",", "_")
            mkeys = ",".join("UK" if k == "UQ" else k for k in flags)
            mermaid.append(f'        {mtype} {column.name}{" " + mkeys if mkeys else ""} "{"nullable" if column.nullable else "required"}"')
            for fk in sorted(column.foreign_keys, key=lambda f: f.target_fullname):
                parent = fk.column
                if parent.table.name in selected:
                    edges.append((column, parent, fk))
        if compact:
            rows.append(f'<TR><TD COLSPAN="3" ALIGN="LEFT" CELLPADDING="6"><FONT POINT-SIZE="10" COLOR="#63788A">{len(table.columns)} kolom total</FONT></TD></TR>')
        dot.append(f'"{name}" [label=<<TABLE BORDER="1" COLOR="#CFDAE3" CELLBORDER="0" CELLSPACING="0" BGCOLOR="white">{"".join(rows)}</TABLE>>];')
        mermaid.append("    }")
    for child, parent, fk in edges:
        tail = "teeodot" if child.nullable else "teetee"
        head = "teeodot" if unique_column(child) else "crowodot"
        description = f"{parent.table.name}.{parent.name} -> {child.table.name}.{child.name}; ON DELETE {fk.ondelete or 'NO ACTION'}"
        dot.append(f'"{parent.table.name}":{parent.name}_out:e -> "{child.table.name}":{child.name}_in:w [arrowtail={tail}, arrowhead={head}, tooltip="{esc(description)}"];')
        parent_mark = "|o" if child.nullable else "||"
        child_mark = "o|" if unique_column(child) else "o{"
        connector = "--" if child.primary_key else ".."
        mermaid.append(f'    {parent.table.name} {parent_mark}{connector}{child_mark} {child.table.name} : "{child.name}"')
    dot.append("}")
    (OUT / f"{stem}.dot").write_text("\n".join(dot) + "\n", encoding="utf-8")
    (OUT / f"{stem}.mmd").write_text("\n".join(mermaid) + "\n", encoding="utf-8")
    return {"name": stem, "tables": len(names), "foreign_keys": len(edges)}


def export_simple(metadata):
    """A selected-column view: show the main ownership tree, not every FK."""
    selection = {
        "users": ("Pengguna", ["id", "name", "email"]),
        "business_projects": ("Proyek bisnis", ["id", "owner_user_id", "context"]),
        "business_documents": ("Dokumen", ["id", "project_id", "name", "status"]),
        "business_personas": ("Persona", ["id", "project_id", "content"]),
        "business_analyses": ("Analisis", ["id", "project_id", "status", "result"]),
        "business_ideas": ("Ide bisnis", ["id", "project_id", "title"]),
        "business_chat_turns": ("Percakapan", ["id", "project_id", "status", "response"]),
        "business_claims": ("Klaim dokumen", ["id", "document_id", "content"]),
        "business_idea_revisions": ("Revisi ide", ["id", "idea_id", "version", "content"]),
    }
    dot = ["digraph ERD {",
           'graph [rankdir=TB, bgcolor="#F8FAFC", pad="0.45", nodesep="0.5", ranksep="0.8", splines=polyline, outputorder=edgesfirst, fontname="Arial", fontcolor="#152E41", labelloc=t,',
           'label=<<FONT POINT-SIZE="26"><B>PAKAR - ERD Sederhana</B></FONT><BR/><FONT POINT-SIZE="15">9 tabel utama | kolom dan relasi inti</FONT><BR/><BR/><FONT POINT-SIZE="12">PK = ID utama | FK = penghubung tabel | lingkaran + kaki tiga = nol atau banyak</FONT><BR/><BR/>>];',
           'node [shape=plain, fontname="Arial"];',
           'edge [color="#607C90", penwidth=1.5, dir=both, arrowtail=teetee, arrowhead=crowodot, arrowsize=0.8];']
    mermaid = ["erDiagram", "    direction TB"]
    edges = []
    for name, (label, columns) in selection.items():
        table = metadata.tables[name]
        _, color, background = category(name)
        rows = [f'<TR><TD COLSPAN="2" BGCOLOR="{color}" ALIGN="LEFT" CELLPADDING="10"><FONT COLOR="white" POINT-SIZE="18"><B>{label}</B></FONT><BR ALIGN="LEFT"/><FONT COLOR="white" POINT-SIZE="10">{name}</FONT></TD></TR>']
        mermaid.append(f"    {name} {{")
        for column_name in columns:
            column = table.c[column_name]
            flags = (["PK"] if column.primary_key else []) + (["FK"] if column.foreign_keys else [])
            suffix = " (JSON)" if str(column.type) == "JSONB" else ""
            rows.append(f'<TR><TD BGCOLOR="{background}" ALIGN="LEFT" CELLPADDING="7"><FONT COLOR="{color}" POINT-SIZE="11">{esc(" ".join(flags))}</FONT></TD><TD ALIGN="LEFT" CELLPADDING="7"><FONT POINT-SIZE="13">{column.name}{suffix}</FONT></TD></TR>')
            mtype = str(column.type).lower().replace(" ", "_").replace(",", "_")
            mermaid.append(f'        {mtype} {column.name}{" " + ",".join(flags) if flags else ""}')
            for fk in column.foreign_keys:
                parent = fk.column
                assert parent.table.name in selection
                assert parent.name in selection[parent.table.name][1]
                assert not column.nullable and not unique_column(column)
                edges.append((parent.table.name, name, column.name))
        mermaid.append("    }")
        dot.append(f'"{name}" [label=<<TABLE BORDER="1" COLOR="#CFDAE3" CELLBORDER="0" CELLSPACING="0" BGCOLOR="white">{"".join(rows)}</TABLE>>];')
    for parent, child, column in edges:
        dot.append(f'"{parent}" -> "{child}" [tooltip="{child}.{column} -> {parent}.id"];')
        mermaid.append(f'    {parent} ||..o{{ {child} : "{column}"')
    dot.append("}")
    (OUT / "erd-simple.dot").write_text("\n".join(dot) + "\n", encoding="utf-8")
    (OUT / "erd-simple.mmd").write_text("\n".join(mermaid) + "\n", encoding="utf-8")
    return {"name": "erd-simple", "tables": len(selection), "foreign_keys": len(edges), "scope": "selected columns and main relationships"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    metadata = load_metadata()
    # Resolve every FK now so incomplete or invalid metadata fails the export.
    foreign_keys = [fk for t in metadata.tables.values() for fk in t.foreign_keys]
    for fk in foreign_keys:
        assert fk.column.table.name in metadata.tables
    all_names = set(metadata.tables)
    business_names = {n for n in all_names if n.startswith(("business_", "provider_spend_"))} | {"users", "sessions", "jobs", "job_attempts"}
    result = [
        export_simple(metadata),
        export(metadata, "erd-overview", "PAKAR / RekaKebijakan - Peta relasi database", all_names, compact=True),
        export(metadata, "erd-business", "PAKAR - Detail modul bisnis dan infrastruktur", business_names),
        export(metadata, "erd-full", "PAKAR / RekaKebijakan - Schema lengkap", all_names),
    ]
    (OUT / "manifest.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
