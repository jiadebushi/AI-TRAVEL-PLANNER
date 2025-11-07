"""语音处理服务 - 科大讯飞语音转文本"""
from config import settings
import httpx
import hashlib
import base64
import json
import hmac
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, quote
import websocket
import ssl
from typing import Optional, Tuple
import threading
import time
import subprocess
import os
import tempfile
import uuid as uuid_lib


class VoiceService:
    """科大讯飞语音转文本服务"""
    
    def __init__(self):
        self.app_id = settings.xunfei_app_id
        self.api_key = settings.xunfei_api_key
        self.api_secret = settings.xunfei_api_secret
        # IAT(听写)与RTASR(实时转写)为两个不同服务，默认使用RTASR标准版
        self.iat_url = "wss://iat-api.xfyun.cn/v2/iat"
        self.rtasr_url = "wss://rtasr.xfyun.cn/v1/ws"
        
        # 大模型版本配置
        self.llm_app_id = settings.xunfei_llm_app_id
        self.llm_access_key_id = settings.xunfei_llm_access_key_id
        self.llm_access_key_secret = settings.xunfei_llm_access_key_secret
        self.llm_url = "wss://office-api-ast-dx.iflyaisol.com/ast/communicate/v1"
    
    def generate_iat_auth_url(self) -> str:
        """IAT 听写鉴权URL（备用）"""
        host = "iat-api.xfyun.cn"
        path = "/v2/iat"
        now = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        signature_origin = f"host: {host}\ndate: {now}\nGET {path} HTTP/1.1"
        signature_sha = hmac.new(self.api_secret.encode('utf-8'), signature_origin.encode('utf-8'), digestmod=hashlib.sha256).digest()
        signature_sha_base64 = base64.b64encode(signature_sha).decode('utf-8')
        authorization_origin = f'api_key="{self.api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')
        values = {"authorization": authorization, "date": now, "host": host}
        return f"wss://{host}{path}?{urlencode(values)}"

    def generate_rtasr_auth_url(self, lang: str = "cn", verbose: bool = False) -> str:
        """RTASR 实时语音转写鉴权URL（标准版）"""
        # 文档: signa = Base64( HmacSHA1( MD5(appid+ts), api_key ) )
        host = "rtasr.xfyun.cn"
        path = "/v1/ws"
        # 注意：必须使用 epoch 秒（time.time），不要用 naive utcnow().timestamp() 以免被当作本地时区计算
        ts = str(int(time.time()))
        base_string = f"{self.app_id}{ts}"
        md5_val = hashlib.md5(base_string.encode('utf-8')).hexdigest()
        signa_bytes = hmac.new(self.api_key.encode('utf-8'), md5_val.encode('utf-8'), hashlib.sha1).digest()
        signa = base64.b64encode(signa_bytes).decode('utf-8')
        params = {
            "appid": self.app_id,
            "ts": ts,
            "signa": signa,
            "lang": lang,
        }
        url = f"wss://{host}{path}?{urlencode(params)}"
        if verbose:
            print(f"[RTASR] auth ts={ts}")
        return url
    
    def generate_llm_rtasr_auth_url(
        self, 
        lang: str = "autodialect",
        uuid: Optional[str] = None,
        samplerate: str = "16000"
    ) -> Tuple[str, str]:
        """
        生成讯飞大模型实时语音转写 WebSocket URL 和 session_id
        
        Args:
            lang: 语言类型，默认 "autodialect"（中英+202种方言），可选 "autominor"（37个语种）
            uuid: 自定义UUID（可选），如果不提供则自动生成
            samplerate: 采样率，默认 "16000"
        
        Returns:
            (ws_url, session_id): WebSocket URL 和会话ID
        """
        if not self.llm_app_id or not self.llm_access_key_id or not self.llm_access_key_secret:
            raise ValueError("讯飞大模型配置未设置，请检查 XUNFEI_LLM_APP_ID、XUNFEI_LLM_ACCESS_KEY_ID、XUNFEI_LLM_ACCESS_KEY_SECRET")
        
        # 1. 生成时间戳（UTC格式）
        # 修改 now 为北京时间
        now = datetime.now(timezone(timedelta(hours=8)))
        utc_str = now.strftime('%Y-%m-%dT%H:%M:%S+0800')
        
        # 2. 生成UUID（如果没有提供）
        if not uuid:
            uuid = str(uuid_lib.uuid4())
        
        # 3. 准备所有参数（不包含signature）
        params = {
            'accessKeyId': self.llm_access_key_id,
            'appId': self.llm_app_id,
            'audio_encode': 'pcm_s16le',
            'lang': lang,
            'samplerate': samplerate,
            'utc': utc_str,  # 未编码的版本用于签名
            'uuid': uuid,
        }
        
        # 4. 按参数名升序排序
        sorted_params = sorted(params.items())
        
        # 5. 构建 baseString（需要对键和值进行URL编码）
        base_string_parts = []
        for key, value in sorted_params:
            encoded_key = quote(key, safe='')
            encoded_value = quote(str(value), safe='')
            base_string_parts.append(f"{encoded_key}={encoded_value}")
        base_string = '&'.join(base_string_parts)
        
        # 6. HMAC-SHA1 加密
        hmac_sha1 = hmac.new(
            self.llm_access_key_secret.encode('utf-8'),
            base_string.encode('utf-8'),
            hashlib.sha1
        ).digest()
        
        # 7. Base64 编码
        signature = base64.b64encode(hmac_sha1).decode('utf-8')
        signature_encoded = quote(signature, safe='')
        
        # 8. 构建完整的查询字符串（所有参数都需要URL编码）
        utc_encoded = quote(utc_str, safe='')
        query_params = {
            'accessKeyId': self.llm_access_key_id,
            'appId': self.llm_app_id,
            'audio_encode': 'pcm_s16le',
            'lang': lang,
            'samplerate': samplerate,
            'utc': utc_encoded,  # 使用编码后的版本
            'uuid': uuid,
            'signature': signature_encoded,
        }
        # 对查询参数进行排序并编码
        query_parts = []
        for k, v in sorted(query_params.items()):
            query_parts.append(f"{quote(k, safe='')}={quote(str(v), safe='')}")
        query_string = '&'.join(query_parts)
        
        # 9. 构建 WebSocket URL
        ws_url = f'{self.llm_url}?{query_string}'
        
        # 10. 生成 sessionId（用于结束识别）
        session_id = str(uuid_lib.uuid4())
        
        return ws_url, session_id

    # =============== 实时转写桥接（WebSocket 转发） ===============
    def start_realtime_proxy(self, audio_queue, result_queue, stop_event):
        """
        使用讯飞 RTASR 标准版：
        - 建立到 rtasr.xfyun.cn/v1/ws 的 WebSocket 连接
        - 从 audio_queue 读取二进制PCM块，直接作为 binary message 发送
        - 接收 text message(JSON)，解析后将识别文本写入 result_queue
        - stop_event 置位后，发送结束帧并关闭连接
        说明：RTASR 要求 16kHz、16bit、单声道 PCM（pcm_s16le）。建议前端发送L16 PCM。
        """
        ws_url = self.generate_rtasr_auth_url()
        print(f"[RTASR] Connecting to: {ws_url}")
        ws_ready = threading.Event()  # 用于标记WebSocket连接已就绪
        ws_instance = None  # 保存WebSocket实例，用于发送数据
        acc_text = ""  # 累积的最终文本
        last_sent_len = 0  # 上次发送到前端的文本长度

        def on_open(ws):
            nonlocal ws_instance
            ws_instance = ws
            print("[RTASR] WebSocket opened")
            result_queue.put("[WS_OPEN]")

        def on_message(ws, message):
            nonlocal acc_text, last_sent_len  # 声明使用外层作用域的变量
            try:
                data = json.loads(message)
                action = data.get("action")
                code = str(data.get("code"))
                
                # 处理握手响应
                if action == "started" and code == "0":
                    print("[RTASR] Handshake started OK")
                    result_queue.put("[WS_READY]")
                    ws_ready.set()  # 标记连接已就绪，可以开始发送音频
                    return
                
                # 处理识别结果
                if action == "result" and code == "0":
                    # data 字段是一个JSON字符串，需再次解析
                    inner = data.get("data")
                    if inner:
                        try:
                            inner_json = json.loads(inner)
                            # 解析识别结果
                            cn_data = inner_json.get("cn", {})
                            if cn_data:
                                st = cn_data.get("st", {})
                                words = []
                                for rt in st.get("rt", []):
                                    for ws_seg in rt.get("ws", []):
                                        for cw in ws_seg.get("cw", []):
                                            w = cw.get("w")
                                            if w:
                                                words.append(w)
                                if words:
                                    text_out = "".join(words)
                                    result_type = st.get("type")  # 0=最终, 1=中间
                                    if result_type == 0:
                                        # 最终结果，累加到缓冲并推送整体文本
                                        acc_text = acc_text + text_out
                                        print(f"[RTASR] Final: {text_out} -> Acc: {acc_text}")
                                        last_sent_len = len(acc_text)
                                        result_queue.put(acc_text)
                                    else:
                                        # 中间结果，推送累积+当前片段供前端展示
                                        preview = acc_text + text_out
                                        # 仅当预览比已发送更长时才推送，避免前端回退/清空
                                        if len(preview) > last_sent_len:
                                            print(f"[RTASR] Partial: {text_out} -> Preview: {preview}")
                                            last_sent_len = len(preview)
                                            result_queue.put(preview)
                        except Exception as e:
                            print(f"[RTASR] Parse error: {e}")
                            result_queue.put(f"[PARSE_ERROR] {str(e)}")
                elif action == "error" or code != "0":
                    error_msg = data.get('desc') or data.get('message') or f"code={code}"
                    print(f"[RTASR] Error: {error_msg}")
                    result_queue.put(f"[ERROR] {error_msg}")
            except Exception as e:
                print(f"[RTASR] Exception in on_message: {e}")
                result_queue.put(f"[EXCEPTION] {str(e)}")

        def on_error(ws, error):
            print(f"[RTASR] WebSocket error: {error}")
            result_queue.put(f"[WS_ERROR] {error}")

        def on_close(ws, *args):
            print("[RTASR] WebSocket closed")
            result_queue.put("[WS_CLOSED]")
            ws_ready.clear()

        # 建立连接
        ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )

        # 在子线程里运行WebSocket
        def run_forever():
            print("[RTASR] run_forever starting...")
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
            print("[RTASR] run_forever ended")

        ws_thread = threading.Thread(target=run_forever, daemon=True)
        ws_thread.start()

        # 等待连接建立和握手完成（最多等待5秒）
        if not ws_ready.wait(timeout=5.0):
            print("[RTASR] Handshake timeout")
            result_queue.put("[ERROR] WebSocket握手超时")
            stop_event.set()
            return

        # 音频发送循环（建议每 ~40ms 发送 ~1280字节）
        while not stop_event.is_set():
            try:
                # 非阻塞获取一块音频
                chunk = None
                try:
                    chunk = audio_queue.get(timeout=0.1)
                except Exception:
                    continue
                
                if chunk is not None and ws_instance:
                    try:
                        # RTASR 要求直接发送二进制 PCM 数据
                        # websocket-client 库的 send 方法会自动处理二进制数据
                        if isinstance(chunk, bytes):
                            ws_instance.send(chunk, opcode=websocket.ABNF.OPCODE_BINARY)
                        else:
                            # 如果不是bytes，尝试转换
                            ws_instance.send(bytes(chunk), opcode=websocket.ABNF.OPCODE_BINARY)
                        print(f"[RTASR] Sent audio chunk: {len(chunk)} bytes")
                    except Exception as e:
                        print(f"[RTASR] Send error: {e}")
                        result_queue.put(f"[SEND_ERROR] {str(e)}")
                        break
            except Exception as e:
                print(f"[RTASR] Loop error: {e}")
                result_queue.put(f"[LOOP_ERROR] {str(e)}")
                break

        # 发送结束标识
        if ws_instance:
            try:
                end_msg = json.dumps({"end": True})
                print(f"[RTASR] Sending end flag: {end_msg}")
                ws_instance.send(end_msg)
            except Exception:
                pass
            try:
                print("[RTASR] Closing WebSocket")
                ws_instance.close()
            except Exception:
                pass
    
    def convert_webm_to_wav(self, webm_path: str, output_path: str) -> str:
        """
        使用 ffmpeg 将 WebM 文件转换为 WAV (PCM格式)
        科大讯飞要求：16kHz, 16bit, 单声道, PCM编码
        
        Args:
            webm_path: WebM文件路径
            output_path: 输出WAV文件路径
            
        Returns:
            转换后的WAV文件路径
        """
        # ffmpeg命令：转换为PCM格式的WAV
        # -ar 16000: 采样率16kHz
        # -ac 1: 单声道
        # -sample_fmt s16: 16bit PCM
        # -f wav: 输出格式为WAV
        cmd = [
            'ffmpeg',
            '-i', webm_path,
            '-ar', '16000',  # 采样率
            '-ac', '1',      # 单声道
            '-sample_fmt', 's16',  # 16bit PCM
            '-f', 'wav',     # 输出格式
            '-y',            # 覆盖输出文件
            output_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            if not os.path.exists(output_path):
                raise Exception(f"转换失败：输出文件不存在 {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            raise Exception(f"ffmpeg转换失败: {e.stderr}")
        except FileNotFoundError:
            raise Exception("未找到ffmpeg工具，请确保已安装ffmpeg并添加到系统PATH")
    
    async def transcribe_audio_file(self, audio_file_path: str) -> str:
        """
        转录音频文件为文本
        支持 WebM 和 WAV 格式，如果是 WebM 会自动转换为 WAV (PCM)
        """
        # 检查文件格式
        file_ext = os.path.splitext(audio_file_path)[1].lower()
        
        # 如果是 WebM，需要先转换为 WAV
        if file_ext == '.webm':
            # 创建临时 WAV 文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_wav:
                wav_path = tmp_wav.name
            
            try:
                # 转换为 WAV
                wav_path = self.convert_webm_to_wav(audio_file_path, wav_path)
                # 使用转换后的文件进行转写
                return await self._transcribe_wav_file(wav_path)
            finally:
                # 清理临时文件
                if os.path.exists(wav_path):
                    os.unlink(wav_path)
        elif file_ext == '.wav':
            # 直接转写 WAV 文件
            return await self._transcribe_wav_file(audio_file_path)
        else:
            raise Exception(f"不支持的音频格式: {file_ext}，仅支持 .webm 和 .wav")
    
    async def _transcribe_wav_file(self, wav_path: str) -> str:
        """转写 WAV 文件为文本"""
        # 这里使用科大讯飞WebSocket API进行实时转写
        # 简化实现：读取音频文件并转换为base64
        
        with open(wav_path, 'rb') as f:
            audio_data = f.read()
        
        # 转换为base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return await self.transcribe_audio_base64(audio_base64)
    
    async def transcribe_audio_base64(self, audio_base64: str, audio_format: str = "wav") -> str:
        """从base64音频数据转写文本（简化版，实际需要使用WebSocket）"""
        # 注意：这是一个简化实现
        # 实际科大讯飞API需要：
        # 1. 建立WebSocket连接
        # 2. 发送音频数据流
        # 3. 接收识别结果
        
        # 这里提供一个使用HTTP接口的简化实现（如果可用）
        # 实际项目中应该使用WebSocket进行实时转写
        
        try:
            # 示例：使用HTTP接口（需要根据科大讯飞实际API文档调整）
            async with httpx.AsyncClient() as client:
                # 这里需要根据科大讯飞实际的HTTP API接口实现
                # 当前为占位实现
                pass
        except Exception as e:
            raise Exception(f"语音转写失败: {str(e)}")
        
        # 返回占位文本（实际应用中应该返回识别结果）
        return "这是从语音转换的文本（需要实现科大讯飞WebSocket连接）"
    
    def transcribe_audio_sync(self, audio_base64: str) -> str:
        """同步转写（使用WebSocket）"""
        # 注意：这是一个占位实现
        # 完整的科大讯飞WebSocket实现需要：
        # 1. 建立WebSocket连接
        # 2. 发送参数和音频数据
        # 3. 接收并解析结果
        
        # 实际实现需要参考科大讯飞官方SDK
        # 这里返回示例文本
        return "语音转文本结果（需要完整实现WebSocket连接）"


# 全局语音服务实例
voice_service = VoiceService()


