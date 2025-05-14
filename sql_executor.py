from sqlalchemy import create_engine, text

def safe_sql_result(uri: str, query: str):
    if not query.strip().lower().startswith("select"):
        return "❌ Hanya query SELECT yang diizinkan."
    
    try:
        engine = create_engine(uri)
        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchall()
            headers = result.keys()
            return [dict(zip(headers, row)) for row in rows]
    except Exception as e:
        return f"❌ Error saat eksekusi query: {e}"
