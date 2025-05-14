from typing import Callable, Dict, Iterable, List, Optional

from llama_index.core.schema import Document
from llama_index.core.readers.base import BaseReader
from llama_index.core.tools.tool_spec.base import BaseToolSpec
from llama_hub.tools.database.base import DatabaseToolSpec
from sqlalchemy import text
from sqlalchemy.exc import InvalidRequestError


class NoSuchDatabaseError(InvalidRequestError):
    """Database does not exist or is not visible to a connection."""


class TrackingDatabaseToolSpec(DatabaseToolSpec):
    """
    Subclass of DatabaseToolSpec with support for handler tracking.
    """
    handler: Optional[Callable[[str, str, Iterable], None]] = None
    database_name: Optional[str] = None

    def __init__(self, uri: str):
        super().__init__(uri=uri)
        self.handler = None
        self.database_name = None

    def set_handler(self, func: Callable[[str, str, Iterable], None]) -> None:
        self.handler = func

    def set_database_name(self, database_name: str) -> None:
        self.database_name = database_name

    def load_data(self, query: str) -> List[Document]:
        """Query and load data from the database, returning a list of Documents."""
        if not query:
            raise ValueError("Query must be provided to load data.")

        documents = []
        with self.sql_database.engine.connect() as connection:
            result = connection.execute(text(query))
            items = result.fetchall()

            if self.handler:
                self.handler(self.database_name, query, items)

            for item in items:
                doc_str = ", ".join([str(entry) for entry in item])
                documents.append(Document(text=doc_str))

        return documents


class MultiDatabaseToolSpec(BaseToolSpec, BaseReader):
    """
    Custom tool spec for managing and querying multiple databases at once.
    """
    database_specs: Dict[str, TrackingDatabaseToolSpec]
    handler: Optional[Callable[[str, str, Iterable], None]]

    spec_functions = ["load_data", "describe_tables", "list_tables", "list_databases"]

    def __init__(
        self,
        database_toolspec_mapping: Optional[Dict[str, TrackingDatabaseToolSpec]] = None,
        handler: Optional[Callable[[str, str, Iterable], None]] = None,
    ) -> None:
        self.database_specs = database_toolspec_mapping or {}
        self.handler = handler

        for spec in self.database_specs.values():
            spec.set_handler(self.handler)

    def add_connection(self, database_name: str, uri: str) -> None:
        spec = TrackingDatabaseToolSpec(uri=uri)
        spec.set_handler(self.handler)
        spec.set_database_name(database_name)
        self.database_specs[database_name] = spec

    def add_database_tool_spec(self, database_name: str, tool_spec: TrackingDatabaseToolSpec) -> None:
        tool_spec.set_handler(self.handler)
        tool_spec.set_database_name(database_name)
        self.database_specs[database_name] = tool_spec

    def load_data(self, database: str, query: str) -> List[Document]:
        if database not in self.database_specs:
            raise NoSuchDatabaseError(f"Database '{database}' does not exist.")
        return self.database_specs[database].load_data(query)

    def describe_tables(self, database: str, tables: Optional[List[str]] = None) -> str:
        if database not in self.database_specs:
            raise NoSuchDatabaseError(f"Database '{database}' does not exist.")
        return self.database_specs[database].describe_tables(tables)

    def list_tables(self, database: str) -> List[str]:
        if database not in self.database_specs:
            raise NoSuchDatabaseError(f"Database '{database}' does not exist.")
        return self.database_specs[database].list_tables()

    def list_databases(self) -> List[str]:
        return list(self.database_specs.keys())
    
    def from_conversation(self, conversation) -> "MultiDatabaseToolSpec":
        """
        Load all database URIs from a Conversation object.
        """
        for db_id in conversation.database_ids:
            uri = conversation.get_database_uri(db_id)
            self.add_connection(database_name=db_id, uri=uri)
        return self
    
