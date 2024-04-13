
from langchain.chains import RetrievalQA
from langchain.vectorstores import Chroma



#ollama/main.py
#0410 RAG_EMBEDDING_MODEL_DEVICE_TYPE, RAG_EMBEDDING_MODEL ADD
from config import SRC_LOG_LEVELS, OLLAMA_BASE_URLS, MODEL_FILTER_ENABLED, MODEL_FILTER_LIST, UPLOAD_DIR, RAG_EMBEDDING_MODEL_DEVICE_TYPE, RAG_EMBEDDING_MODEL
#0410
from chromadb.utils import embedding_functions
#0410
from langchain.vectorstores import Chroma

#0413
#0413
# CHROMA_CLIENT
# config.py에 선언된 전역 변수


#통합
#0410 RAG_EMBEDDING_MODEL_DEVICE_TYPE, RAG_EMBEDDING_MODEL, CHROMA_CLIENT ADD 
#0410
from langchain.vectorstores import Chroma
from config import SRC_LOG_LEVELS, OLLAMA_BASE_URLS, MODEL_FILTER_ENABLED, MODEL_FILTER_LIST, UPLOAD_DIR, RAG_EMBEDDING_MODEL_DEVICE_TYPE, RAG_EMBEDDING_MODEL, CHROMA_CLIENT
from utils.misc import calculate_sha256
from langchain.embeddings import SentenceTransformerEmbeddings
from chromadb.utils import embedding_functions


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





#0413
#ollama/main.py
            #log.info(f"form_data.model_dump_json(exclude_none=True) > {form_data.model_dump_json(exclude_none=True)}")

            #log.info(f"form_data> > > {form_data}")
            # form_data 객체에서 딕셔너리 데이터를 가져옴
            form_dict = form_data.dict()

            user_messages = [msg for msg in form_dict['messages'] if msg['role'] == 'user']
            if user_messages:  # user_messages 리스트가 비어있지 않은 경우에만 실행
                last_user_content = user_messages[-1]['content']
                log.info(f"last_user_content >> {last_user_content}")
            else:
                log.info("No user messages found")

            #0410 check1
            #client = chromadb.PersistentClient(path="../../data/uploads")    
            # collection = client.get_or_create_collection(
            #     name="All-Documents"
            # )
            #     # DB 쿼리
            # collection.query(
            #     query_texts=["user_messages"],
            #     n_results=5,
            # )
            #0410
            #../../data/vector_db'
            #log.info("1")
            #embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
            #persist_directory = '/Users/kimjunhyeok/Desktop/Visual Studio Code/open-webui/open-webui/backend/data/test_vector_db'
            #persist_directory = '/Users/kimjunhyeok/Desktop/Visual Studio Code/open-webui/open-webui/backend/data/vector_db'
            #vectordb = Chroma(persist_directory=persist_directory, embedding_function=embedding_function)
            #vectordb = chromadb.PersistentClient(path=persist_directory)

            #0413
            chromadb = CHROMA_CLIENT
            collections = chromadb.list_collections()
            # 최소 거리의 초기값을 무한대로 설정합니다.
            min_distance = float('inf')
            # 최소 거리에 해당하는 결과를 저장할 변수를 초기화합니다.
            min_result = None
            # 최소 거리를 가진 컬렉션의 이름을 저장할 변수를 초기화합니다.
            min_collection_name = ''

            for collection in collections:
                collection_name = collection.name
    
                # 해당 이름을 사용하여 컬렉션 인스턴스를 가져옵니다.
                collection_instance = chromadb.get_collection(collection_name)
                result = collection_instance.query(
                    query_texts=[user_messages],
                    n_results=5,
                )

                log.info(f"Results for collection {collection_name}: {result}")
                # 결과에서 distances의 값이 가장 작은지 확인합니다.
                if result['distances'] and result['distances'][0]:
                    if result['distances'][0][0] < min_distance:
                        # 현재 결과의 거리가 더 작다면, 최소값을 업데이트합니다.
                        min_distance = result['distances'][0][0]
                        min_result = result
                        min_collection_name = collection_name
                    log.info(f"Results for collection {collection_name}: {result}")
    
            log.info("######################## MIN DISTANCE ############################# \n\n\n\n\n")
            collection_instance = chromadb.get_collection(min_collection_name)
            result = collection_instance.query(
                    query_texts=[user_messages],
                    n_results=5,
            )
            log.info(f"Results for collection {collection_name}: {result}")
            log.info("######################## MIN DISTANCE ############################# \n\n\n\n\n")

            # DB 쿼리
            #retriever = chromadb.as_retriever()
            #result = retriever.invoke("일산")
            #docs = retriever.get_relevant_documents("일산")
            # for doc in docs:
            #     log.info(doc.metadata["source"])
            # embedding_vector = embedding_function.embed_query("일산")
            # docs = vectordb.similarity_search_by_vector(embedding_vector)
            #log.info(f"docs >>>>>>> {docs}")