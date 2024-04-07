
log.info(f"form_data.model_dump_json(exclude_none=True) > {form_data.model_dump_json(exclude_none=True)}")

log.info(f"form_data> > > {form_data}")

user_messages = [msg for msg in form_data['messages'] if msg['role'] == 'user']
if user_messages:  # user_messages 리스트가 비어있지 않은 경우에만 실행
    last_user_content = user_messages[-1]['content']
    log.info(f"last_user_content >> {last_user_content}")
else:
    log.info("No user messages found")


from langchain.vectorstores import Chroma
db3 = Chroma(persist_directory="./chroma_db", embedding_function=form_data.model)
docs = db3.similarity_search(last_user_content)
log.info(f"docs >>>  {docs}")

