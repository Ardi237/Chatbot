from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.embeddings.openai import OpenAIEmbedding
# from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core import StorageContext

def index_uploaded_files(folder_path="uploads"):
    documents = SimpleDirectoryReader(folder_path).load_data()

    vector_store = ChromaVectorStore(persist_dir="file_vector")
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        embed_model=OpenAIEmbedding(),
    )

    index.storage_context.persist()
    return index
