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


            #s 0414
            form_dict = form_data.dict()
            last_user_content = ''
            user_messages = [msg for msg in form_dict['messages'] if msg['role'] == 'user']
            if user_messages:
                last_user_content = user_messages[-1]['content']
                log.info(f"last_user_content >> {last_user_content}")
            else:
                log.info("No user messages found")

            chromadb = CHROMA_CLIENT

            collections = chromadb.list_collections()
            min_distance = float('inf')
            min_result = None
            min_collection_name = ''

            for collection in collections:
                collection_name = collection.name
    
                collection_instance = chromadb.get_collection(collection_name)
                result = collection_instance.query(
                    query_texts=[last_user_content],
                    n_results=5,
                )

                if result['distances'] and result['distances'][0]:
                    if result['distances'][0][0] < min_distance:
                        min_distance = result['distances'][0][0]
                        min_result = result
                        min_collection_name = collection_name
    
            if min_distance < 1 :
                collection_instance = chromadb.get_collection(min_collection_name)
                result = collection_instance.query(
                        query_texts=[last_user_content],
                        n_results=5,
                )
                extracted_documents = result['documents'][0][0]
                final_content = "내부에서 배운 지식으로 다음 컨텍스트를 사용하십시오. <context></context> XML tags.\n<context>\n"
                final_content += extracted_documents
                final_content += "\n\n</context>\n\n너가 유저에게 대답할 때 :\n-반드시 한국어로 대답해라. 만약 너가 잘 모르겠으면 모르겠다고 답해라.\n- 확실하지 않을 때 유저에게 명확하게 설명을 요청하세요.\n-맥락에서 정보를 얻었음을 언급하지 마세요.\n그리고 반드시 한국어로 대답합니다.\n        \n컨텍스트 정보를 바탕으로 쿼리에 답하세요.\n쿼리: "
                final_content += last_user_content

                new_chat_message = ChatMessage(role='user', content=final_content, images=None)
                log.info("\n######################## result ################### \n")
                log.info(f"{extracted_documents}")
                log.info("\n ######################## result  ###################")


                form_data.messages.append(new_chat_message)

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
