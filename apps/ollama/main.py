
from langchain.vectorstores import Chroma
log.info(f"form_data> > > {form_data}")
db3 = Chroma(persist_directory="./chroma_db", embedding_function=embedding_model)
docs = db3.similarity_search(query)
log.info(f"docs >>>  {docs}")