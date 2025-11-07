"""实时语音识别 WebSocket 路由（科大讯飞 IAT 代理）"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from app.services.voice_service import voice_service
from app.api.auth import get_current_user
import asyncio
import threading
import queue


router = APIRouter(prefix="/api/v1/voice", tags=["语音-实时"])


@router.websocket("/realtime")
async def realtime_asr(websocket: WebSocket):
    """
    前端通过 WebSocket 发送音频二进制块（建议16kHz/16bit/单声道 PCM），
    本后端转发到科大讯飞实时识别服务，并将识别文字实时回传给前端。

    前端建议流程：
    - 连接 ws://<host>/api/v1/voice/realtime
    - 发送二进制音频块（ArrayBuffer）
    - 接收文本消息（JSON或纯文本）作为识别结果
    - 结束时关闭WebSocket
    """
    await websocket.accept()

    # 线程安全队列：音频 -> iflytek；结果 <- iflytek
    audio_queue: "queue.Queue[bytes]" = queue.Queue(maxsize=100)
    result_queue: "queue.Queue[str]" = queue.Queue(maxsize=100)
    stop_event = threading.Event()

    # 启动子线程连接 iflytek 并进行转发
    proxy_thread = threading.Thread(
        target=voice_service.start_realtime_proxy,
        args=(audio_queue, result_queue, stop_event),
        daemon=True,
    )
    proxy_thread.start()

    async def pump_results_to_client():
        # 将识别结果异步推送给前端
        while not stop_event.is_set():
            try:
                text = result_queue.get(timeout=0.1)
                if text:
                    await websocket.send_text(text)
            except Exception:
                await asyncio.sleep(0.05)

    pump_task = asyncio.create_task(pump_results_to_client())

    try:
        # 接收前端音频数据
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if "bytes" in msg and msg["bytes"] is not None:
                # 音频二进制块
                try:
                    audio_queue.put_nowait(msg["bytes"])
                except queue.Full:
                    # 队列满则丢弃最旧，确保实时性
                    try:
                        audio_queue.get_nowait()
                    except Exception:
                        pass
                    try:
                        audio_queue.put_nowait(msg["bytes"])
                    except Exception:
                        pass
            elif "text" in msg and msg["text"] is not None:
                # 可选择处理控制指令，例如 "{"cmd":"stop"}"
                if msg["text"].strip().lower() == "stop":
                    break
    except WebSocketDisconnect:
        pass
    finally:
        # 通知子线程结束
        stop_event.set()
        try:
            await pump_task
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/xunfei/ws-url")
async def get_xunfei_ws_url(
    current_user: dict = Depends(get_current_user),
    lang: str = "cn"
):
    """
    返回已鉴权的讯飞 RTASR 标准版 WebSocket URL（前端直连讯飞，后端生成签名）
    - 需携带用户鉴权（JWT）
    - 默认中文: lang=cn
    """
    try:
        ws_url = voice_service.generate_rtasr_auth_url(lang=lang, verbose=False)
        # 讯飞官方未明确固定有效期，此处推荐 300 秒内使用
        return {"ws_url": ws_url, "expires_in": 300}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成WebSocket URL失败: {str(e)}"
        )


@router.get("/xunfei-llm/ws-url")
async def get_xunfei_llm_ws_url(
    current_user: dict = Depends(get_current_user),
    lang: str = "autodialect",
    samplerate: str = "16000"
):
    """
    返回已鉴权的讯飞大模型实时语音转写 WebSocket URL（前端直连讯飞，后端生成签名）
    - 需携带用户鉴权（JWT）
    - lang: 语言类型，默认 "autodialect"（中英+202种方言），可选 "autominor"（37个语种）
    - samplerate: 采样率，默认 "16000"
    """
    try:
        ws_url, session_id = voice_service.generate_llm_rtasr_auth_url(
            lang=lang,
            samplerate=samplerate
        )
        # 调试输出
        resp = {
            "ws_url": ws_url,
            "session_id": session_id,
            "expires_in": 300
        }
        print(f"[Xunfei LLM] response={resp}")
        # 讯飞官方未明确固定有效期，此处推荐 300 秒内使用
        return resp
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成WebSocket URL失败: {str(e)}"
        )


