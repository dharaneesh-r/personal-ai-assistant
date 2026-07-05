import sqlite3
import os
from contextlib import contextmanager
from typing import Any, Dict, List

DB_PATH = "data/knowledge_graph.db"


@contextmanager
def get_db_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                source TEXT NOT NULL,
                UNIQUE(name, source)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_entity TEXT NOT NULL,
                target_entity TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                description TEXT,
                source TEXT NOT NULL,
                UNIQUE(source_entity, target_entity, relation_type, source)
            )
        """)


def add_entities_and_relations(
    entities: List[Dict[str, Any]],
    relations: List[Dict[str, Any]],
    source: str
):
    init_db()
    with get_db_conn() as conn:
        # Insert entities
        for ent in entities:
            name = ent.get("name", "").strip()
            ent_type = ent.get("type", "concept").strip()
            desc = ent.get("description", "").strip()
            if not name:
                continue
            conn.execute(
                """
                INSERT INTO entities (name, type, description, source)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name, source) DO UPDATE SET
                    type=excluded.type,
                    description=excluded.description
                """,
                (name, ent_type, desc, source)
            )

        # Insert relations
        for rel in relations:
            src_ent = rel.get("source", "").strip()
            tgt_ent = rel.get("target", "").strip()
            rel_type = rel.get("type", "").strip()
            desc = rel.get("description", "").strip()
            if not src_ent or not tgt_ent or not rel_type:
                continue
            conn.execute(
                """
                INSERT INTO relations (source_entity, target_entity, relation_type, description, source)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_entity, target_entity, relation_type, source) DO UPDATE SET
                    description=excluded.description
                """,
                (src_ent, tgt_ent, rel_type, desc, source)
            )


def delete_source_graph(source: str) -> int:
    init_db()
    deleted_count = 0
    with get_db_conn() as conn:
        r1 = conn.execute("DELETE FROM entities WHERE source = ?", (source,))
        r2 = conn.execute("DELETE FROM relations WHERE source = ?", (source,))
        deleted_count = r1.rowcount + r2.rowcount
    return deleted_count


def clear_graph():
    init_db()
    with get_db_conn() as conn:
        conn.execute("DELETE FROM entities")
        conn.execute("DELETE FROM relations")


def get_all_graph() -> Dict[str, List[Dict[str, Any]]]:
    init_db()
    with get_db_conn() as conn:
        entities_cursor = conn.execute("SELECT name, type, description, source FROM entities")
        relations_cursor = conn.execute("SELECT source_entity, target_entity, relation_type, description, source FROM relations")
        
        nodes = []
        # Deduplicate nodes by name across multiple sources if they exist, but keep info
        seen_nodes = {}
        for row in entities_cursor:
            name = row["name"]
            if name not in seen_nodes:
                seen_nodes[name] = {
                    "id": name,
                    "label": name,
                    "type": row["type"],
                    "description": row["description"] or "",
                    "sources": [row["source"]]
                }
            else:
                if row["source"] not in seen_nodes[name]["sources"]:
                    seen_nodes[name]["sources"].append(row["source"])
                # Prefer non-empty descriptions
                if not seen_nodes[name]["description"] and row["description"]:
                    seen_nodes[name]["description"] = row["description"]

        nodes = list(seen_nodes.values())
        
        edges = []
        for row in relations_cursor:
            edges.append({
                "source": row["source_entity"],
                "target": row["target_entity"],
                "type": row["relation_type"],
                "description": row["description"] or "",
                "source_file": row["source"]
            })
            
    return {"nodes": nodes, "links": edges}


def get_neighborhood(entity_names: List[str], max_facts: int = 15) -> Dict[str, Any]:
    """Retrieves 1-hop relation descriptions and their sources for given entities to build RAG context."""
    if not entity_names:
        return {"facts": [], "sources": []}
    
    init_db()
    facts = []
    sources = set()
    
    # Sanitize and prepare search terms
    terms = [name.strip().lower() for name in entity_names if name.strip()]
    if not terms:
        return {"facts": [], "sources": []}

    # Map name placeholders to SQL query
    placeholders = ",".join(["?"] * len(terms))
    
    with get_db_conn() as conn:
        # Get relations where query entities are either source or target
        query = f"""
            SELECT source_entity, target_entity, relation_type, description, source
            FROM relations
            WHERE LOWER(source_entity) IN ({placeholders}) OR LOWER(target_entity) IN ({placeholders})
            LIMIT ?
        """
        params = terms + terms + [max_facts]
        cursor = conn.execute(query, params)
        
        for row in cursor:
            src = row["source_entity"]
            tgt = row["target_entity"]
            rel = row["relation_type"]
            desc = row["description"]
            source = row["source"]
            
            fact = f"- {src} ({rel}) {tgt}"
            if desc:
                fact += f": {desc}"
            facts.append(fact)
            if source:
                sources.add(source)
            
    return {"facts": facts, "sources": list(sources)}
