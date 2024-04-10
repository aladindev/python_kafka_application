
from langchain.chains import RetrievalQA
from langchain.vectorstores import Chroma



#ollama/main.py
#0410 RAG_EMBEDDING_MODEL_DEVICE_TYPE, RAG_EMBEDDING_MODEL ADD
from config import SRC_LOG_LEVELS, OLLAMA_BASE_URLS, MODEL_FILTER_ENABLED, MODEL_FILTER_LIST, UPLOAD_DIR, RAG_EMBEDDING_MODEL_DEVICE_TYPE, RAG_EMBEDDING_MODEL
#0410
from chromadb.utils import embedding_functions
#0410
from langchain.vectorstores import Chroma

#0410
app.state.RAG_EMBEDDING_MODEL = RAG_EMBEDDING_MODEL
app.state.sentence_transformer_ef = (
    embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=app.state.RAG_EMBEDDING_MODEL,
        device=RAG_EMBEDDING_MODEL_DEVICE_TYPE,
    )
)

#0410
vectordb = Chroma(persist_directory='../../data/vector_db', embedding_function=app.state.sentence_transformer_ef)
retriever = vectordb.as_retriever()

docs = retriever.get_relevant_documents("ask Text")

for doc in docs:
    log.info(doc.metadata["source"])


# loader = TextLoader('single_text_file.txt')
loader = DirectoryLoader('./articles', glob="*.txt", loader_cls=TextLoader)
documents = loader.load()

len(documents)



vectordb = chroma(persist_directory=persist_directory, embedding_function=embedding)
retriever = vectordb.as_retriever()


docs = retriever.get_relevant_documents("ask Text")

for doc in docs:
     print(doc.metadata["source"])













# 
#

# retriever 


log.info(f"form_data.model_dump_json(exclude_none=True) > {form_data.model_dump_json(exclude_none=True)}")

log.info(f"form_data> > > {form_data}")
# form_data 객체에서 딕셔너리 데이터를 가져옴
form_dict = form_data.dict()

user_messages = [msg for msg in form_dict['messages'] if msg['role'] == 'user']
if user_messages:  # user_messages 리스트가 비어있지 않은 경우에만 실행
    last_user_content = user_messages[-1]['content']
    log.info(f"last_user_content >> {last_user_content}")
else:
    log.info("No user messages found")


from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
model_name = "jhgan/ko-sroberta-multitask" # (KorNLU 데이터셋에 학습시킨 한국어 임베딩 모델)
model_kwargs = {'device': 'cpu'}
encode_kwargs = {'normalize_embeddings': False}
embedding_model = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs
)
db3 = Chroma(persist_directory="./chroma_db", embedding_function=form_data.model)
docs = db3.similarity_search(last_user_content)
log.info(f"docs >>>  {docs}")

