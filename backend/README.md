## 基础设置
```
conda activate /data/xbx/kdd_env
cd /data/xbx/KDD
nvitop
```
nvitop看哪张卡是空的，CUDA_VISIBLE_DEVICES=0,1代表只使用0,1号卡，空的卡才能用

## 造一个英文的商品数据集
部署chat server的sglang服务
```
bash app/sglang_server.sh
```

生成数据集
```
cd app
bash data.sh
```
改data.sh里的categories生成不同的数据，生成的数据集会在/data/xbx/KDD/app/data/raw


--lang en指定数据集为英文，--lang zh指定为中文

--id-prefix "en" 是编号的前缀，生成lifestyle时可以指定为--id-prefix "life"

更多品类可以在/data/xbx/KDD/app/scripts/prompts_En.py, /data/xbx/KDD/app/scripts/prompts.py添加category

注意要分配不同的id-prefix，这会影响后面的识别

----------------
```
【启动阶段 - 一次性】
products.json 
    ↓ 
  读取所有商品
    ↓
  生成每个商品的文本描述
    ↓
  Embedding Model (批量)
    ↓
  向量索引（NumPy 数组，内存）

━━━━━━━━━━━━━━━━━━━━━━━━━━━

【请求阶段 - 每次查询】

用户 query ("泳衣")
    ↓
  Embedding Model → query_embedding
    ↓
  向量检索（余弦相似度）
    ↓
  anchor 商品 ("儿童泳衣套装")
    ↓
  ┌─────────────┬─────────────┐
  │   类目先验   │   向量检索   │
  │  (规则过滤)  │ (anchor相似) │
  └─────────────┴─────────────┘
    ↓           ↓
    合并去重 → candidates (20个候选商品)
    ↓
  构造新的 query: "与'儿童泳衣套装'一起购买的互补商品"
    ↓
  Reranker Model
    输入1: 新构造的 query 文本
    输入2: candidates 的原始文本列表
    ↓
  打分 & 排序
    ↓
  Top-K (8个商品)
    ↓
  返回结果
```
