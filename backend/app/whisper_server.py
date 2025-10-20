#!/usr/bin/env python3
"""
Whisper ASR 服务 - 使用 faster-whisper 实现
支持音频文件和实时流式转写
"""
import os
import io
import tempfile
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import torch
from faster_whisper import WhisperModel

# 配置
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")  # tiny, base, small, medium, large
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"

app = FastAPI(title="Whisper ASR Service")

# CORS 支持（方便前端调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局 Whisper 模型
whisper_model = None


class TranscribeRequest(BaseModel):
    """文本转写请求"""
    language: Optional[str] = None  # zh, en, auto
    task: str = "transcribe"  # transcribe 或 translate


@app.on_event("startup")
async def startup():
    """启动时加载模型"""
    global whisper_model
    print(f"[INFO] Loading Whisper model: {WHISPER_MODEL}")
    print(f"[INFO] Device: {DEVICE}, Compute Type: {COMPUTE_TYPE}")
    
    # 使用 faster-whisper（比 transformers 快 4x）
    whisper_model = WhisperModel(
        WHISPER_MODEL,
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
        download_root="/data/xbx/models/whisper"  # 本地缓存
    )
    print(f"[INFO] Whisper model loaded successfully!")


@app.post("/v1/audio/transcriptions")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = None,
    task: str = "transcribe"
):
    """
    OpenAI 兼容的音频转写接口
    
    参数:
        file: 音频文件 (支持 mp3, wav, m4a, ogg, etc.)
        language: 语言代码 (zh, en, auto)
        task: transcribe (转写) 或 translate (翻译成英文)
    
    返回:
        {"text": "转写文本"}
    """
    if not whisper_model:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # 读取音频文件
        audio_bytes = await file.read()
        
        # 保存到临时文件（faster-whisper 需要文件路径）
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        
        # 转写
        segments, info = whisper_model.transcribe(
            tmp_path,
            language=language if language != "auto" else None,
            task=task,
            beam_size=5,
            vad_filter=True,  # 语音活动检测
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        # 拼接结果
        text = " ".join([segment.text for segment in segments]).strip()
        
        # 删除临时文件
        os.unlink(tmp_path)
        
        return {
            "text": text,
            "language": info.language,
            "duration": info.duration,
            "segments": len(list(segments))
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@app.post("/transcribe")
async def transcribe_simple(
    file: UploadFile = File(...),
    language: str = "zh"
):
    """
    简化版转写接口
    """
    result = await transcribe_audio(file, language=language)
    return {"text": result["text"]}


@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "healthy",
        "model": WHISPER_MODEL,
        "device": DEVICE,
        "model_loaded": whisper_model is not None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=30004)