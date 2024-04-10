
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

