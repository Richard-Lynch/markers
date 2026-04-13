"""
Real-world usage: ORM-style schema definition with markers.

Defines a DB marker group with column constraints and relationships,
then shows functions that extract table definitions and relationship
maps from the annotated classes.
"""

from typing import Annotated, Any

from markers import Marker, MarkerGroup, Registry

# ===================================================================
# 1. Define markers
# ===================================================================


# Column constraints
class PrimaryKey(Marker):
    mark = "primary_key"
    auto_increment: bool = True


class NotNull(Marker):
    mark = "not_null"


class Unique(Marker):
    pass


class Default(Marker):
    value: Any


class Check(Marker):
    expression: str


class Indexed(Marker):
    unique: bool = False
    name: str = ""


class ColumnType(Marker):
    mark = "column_type"
    sql_type: str


# Relationships
class ForeignKey(Marker):
    mark = "foreign_key"
    to: str
    column: str = "id"
    on_delete: str = "CASCADE"
    on_update: str = "NO ACTION"


class OneToOne(Marker):
    mark = "one_to_one"
    to: str
    foreign_key: str


class OneToMany(Marker):
    mark = "one_to_many"
    to: str
    foreign_key: str


class ManyToMany(Marker):
    mark = "many_to_many"
    to: str
    through: str
    local_key: str = "id"
    remote_key: str = "id"


# Table-level config
class TableName(Marker):
    mark = "table_name"
    name: str


# ===================================================================
# 2. MarkerGroup
# ===================================================================


class DB(MarkerGroup):
    PrimaryKey = PrimaryKey
    NotNull = NotNull
    Unique = Unique
    Default = Default
    Check = Check
    Indexed = Indexed
    ColumnType = ColumnType
    ForeignKey = ForeignKey
    OneToOne = OneToOne
    OneToMany = OneToMany
    ManyToMany = ManyToMany
    TableName = TableName


# ===================================================================
# 3. Define models
# ===================================================================


class Entity(DB.mixin, Registry):
    id: Annotated[int, DB.PrimaryKey(), DB.ColumnType(sql_type="SERIAL")]


class User(Entity):
    username: Annotated[str, DB.NotNull(), DB.Unique(), DB.Indexed(unique=True), DB.ColumnType(sql_type="VARCHAR(50)")]
    email: Annotated[str, DB.NotNull(), DB.Unique(), DB.Indexed(unique=True), DB.ColumnType(sql_type="VARCHAR(255)")]
    password_hash: Annotated[str, DB.NotNull(), DB.ColumnType(sql_type="VARCHAR(255)")]
    is_active: Annotated[bool, DB.NotNull(), DB.Default(value=True), DB.ColumnType(sql_type="BOOLEAN")] = True
    created_at: Annotated[str, DB.NotNull(), DB.Default(value="NOW()"), DB.ColumnType(sql_type="TIMESTAMP")] = ""

    # Relationships (virtual — not columns, but metadata for the ORM)
    profile: Annotated[Any, DB.OneToOne(to="Profile", foreign_key="user_id")]
    posts: Annotated[Any, DB.OneToMany(to="Post", foreign_key="author_id")]
    roles: Annotated[Any, DB.ManyToMany(to="Role", through="user_roles")]


class Profile(Entity):
    user_id: Annotated[int, DB.NotNull(), DB.ForeignKey(to="User"), DB.Unique(), DB.ColumnType(sql_type="INTEGER")]
    display_name: Annotated[str, DB.ColumnType(sql_type="VARCHAR(100)")] = ""
    bio: Annotated[str, DB.ColumnType(sql_type="TEXT")] = ""
    avatar_url: Annotated[str, DB.ColumnType(sql_type="VARCHAR(500)")] = ""


class Post(Entity):
    author_id: Annotated[int, DB.NotNull(), DB.ForeignKey(to="User"), DB.Indexed(), DB.ColumnType(sql_type="INTEGER")]
    title: Annotated[str, DB.NotNull(), DB.ColumnType(sql_type="VARCHAR(200)")]
    body: Annotated[str, DB.NotNull(), DB.ColumnType(sql_type="TEXT")]
    status: Annotated[
        str,
        DB.NotNull(),
        DB.Default(value="draft"),
        DB.Check(expression="status IN ('draft','published','archived')"),
        DB.ColumnType(sql_type="VARCHAR(20)"),
    ] = "draft"
    published_at: Annotated[str | None, DB.ColumnType(sql_type="TIMESTAMP")] = None

    # Relationships
    author: Annotated[Any, DB.ForeignKey(to="User"), DB.OneToOne(to="User", foreign_key="author_id")]
    comments: Annotated[Any, DB.OneToMany(to="Comment", foreign_key="post_id")]
    tags: Annotated[Any, DB.ManyToMany(to="Tag", through="post_tags")]


class Comment(Entity):
    post_id: Annotated[int, DB.NotNull(), DB.ForeignKey(to="Post"), DB.Indexed(), DB.ColumnType(sql_type="INTEGER")]
    user_id: Annotated[int, DB.NotNull(), DB.ForeignKey(to="User"), DB.Indexed(), DB.ColumnType(sql_type="INTEGER")]
    body: Annotated[str, DB.NotNull(), DB.ColumnType(sql_type="TEXT")]
    created_at: Annotated[str, DB.NotNull(), DB.Default(value="NOW()"), DB.ColumnType(sql_type="TIMESTAMP")] = ""


class Tag(Entity):
    name: Annotated[str, DB.NotNull(), DB.Unique(), DB.ColumnType(sql_type="VARCHAR(50)")]


class Role(Entity):
    name: Annotated[str, DB.NotNull(), DB.Unique(), DB.ColumnType(sql_type="VARCHAR(50)")]
    description: Annotated[str, DB.ColumnType(sql_type="TEXT")] = ""


# ===================================================================
# 4. Extraction functions
# ===================================================================


def get_table_name(cls: type) -> str:
    """Derive SQL table name from class or TableName marker."""
    for info in cls.fields.values():
        marker = info.get("table_name")
        if marker:
            return marker.name
    return cls.__name__.lower() + "s"


def extract_columns(cls: type) -> list[dict[str, Any]]:
    """Extract column definitions from a model class."""
    columns = []
    for name, info in cls.fields.items():
        # Skip relationship-only fields (no column_type)
        col_type_marker = info.get("column_type")
        if col_type_marker is None:
            continue

        col: dict[str, Any] = {
            "name": name,
            "sql_type": col_type_marker.sql_type,
            "primary_key": info.has("primary_key"),
            "not_null": info.has("not_null"),
            "unique": info.has("unique"),
        }

        if info.has("primary_key"):
            col["auto_increment"] = info.get("primary_key").auto_increment

        default_marker = info.get("default")
        if default_marker:
            col["default"] = default_marker.value

        check_marker = info.get("check")
        if check_marker:
            col["check"] = check_marker.expression

        fk_marker = info.get("foreign_key")
        if fk_marker:
            col["references"] = {
                "table": get_table_name_for(fk_marker.to),
                "column": fk_marker.column,
                "on_delete": fk_marker.on_delete,
                "on_update": fk_marker.on_update,
            }

        columns.append(col)
    return columns


def get_table_name_for(class_name: str) -> str:
    """Get table name for a class by name lookup in registry."""
    for cls in Entity.subclasses():
        if cls.__name__ == class_name:
            return get_table_name(cls)
    return class_name.lower() + "s"


def extract_indexes(cls: type) -> list[dict[str, Any]]:
    """Extract index definitions from a model class."""
    indexes = []
    for name, info in cls.indexed.items():
        marker = info.get("indexed")
        idx = {
            "column": name,
            "unique": marker.unique,
        }
        if marker.name:
            idx["name"] = marker.name
        indexes.append(idx)
    return indexes


def extract_relationships(cls: type) -> dict[str, list[dict[str, Any]]]:
    """Extract relationship metadata from a model class."""
    rels: dict[str, list[dict[str, Any]]] = {
        "one_to_one": [],
        "one_to_many": [],
        "many_to_many": [],
    }

    for name, info in cls.fields.items():
        oto = info.get("one_to_one")
        if oto:
            rels["one_to_one"].append(
                {
                    "field": name,
                    "to": oto.to,
                    "foreign_key": oto.foreign_key,
                }
            )

        otm = info.get("one_to_many")
        if otm:
            rels["one_to_many"].append(
                {
                    "field": name,
                    "to": otm.to,
                    "foreign_key": otm.foreign_key,
                }
            )

        mtm = info.get("many_to_many")
        if mtm:
            rels["many_to_many"].append(
                {
                    "field": name,
                    "to": mtm.to,
                    "through": mtm.through,
                    "local_key": mtm.local_key,
                    "remote_key": mtm.remote_key,
                }
            )

    return rels


def extract_junction_tables(registry_cls: type) -> list[dict[str, Any]]:
    """Extract junction table definitions from all many-to-many relationships."""
    tables = []
    seen = set()

    for cls in registry_cls.subclasses():
        for _name, info in cls.fields.items():
            mtm = info.get("many_to_many")
            if mtm and mtm.through not in seen:
                seen.add(mtm.through)
                tables.append(
                    {
                        "table": mtm.through,
                        "columns": [
                            {
                                "name": f"{get_table_name(cls).rstrip('s')}_id",
                                "sql_type": "INTEGER",
                                "references": get_table_name(cls),
                            },
                            {
                                "name": f"{mtm.to.lower()}_id",
                                "sql_type": "INTEGER",
                                "references": get_table_name_for(mtm.to),
                            },
                        ],
                        "primary_key": [
                            f"{get_table_name(cls).rstrip('s')}_id",
                            f"{mtm.to.lower()}_id",
                        ],
                    }
                )

    return tables


def generate_create_sql(cls: type) -> str:
    """Generate CREATE TABLE SQL from model metadata."""
    table = get_table_name(cls)
    columns = extract_columns(cls)
    indexes = extract_indexes(cls)

    lines = []
    for col in columns:
        parts = [f"  {col['name']} {col['sql_type']}"]
        if col.get("primary_key"):
            parts.append("PRIMARY KEY")
        if col.get("not_null") and not col.get("primary_key"):
            parts.append("NOT NULL")
        if col.get("unique") and not col.get("primary_key"):
            parts.append("UNIQUE")
        if "default" in col:
            parts.append(f"DEFAULT {col['default']}")
        if "check" in col:
            parts.append(f"CHECK ({col['check']})")
        if "references" in col:
            ref = col["references"]
            parts.append(f"REFERENCES {ref['table']}({ref['column']})")
            parts.append(f"ON DELETE {ref['on_delete']}")
        lines.append(" ".join(parts))

    sql = f"CREATE TABLE {table} (\n"
    sql += ",\n".join(lines)
    sql += "\n);\n"

    for idx in indexes:
        unique = "UNIQUE " if idx["unique"] else ""
        idx_name = idx.get("name") or f"idx_{table}_{idx['column']}"
        sql += f"CREATE {unique}INDEX {idx_name} ON {table}({idx['column']});\n"

    return sql


# ===================================================================
# 5. Output
# ===================================================================

print("=" * 70)
print("REGISTERED ENTITIES")
print("=" * 70)
for cls in Entity.subclasses():
    print(f"  {cls.__name__} -> {get_table_name(cls)}")

print(f"\n{'=' * 70}")
print("TABLE DEFINITIONS")
print("=" * 70)

for cls in Entity.subclasses():
    print(f"\n--- {cls.__name__} ---")
    columns = extract_columns(cls)
    for col in columns:
        parts = [f"  {col['name']:20s} {col['sql_type']:15s}"]
        flags = []
        if col.get("primary_key"):
            flags.append("PK")
        if col.get("not_null"):
            flags.append("NOT NULL")
        if col.get("unique"):
            flags.append("UNIQUE")
        if "default" in col:
            flags.append(f"DEFAULT={col['default']}")
        if "references" in col:
            ref = col["references"]
            flags.append(f"FK->{ref['table']}.{ref['column']}")
        if flags:
            parts.append(f"  [{', '.join(flags)}]")
        print("".join(parts))

print(f"\n{'=' * 70}")
print("RELATIONSHIPS")
print("=" * 70)

for cls in Entity.subclasses():
    rels = extract_relationships(cls)
    has_rels = any(v for v in rels.values())
    if not has_rels:
        continue

    print(f"\n--- {cls.__name__} ---")
    for oto in rels["one_to_one"]:
        print(f"  {oto['field']:20s} OneToOne  -> {oto['to']} (via {oto['foreign_key']})")
    for otm in rels["one_to_many"]:
        print(f"  {otm['field']:20s} OneToMany -> {otm['to']} (via {otm['foreign_key']})")
    for mtm in rels["many_to_many"]:
        print(f"  {mtm['field']:20s} ManyToMany -> {mtm['to']} (through {mtm['through']})")

print(f"\n{'=' * 70}")
print("JUNCTION TABLES")
print("=" * 70)

for jt in extract_junction_tables(Entity):
    print(f"\n--- {jt['table']} ---")
    for col in jt["columns"]:
        print(f"  {col['name']:20s} {col['sql_type']:15s}  FK->{col['references']}")
    print(f"  PRIMARY KEY: ({', '.join(jt['primary_key'])})")

print(f"\n{'=' * 70}")
print("INDEXES")
print("=" * 70)

for cls in Entity.subclasses():
    indexes = extract_indexes(cls)
    if indexes:
        print(f"\n--- {cls.__name__} ---")
        for idx in indexes:
            unique = "UNIQUE " if idx["unique"] else ""
            print(f"  {unique}INDEX on {idx['column']}")

print(f"\n{'=' * 70}")
print("CROSS-ENTITY QUERIES VIA .all")
print("=" * 70)

print("\nAll foreign keys in the system:")
for name, infos in Entity.all.foreign_key.items():
    for info in infos:
        fk = info.get("foreign_key")
        print(f"  {info.owner.__name__}.{name} -> {fk.to}({fk.column}) ON DELETE {fk.on_delete}")

print("\nAll unique constraints:")
for name, infos in Entity.all.unique.items():
    owners = [i.owner.__name__ for i in infos]
    print(f"  {name}: {owners}")

print("\nAll NOT NULL columns:")
for name, infos in Entity.all.not_null.items():
    owners = [i.owner.__name__ for i in infos]
    print(f"  {name}: {owners}")

print(f"\n{'=' * 70}")
print("GENERATED SQL")
print("=" * 70)

for cls in Entity.subclasses():
    print()
    print(generate_create_sql(cls))
