@app.post("/api/chat")
@app.post("/api/chat/{url_idx}")
async def generate_chat_completion(
    form_data: GenerateChatCompletionForm,
    url_idx: Optional[int] = None,
    user=Depends(get_current_user),
):

    if url_idx == None:
        if form_data.model in app.state.MODELS:
            url_idx = random.choice(app.state.MODELS[form_data.model]["urls"])
        else:
            raise HTTPException(
                status_code=400,
                detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.model),
            )

    url = app.state.OLLAMA_BASE_URLS[url_idx]
    log.info(f"url: {url}")

    r = None

    log.debug("form_data.model_dump_json(exclude_none=True).encode(): {0} ".format(form_data.model_dump_json(exclude_none=True).encode()))

    def get_request():
        nonlocal form_data
        nonlocal r

        request_id = str(uuid.uuid4())
        try:
            REQUEST_POOL.append(request_id)

            def stream_content():
                try:
                    if form_data.stream:
                        yield json.dumps({"id": request_id, "done": False}) + "\n"

                    for chunk in r.iter_content(chunk_size=8192):
                        if request_id in REQUEST_POOL:
                            yield chunk
                        else:
                            log.warning("User: canceled request")
                            break
                finally:
                    if hasattr(r, "close"):
                        r.close()
                        if request_id in REQUEST_POOL:
                            REQUEST_POOL.remove(request_id)

            #log.info(f"form_data.model_dump_json(exclude_none=True) > {form_data.model_dump_json(exclude_none=True)}")

            #log.info(f"form_data> > > {form_data}")
            # form_data 객체에서 딕셔너리 데이터를 가져옴
            form_dict = form_data.dict()
            last_user_content = ''
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
                    query_texts=[last_user_content],
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
                    query_texts=[last_user_content],
                    n_results=5,
            )
            log.info(f"Results for collection {collection_name}: {result}")
            log.info("######################## MIN DISTANCE ############################# \n\n\n\n\n")

            extracted_documents = result['documents'][0][0]

            new_chat_message = ChatMessage(role='assistant', content=extracted_documents, images=None)
            log.info(extracted_documents)
            # DB 쿼리
            #retriever = chromadb.as_retriever()
            #result = retriever.invoke("일산")
            #docs = retriever.get_relevant_documents("일산")
            # for doc in docs:
            #     log.info(doc.metadata["source"])
            # embedding_vector = embedding_function.embed_query("일산")
            # docs = vectordb.similarity_search_by_vector(embedding_vector)
            #log.info(f"docs >>>>>>> {docs}")

            log.info("################ form_data ASIS ####################\n\n\n\n\n")
            log.info(form_data.messages)
            form_data.messages.append(new_chat_message)
            log.info("################ form_data TOBE ####################\n\n\n\n\n")
            log.info(form_data.messages)
            
            r = requests.request(
                method="POST",
                url=f"{url}/api/chat",
                data=form_data.model_dump_json(exclude_none=True).encode(),
                stream=True,
            )

            r.raise_for_status()

            return StreamingResponse(
                stream_content(),
                status_code=r.status_code,
                headers=dict(r.headers),
            )
        except Exception as e:
            log.exception(e)
            raise e

    try:
        return await run_in_threadpool(get_request)
    except Exception as e:
        error_detail = "Open WebUI: Server Connection Error"
        if r is not None:
            try:
                res = r.json()
                if "error" in res:
                    error_detail = f"Ollama: {res['error']}"
            except:
                error_detail = f"Ollama: {e}"

        raise HTTPException(
            status_code=r.status_code if r else 500,
            detail=error_detail,
        )