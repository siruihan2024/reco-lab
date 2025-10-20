# app/server.py
import os
import base64
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
from app.engine.recommendation import AssocRecommender
from app.config import USE_LLM_CATEGORY_MAPPER
from app.models.vision import VisionClient  # 🆕 新增

DATA_PATH = os.getenv("PRODUCTS_PATH", "/data/xbx/KDD/app/data/products.json")
WHISPER_API_URL = os.getenv("WHISPER_API_URL", "http://127.0.0.1:30004")

app = FastAPI(title="Assoc Recommender via Qwen + sglang + Whisper + Vision")

# CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RecommendReq(BaseModel):
    query: str = Field(..., description="用户查询，如'泳衣'")
    top_k: Optional[int] = Field(8, ge=1, le=50)
    debug: Optional[bool] = Field(False, description="是否开启调试模式")


@app.on_event("startup")
async def _startup():
    app.state.reco = AssocRecommender(DATA_PATH, use_llm_mapper=USE_LLM_CATEGORY_MAPPER)
    app.state.vision = VisionClient()  # 🆕 初始化 VL 客户端
    await app.state.reco.warmup()


@app.post("/recommend")
async def recommend(req: RecommendReq):
    """文本推荐"""
    res = await app.state.reco.recommend(
        req.query, 
        top_k=req.top_k or 8,
        debug=req.debug or False
    )
    return res


@app.post("/recommend/voice")
async def recommend_by_voice(
    audio: UploadFile = File(...),
    top_k: int = 8,
    language: str = "zh"
):
    """🎤 语音推荐接口"""
    try:
        # 1) 调用 Whisper 转写
        async with httpx.AsyncClient(timeout=30) as client:
            files = {"file": (audio.filename, await audio.read(), audio.content_type)}
            data = {"language": language}
            
            resp = await client.post(
                f"{WHISPER_API_URL}/v1/audio/transcriptions",
                files=files,
                data=data
            )
            resp.raise_for_status()
            asr_result = resp.json()
        
        transcription = asr_result.get("text", "")
        
        if not transcription:
            raise HTTPException(status_code=400, detail="转写结果为空")
        
        # 2) 调用推荐引擎
        reco_result = await app.state.reco.recommend(transcription, top_k=top_k)
        
        # 3) 返回结果
        return {
            "transcription": transcription,
            "language": asr_result.get("language"),
            "duration": asr_result.get("duration"),
            **reco_result
        }
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Whisper service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommend/image")
async def recommend_by_image(
    image: UploadFile = File(..., description="图片文件 (jpg, png, etc.)"),
    top_k: int = Form(8, ge=1, le=50),
    custom_prompt: Optional[str] = Form(None, description="自定义图片理解提示词")
):
    """
    🖼️ 图片推荐接口
    
    参数:
        image: 图片文件 (jpg, png, webp, etc.)
        top_k: 返回推荐数量
        custom_prompt: 自定义提示词（可选）
    
    返回:
        {
            "understanding": "图片理解结果",
            "query": "提取的查询关键词",
            "anchor": {...},
            "items": [...]
        }
    """
    try:
        # 1) 读取图片
        image_data = await image.read()
        
        if len(image_data) > 10 * 1024 * 1024:  # 限制 10MB
            raise HTTPException(status_code=400, detail="图片文件过大（最大10MB）")
        
        # 2) 调用 VL 模型理解图片
        if custom_prompt:
            understanding = await app.state.vision.understand_image(image_data, prompt=custom_prompt)
            query = understanding  # 使用完整理解结果
        else:
            query = await app.state.vision.extract_query(image_data)
            understanding = query
        
        if not query:
            raise HTTPException(status_code=400, detail="无法识别图片内容")
        
        # 3) 调用推荐引擎
        reco_result = await app.state.reco.recommend(query, top_k=top_k)
        
        # 4) 返回结果
        return {
            "understanding": understanding,
            "query": query,
            "image_filename": image.filename,
            "image_size_kb": len(image_data) / 1024,
            **reco_result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image recommendation failed: {str(e)}")


@app.get("/admin/stats")
async def stats():
    return app.state.reco.stats()


@app.post("/admin/reload")
async def reload_data():
    return await app.state.reco.reload()


@app.post("/admin/clear_category_cache")
async def clear_category_cache():
    """清空类目映射缓存"""
    if app.state.reco.category_mapper:
        app.state.reco.category_mapper.clear_cache()
        return {"ok": True, "message": "Category cache cleared"}
    return {"ok": False, "message": "LLM category mapper not enabled"}


@app.get("/admin/category_cache_stats")
async def category_cache_stats():
    """查看类目映射缓存统计"""
    if app.state.reco.category_mapper:
        return app.state.reco.category_mapper.get_stats()
    return {"error": "LLM category mapper not enabled"}