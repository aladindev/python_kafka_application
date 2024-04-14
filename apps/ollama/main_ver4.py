from fastapi import (
    FastAPI,
    Request,
    Response,
    HTTPException,
    Depends,
    status,
    UploadFile,
    File,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool

from pydantic import BaseModel, ConfigDict







import os
import copy
import random
import requests
import json
import uuid
import aiohttp
import asyncio
import logging
from urllib.parse import urlparse
from typing import Optional, List, Union


from apps.web.models.users import Users
from constants import ERROR_MESSAGES
from utils.utils import decode_token, get_current_user, get_admin_user


#0410 RAG_EMBEDDING_MODEL_DEVICE_TYPE, RAG_EMBEDDING_MODEL, CHROMA_CLIENT ADD 
from config import SRC_LOG_LEVELS, OLLAMA_BASE_URLS, MODEL_FILTER_ENABLED, MODEL_FILTER_LIST, UPLOAD_DIR, RAG_EMBEDDING_MODEL_DEVICE_TYPE, RAG_EMBEDDING_MODEL, CHROMA_CLIENT
from utils.misc import calculate_sha256


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["OLLAMA"])

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.MODEL_FILTER_ENABLED = MODEL_FILTER_ENABLED
app.state.MODEL_FILTER_LIST = MODEL_FILTER_LIST

app.state.OLLAMA_BASE_URLS = OLLAMA_BASE_URLS
app.state.MODELS = {}


REQUEST_POOL = []


# TODO: Implement a more intelligent load balancing mechanism for distributing requests among multiple backend instances.
# Current implementation uses a simple round-robin approach (random.choice). Consider incorporating algorithms like weighted round-robin,
# least connections, or least response time for better resource utilization and performance optimization.


@app.middleware("http")
async def check_url(request: Request, call_next):
    if len(app.state.MODELS) == 0:
        await get_all_models()
    else:
        pass

    response = await call_next(request)
    return response


@app.get("/urls")
async def get_ollama_api_urls(user=Depends(get_admin_user)):
    return {"OLLAMA_BASE_URLS": app.state.OLLAMA_BASE_URLS}


class UrlUpdateForm(BaseModel):
    urls: List[str]


@app.post("/urls/update")
async def update_ollama_api_url(form_data: UrlUpdateForm, user=Depends(get_admin_user)):
    app.state.OLLAMA_BASE_URLS = form_data.urls

    log.info(f"app.state.OLLAMA_BASE_URLS: {app.state.OLLAMA_BASE_URLS}")
    return {"OLLAMA_BASE_URLS": app.state.OLLAMA_BASE_URLS}


@app.get("/cancel/{request_id}")
async def cancel_ollama_request(request_id: str, user=Depends(get_current_user)):
    if user:
        if request_id in REQUEST_POOL:
            REQUEST_POOL.remove(request_id)
        return True
    else:
        raise HTTPException(status_code=401, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)


async def fetch_url(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()
    except Exception as e:
        # Handle connection error here
        log.error(f"Connection error: {e}")
        return None


def merge_models_lists(model_lists):
    merged_models = {}

    for idx, model_list in enumerate(model_lists):
        if model_list is not None:
            for model in model_list:
                digest = model["digest"]
                if digest not in merged_models:
                    model["urls"] = [idx]
                    merged_models[digest] = model
                else:
                    merged_models[digest]["urls"].append(idx)

    return list(merged_models.values())


# user=Depends(get_current_user)


async def get_all_models():
    log.info("get_all_models()")
    tasks = [fetch_url(f"{url}/api/tags") for url in app.state.OLLAMA_BASE_URLS]
    responses = await asyncio.gather(*tasks)

    models = {
        "models": merge_models_lists(
            map(lambda response: response["models"] if response else None, responses)
        )
    }

    app.state.MODELS = {model["model"]: model for model in models["models"]}

    return models


@app.get("/api/tags")
@app.get("/api/tags/{url_idx}")
async def get_ollama_tags(
    url_idx: Optional[int] = None, user=Depends(get_current_user)
):
    if url_idx == None:
        models = await get_all_models()

        if app.state.MODEL_FILTER_ENABLED:
            if user.role == "user":
                models["models"] = list(
                    filter(
                        lambda model: model["name"] in app.state.MODEL_FILTER_LIST,
                        models["models"],
                    )
                )
                return models
        return models
    else:
        url = app.state.OLLAMA_BASE_URLS[url_idx]
        try:
            r = requests.request(method="GET", url=f"{url}/api/tags")
            r.raise_for_status()

            return r.json()
        except Exception as e:
            log.exception(e)
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


@app.get("/api/version")
@app.get("/api/version/{url_idx}")
async def get_ollama_versions(url_idx: Optional[int] = None):

    if url_idx == None:

        # returns lowest version
        tasks = [fetch_url(f"{url}/api/version") for url in app.state.OLLAMA_BASE_URLS]
        responses = await asyncio.gather(*tasks)
        responses = list(filter(lambda x: x is not None, responses))

        if len(responses) > 0:
            lowest_version = min(
                responses, key=lambda x: tuple(map(int, x["version"].split(".")))
            )

            return {"version": lowest_version["version"]}
        else:
            raise HTTPException(
                status_code=500,
                detail=ERROR_MESSAGES.OLLAMA_NOT_FOUND,
            )
    else:
        url = app.state.OLLAMA_BASE_URLS[url_idx]
        try:
            r = requests.request(method="GET", url=f"{url}/api/version")
            r.raise_for_status()

            return r.json()
        except Exception as e:
            log.exception(e)
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


class ModelNameForm(BaseModel):
    name: str


@app.post("/api/pull")
@app.post("/api/pull/{url_idx}")
async def pull_model(
    form_data: ModelNameForm, url_idx: int = 0, user=Depends(get_admin_user)
):
    url = app.state.OLLAMA_BASE_URLS[url_idx]
    log.info(f"url: {url}")

    r = None

    def get_request():
        nonlocal url
        nonlocal r

        request_id = str(uuid.uuid4())
        try:
            REQUEST_POOL.append(request_id)

            def stream_content():
                try:
                    yield json.dumps({"id": request_id, "done": False}) + "\n"

                    for chunk in r.iter_content(chunk_size=8192):
                        if request_id in REQUEST_POOL:
                            yield chunk
                        else:
                            print("User: canceled request")
                            break
                finally:
                    if hasattr(r, "close"):
                        r.close()
                        if request_id in REQUEST_POOL:
                            REQUEST_POOL.remove(request_id)

            r = requests.request(
                method="POST",
                url=f"{url}/api/pull",
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
            raise e

    try:
        return await run_in_threadpool(get_request)

    except Exception as e:
        log.exception(e)
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


class PushModelForm(BaseModel):
    name: str
    insecure: Optional[bool] = None
    stream: Optional[bool] = None


@app.delete("/api/push")
@app.delete("/api/push/{url_idx}")
async def push_model(
    form_data: PushModelForm,
    url_idx: Optional[int] = None,
    user=Depends(get_admin_user),
):
    if url_idx == None:
        if form_data.name in app.state.MODELS:
            url_idx = app.state.MODELS[form_data.name]["urls"][0]
        else:
            raise HTTPException(
                status_code=400,
                detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.name),
            )

    url = app.state.OLLAMA_BASE_URLS[url_idx]
    log.debug(f"url: {url}")

    r = None

    def get_request():
        nonlocal url
        nonlocal r
        try:

            def stream_content():
                for chunk in r.iter_content(chunk_size=8192):
                    yield chunk

            r = requests.request(
                method="POST",
                url=f"{url}/api/push",
                data=form_data.model_dump_json(exclude_none=True).encode(),
            )

            r.raise_for_status()

            return StreamingResponse(
                stream_content(),
                status_code=r.status_code,
                headers=dict(r.headers),
            )
        except Exception as e:
            raise e

    try:
        return await run_in_threadpool(get_request)
    except Exception as e:
        log.exception(e)
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


class CreateModelForm(BaseModel):
    name: str
    modelfile: Optional[str] = None
    stream: Optional[bool] = None
    path: Optional[str] = None


@app.post("/api/create")
@app.post("/api/create/{url_idx}")
async def create_model(
    form_data: CreateModelForm, url_idx: int = 0, user=Depends(get_admin_user)
):
    log.debug(f"form_data: {form_data}")
    url = app.state.OLLAMA_BASE_URLS[url_idx]
    log.info(f"url: {url}")

    r = None

    def get_request():
        nonlocal url
        nonlocal r
        try:

            def stream_content():
                for chunk in r.iter_content(chunk_size=8192):
                    yield chunk

            r = requests.request(
                method="POST",
                url=f"{url}/api/create",
                data=form_data.model_dump_json(exclude_none=True).encode(),
                stream=True,
            )

            r.raise_for_status()

            log.debug(f"r: {r}")

            return StreamingResponse(
                stream_content(),
                status_code=r.status_code,
                headers=dict(r.headers),
            )
        except Exception as e:
            raise e

    try:
        return await run_in_threadpool(get_request)
    except Exception as e:
        log.exception(e)
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


class CopyModelForm(BaseModel):
    source: str
    destination: str


@app.post("/api/copy")
@app.post("/api/copy/{url_idx}")
async def copy_model(
    form_data: CopyModelForm,
    url_idx: Optional[int] = None,
    user=Depends(get_admin_user),
):
    if url_idx == None:
        if form_data.source in app.state.MODELS:
            url_idx = app.state.MODELS[form_data.source]["urls"][0]
        else:
            raise HTTPException(
                status_code=400,
                detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.source),
            )

    url = app.state.OLLAMA_BASE_URLS[url_idx]
    log.info(f"url: {url}")

    try:
        r = requests.request(
            method="POST",
            url=f"{url}/api/copy",
            data=form_data.model_dump_json(exclude_none=True).encode(),
        )
        r.raise_for_status()

        log.debug(f"r.text: {r.text}")

        return True
    except Exception as e:
        log.exception(e)
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


@app.delete("/api/delete")
@app.delete("/api/delete/{url_idx}")
async def delete_model(
    form_data: ModelNameForm,
    url_idx: Optional[int] = None,
    user=Depends(get_admin_user),
):
    if url_idx == None:
        if form_data.name in app.state.MODELS:
            url_idx = app.state.MODELS[form_data.name]["urls"][0]
        else:
            raise HTTPException(
                status_code=400,
                detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.name),
            )

    url = app.state.OLLAMA_BASE_URLS[url_idx]
    log.info(f"url: {url}")

    try:
        r = requests.request(
            method="DELETE",
            url=f"{url}/api/delete",
            data=form_data.model_dump_json(exclude_none=True).encode(),
        )
        r.raise_for_status()

        log.debug(f"r.text: {r.text}")

        return True
    except Exception as e:
        log.exception(e)
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


@app.post("/api/show")
async def show_model_info(form_data: ModelNameForm, user=Depends(get_current_user)):
    if form_data.name not in app.state.MODELS:
        raise HTTPException(
            status_code=400,
            detail=ERROR_MESSAGES.MODEL_NOT_FOUND(form_data.name),
        )

    url_idx = random.choice(app.state.MODELS[form_data.name]["urls"])
    url = app.state.OLLAMA_BASE_URLS[url_idx]
    log.info(f"url: {url}")

    try:
        r = requests.request(
            method="POST",
            url=f"{url}/api/show",
            data=form_data.model_dump_json(exclude_none=True).encode(),
        )
        r.raise_for_status()

        return r.json()
    except Exception as e:
        log.exception(e)
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


class GenerateEmbeddingsForm(BaseModel):
    model: str
    prompt: str
    options: Optional[dict] = None
    keep_alive: Optional[Union[int, str]] = None


@app.post("/api/embeddings")
@app.post("/api/embeddings/{url_idx}")
async def generate_embeddings(
    form_data: GenerateEmbeddingsForm,
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

    try:
        r = requests.request(
            method="POST",
            url=f"{url}/api/embeddings",
            data=form_data.model_dump_json(exclude_none=True).encode(),
        )
        r.raise_for_status()

        return r.json()
    except Exception as e:
        log.exception(e)
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


class GenerateCompletionForm(BaseModel):
    model: str
    prompt: str
    images: Optional[List[str]] = None
    format: Optional[str] = None
    options: Optional[dict] = None
    system: Optional[str] = None
    template: Optional[str] = None
    context: Optional[str] = None
    stream: Optional[bool] = True
    raw: Optional[bool] = None
    keep_alive: Optional[Union[int, str]] = None


@app.post("/api/generate")
@app.post("/api/generate/{url_idx}")
async def generate_completion(
    form_data: GenerateCompletionForm,
    url_idx: Optional[int] = None,
    user=Depends(get_current_user),
):


    log.info(f"form_data >> {form_data}")
    if url_idx == None:
        if form_data.model in app.state.MODELS:
            url_idx = random.choice(app.state.MODELS[form_data.model]["urls"])
        else:
            raise HTTPException(
                status_code=400,
                detail="error_detail",
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

                # form_data 객체에서 딕셔너리 데이터를 가져옴
                # form_dict = form_data.dict()

                # log.info(f"form_dict >> {form_dict}")

                # user_messages = [msg for msg in form_dict['messages'] if msg['role'] == 'user']
                # if user_messages:  # user_messages 리스트가 비어있지 않은 경우에만 실행
                #     last_user_content = user_messages[-1]['content']
                #     log.info(f"last_user_content >> {last_user_content}")
                # else:
                #     log.info("No user messages found")

                # model_name = "jhgan/ko-sroberta-multitask" # (KorNLU 데이터셋에 학습시킨 한국어 임베딩 모델)
                # model_kwargs = {'device': 'cpu'}
                # encode_kwargs = {'normalize_embeddings': False}
                # embedding_model = HuggingFaceEmbeddings(
                #     model_name=model_name,
                #     model_kwargs=model_kwargs,
                #     encode_kwargs=encode_kwargs
                # )
                # db3 = Chroma(persist_directory="./chroma_db", embedding_function=form_data.model)
                # docs = db3.similarity_search(last_user_content)
                # log.info(f"docs >>>  {docs}")


            r = requests.request(
                method="POST",
                url=f"{url}/api/generate",
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


class ChatMessage(BaseModel):
    role: str
    content: str
    images: Optional[List[str]] = None


class GenerateChatCompletionForm(BaseModel):
    model: str
    messages: List[ChatMessage]
    format: Optional[str] = None
    options: Optional[dict] = None
    template: Optional[str] = None
    stream: Optional[bool] = None
    keep_alive: Optional[Union[int, str]] = None


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


            # start
            # form_data 객체에서 딕셔너리 데이터를 가져옴
            form_dict = form_data.dict()
            last_user_content = ''
            user_messages = [msg for msg in form_dict['messages'] if msg['role'] == 'user']
            if user_messages:  # user_messages 리스트가 비어있지 않은 경우에만 실행
                last_user_content = user_messages[-1]['content']
                log.info(f"last_user_content >> {last_user_content}")
            else:
                log.info("No user messages found")

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

                # 결과에서 distances의 값이 가장 작은지 확인합니다.
                if result['distances'] and result['distances'][0]:
                    if result['distances'][0][0] < min_distance:
                        # 현재 결과의 거리가 더 작다면, 최소값을 업데이트합니다.
                        min_distance = result['distances'][0][0]
                        min_result = result
                        min_collection_name = collection_name
    
            log.info("###################################################\n")
            log.info(f"\nmin_distance : {min_distance}")
            log.info("###################################################\n")
            if min_distance < 1 :
                # log.info("######################## MIN DISTANCE ############################# \n\n\n\n\n")
                collection_instance = chromadb.get_collection(min_collection_name)
                result = collection_instance.query(
                        query_texts=[last_user_content],
                        n_results=5,
                )
                # log.info(f"\n\n\n############  min_distance >>  {min_distance}" )
                # log.info(f"Results for collection {collection_name}: {result}")
                # log.info("######################## MIN DISTANCE ############################# \n\n\n\n\n")


                extracted_documents = result['documents'][0][0]
                #final_content = "Use the following context as your learned knowledge, inside <context></context> XML tags.\n<context>\n    "
                final_content = "내부에서 배운 지식으로 다음 컨텍스트를 사용하십시오. <context></context> XML tags.\n<context>\n"
                final_content += extracted_documents
                final_content += "\n\n</context>\n\n너가 유저에게 대답할 때 :\n-반드시 한국어로 대답해라. 만약 너가 잘 모르겠으면 모르겠다고 답해라.\n- 확실하지 않을 때 유저에게 명확하게 설명을 요청하세요.\n-맥락에서 정보를 얻었음을 언급하지 마세요.\n그리고 반드시 한국어로 대답합니다.\n        \n컨텍스트 정보를 바탕으로 쿼리에 답하세요.\n쿼리: "
                final_content += last_user_content

                new_chat_message = ChatMessage(role='user', content=final_content, images=None)
                log.info("\n######################## result ################### \n")
                log.info(f"{extracted_documents}")
                log.info("\n ######################## result  ###################")


                #아래의 주석 해제
                form_data.messages.append(new_chat_message)
                # log.info("################ form_data TOBE ####################\n\n\n\n\n")
                # log.info(form_data.messages)


                # log.info("######################## result ################### \n\n\n\n")
                # log.info(f"\n\n{form_data.model_dump_json(exclude_none=True)}")
                # log.info("\n\n\n\n ######################## result  ###################")

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


# TODO: we should update this part once Ollama supports other types
class OpenAIChatMessage(BaseModel):
    role: str
    content: str

    model_config = ConfigDict(extra="allow")


class OpenAIChatCompletionForm(BaseModel):
    model: str
    messages: List[OpenAIChatMessage]

    model_config = ConfigDict(extra="allow")


@app.post("/v1/chat/completions")
@app.post("/v1/chat/completions/{url_idx}")
async def generate_openai_chat_completion(
    form_data: OpenAIChatCompletionForm,
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
                        yield json.dumps(
                            {"request_id": request_id, "done": False}
                        ) + "\n"

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

            r = requests.request(
                method="POST",
                url=f"{url}/v1/chat/completions",
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


class UrlForm(BaseModel):
    url: str


class UploadBlobForm(BaseModel):
    filename: str


def parse_huggingface_url(hf_url):
    try:
        # Parse the URL
        parsed_url = urlparse(hf_url)

        # Get the path and split it into components
        path_components = parsed_url.path.split("/")

        # Extract the desired output
        user_repo = "/".join(path_components[1:3])
        model_file = path_components[-1]

        return model_file
    except ValueError:
        return None


async def download_file_stream(
    ollama_url, file_url, file_path, file_name, chunk_size=1024 * 1024
):
    done = False

    if os.path.exists(file_path):
        current_size = os.path.getsize(file_path)
    else:
        current_size = 0

    headers = {"Range": f"bytes={current_size}-"} if current_size > 0 else {}

    timeout = aiohttp.ClientTimeout(total=600)  # Set the timeout

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(file_url, headers=headers) as response:
            total_size = int(response.headers.get("content-length", 0)) + current_size

            with open(file_path, "ab+") as file:
                async for data in response.content.iter_chunked(chunk_size):
                    current_size += len(data)
                    file.write(data)

                    done = current_size == total_size
                    progress = round((current_size / total_size) * 100, 2)

                    yield f'data: {{"progress": {progress}, "completed": {current_size}, "total": {total_size}}}\n\n'

                if done:
                    file.seek(0)
                    hashed = calculate_sha256(file)
                    file.seek(0)

                    url = f"{ollama_url}/api/blobs/sha256:{hashed}"
                    response = requests.post(url, data=file)

                    if response.ok:
                        res = {
                            "done": done,
                            "blob": f"sha256:{hashed}",
                            "name": file_name,
                        }
                        os.remove(file_path)

                        yield f"data: {json.dumps(res)}\n\n"
                    else:
                        raise "Ollama: Could not create blob, Please try again."


# def number_generator():
#     for i in range(1, 101):
#         yield f"data: {i}\n"


# url = "https://huggingface.co/TheBloke/stablelm-zephyr-3b-GGUF/resolve/main/stablelm-zephyr-3b.Q2_K.gguf"
@app.post("/models/download")
@app.post("/models/download/{url_idx}")
async def download_model(
    form_data: UrlForm,
    url_idx: Optional[int] = None,
):

    if url_idx == None:
        url_idx = 0
    url = app.state.OLLAMA_BASE_URLS[url_idx]

    file_name = parse_huggingface_url(form_data.url)

    if file_name:
        file_path = f"{UPLOAD_DIR}/{file_name}"
        return StreamingResponse(
            download_file_stream(url, form_data.url, file_path, file_name),
        )
    else:
        return None


@app.post("/models/upload")
@app.post("/models/upload/{url_idx}")
def upload_model(file: UploadFile = File(...), url_idx: Optional[int] = None):
    if url_idx == None:
        url_idx = 0
    ollama_url = app.state.OLLAMA_BASE_URLS[url_idx]

    file_path = f"{UPLOAD_DIR}/{file.filename}"

    # Save file in chunks
    with open(file_path, "wb+") as f:
        for chunk in file.file:
            f.write(chunk)

    def file_process_stream():
        nonlocal ollama_url
        total_size = os.path.getsize(file_path)
        chunk_size = 1024 * 1024
        try:
            with open(file_path, "rb") as f:
                total = 0
                done = False

                while not done:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        done = True
                        continue

                    total += len(chunk)
                    progress = round((total / total_size) * 100, 2)

                    res = {
                        "progress": progress,
                        "total": total_size,
                        "completed": total,
                    }
                    yield f"data: {json.dumps(res)}\n\n"

                if done:
                    f.seek(0)
                    hashed = calculate_sha256(f)
                    f.seek(0)

                    url = f"{ollama_url}/api/blobs/sha256:{hashed}"
                    response = requests.post(url, data=f)

                    if response.ok:
                        res = {
                            "done": done,
                            "blob": f"sha256:{hashed}",
                            "name": file.filename,
                        }
                        os.remove(file_path)
                        yield f"data: {json.dumps(res)}\n\n"
                    else:
                        raise Exception(
                            "Ollama: Could not create blob, Please try again."
                        )

        except Exception as e:
            res = {"error": str(e)}
            yield f"data: {json.dumps(res)}\n\n"

    return StreamingResponse(file_process_stream(), media_type="text/event-stream")


# async def upload_model(file: UploadFile = File(), url_idx: Optional[int] = None):
#     if url_idx == None:
#         url_idx = 0
#     url = app.state.OLLAMA_BASE_URLS[url_idx]

#     file_location = os.path.join(UPLOAD_DIR, file.filename)
#     total_size = file.size

#     async def file_upload_generator(file):
#         print(file)
#         try:
#             async with aiofiles.open(file_location, "wb") as f:
#                 completed_size = 0
#                 while True:
#                     chunk = await file.read(1024*1024)
#                     if not chunk:
#                         break
#                     await f.write(chunk)
#                     completed_size += len(chunk)
#                     progress = (completed_size / total_size) * 100

#                     print(progress)
#                     yield f'data: {json.dumps({"status": "uploading", "percentage": progress, "total": total_size, "completed": completed_size, "done": False})}\n'
#         except Exception as e:
#             print(e)
#             yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n"
#         finally:
#             await file.close()
#             print("done")
#             yield f'data: {json.dumps({"status": "completed", "percentage": 100, "total": total_size, "completed": completed_size, "done": True})}\n'

#     return StreamingResponse(
#         file_upload_generator(copy.deepcopy(file)), media_type="text/event-stream"
#     )


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def deprecated_proxy(path: str, request: Request, user=Depends(get_current_user)):
    url = app.state.OLLAMA_BASE_URLS[0]
    target_url = f"{url}/{path}"

    body = await request.body()
    headers = dict(request.headers)

    if user.role in ["user", "admin"]:
        if path in ["pull", "delete", "push", "copy", "create"]:
            if user.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
                )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    headers.pop("host", None)
    headers.pop("authorization", None)
    headers.pop("origin", None)
    headers.pop("referer", None)

    r = None

    def get_request():
        nonlocal r

        request_id = str(uuid.uuid4())
        try:
            REQUEST_POOL.append(request_id)

            def stream_content():
                try:
                    if path == "generate":
                        data = json.loads(body.decode("utf-8"))

                        if not ("stream" in data and data["stream"] == False):
                            yield json.dumps({"id": request_id, "done": False}) + "\n"

                    elif path == "chat":
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

            r = requests.request(
                method=request.method,
                url=target_url,
                data=body,
                headers=headers,
                stream=True,
            )

            r.raise_for_status()

            # r.close()

            return StreamingResponse(
                stream_content(),
                status_code=r.status_code,
                headers=dict(r.headers),
            )
        except Exception as e:
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
