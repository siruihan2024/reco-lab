export CHAT_BASE_URL="http://127.0.0.1:30003/v1"
export CHAT_MODEL="/data/xbx/Qwen/Qwen3-8B"
export OPENAI_API_KEY="EMPTY"
export DATA_DIR="/data/xbx/KDD/app/data"

# 美妆,数码,家电,母婴,运动,家居,
# python scripts/gen_products.py --categories 母婴 --per-category 20 --batch-size 5 --id-prefix baby
# python scripts/gen_products.py --categories 家居 --per-category 20 --batch-size 5 --id-prefix home
# python scripts/gen_products.py --categories 美妆 --per-category 20 --batch-size 5 --id-prefix makeup
# python scripts/gen_products.py --categories 家电,数码 --per-category 20 --batch-size 5 --id-prefix elec
# python scripts/gen_products.py --categories " Furniture" --per-category 20 --batch-size 10 --id-prefix "furniture" --lang en
# python scripts/gen_products.py --categories " Food" --per-category 20 --batch-size 10 --id-prefix "food" --lang en
# python scripts/gen_products.py --categories " Clothing" --per-category 20 --batch-size 10 --id-prefix "clothing" --lang en
# python scripts/gen_products.py --categories " Electronics" --per-category 20 --batch-size 10 --id-prefix "electronics" --lang en
# python scripts/gen_products.py --categories " Books" --per-category 20 --batch-size 10 --id-prefix "books" --lang en
# python scripts/gen_products.py --categories " Movies" --per-category 20 --batch-size 10 --id-prefix "movies" --lang en
# python scripts/gen_products.py --categories " Music" --per-category 20 --batch-size 10 --id-prefix "music" --lang en
# python scripts/gen_products.py --categories " Games" --per-category 20 --batch-size 10 --id-prefix "games" --lang en
# python scripts/gen_products.py --categories " Toys" --per-category 20 --batch-size 10 --id-prefix "toys" --lang en
# python scripts/gen_products.py --categories " Sports" --per-category 20 --batch-size 10 --id-prefix "sports" --lang en
# python scripts/gen_products.py --categories " Hobbies" --per-category 20 --batch-size 10 --id-prefix "hobbies" --lang en
# python scripts/gen_products.py --categories " Other" --per-category 20 --batch-size 10 --id-prefix "other" --lang en

# python scripts/gen_products.py --categories " Computer" --per-category 20 --batch-size 10 --id-prefix "computer" --lang en
# python scripts/gen_products.py --categories " Beauty" --per-category 20 --batch-size 10 --id-prefix "beauty" --lang en
# python scripts/gen_products.py --categories " Clothing" --per-category 20 --batch-size 10 --id-prefix "clothing" --lang en
# python scripts/gen_products.py --categories " Electronics" --per-category 20 --batch-size 10 --id-prefix "electronics" --lang en
# python scripts/gen_products.py --categories " Appliances" --per-category 20 --batch-size 10 --id-prefix "appliances" --lang en
# python scripts/gen_products.py --categories " Baby" --per-category 20 --batch-size 10 --id-prefix "baby" --lang en
# python scripts/gen_products.py --categories " Sports" --per-category 20 --batch-size 10 --id-prefix "sports" --lang en
# python scripts/gen_products.py --categories " Home" --per-category 20 --batch-size 10 --id-prefix "home" --lang en
# python scripts/gen_products.py --categories " Pets" --per-category 20 --batch-size 10 --id-prefix "pets" --lang en
# python scripts/gen_products.py --categories " Books" --per-category 20 --batch-size 10 --id-prefix "books" --lang en
# python scripts/gen_products.py --categories " Music" --per-category 20 --batch-size 10 --id-prefix "music" --lang en
# python scripts/gen_products.py --categories " Movies" --per-category 20 --batch-size 10 --id-prefix "movies" --lang en
# python scripts/gen_products.py --categories " Games" --per-category 20 --batch-size 10 --id-prefix "games" --lang en
# python scripts/gen_products.py --categories " Toys" --per-category 20 --batch-size 10 --id-prefix "toys" --lang en
# python scripts/gen_products.py --categories " Hobbies" --per-category 20 --batch-size 10 --id-prefix "hobbies" --lang en
# python scripts/gen_products.py --categories " Automotive" --per-category 20 --batch-size 10 --id-prefix "automotive" --lang en
# python scripts/gen_products.py --categories " Garden" --per-category 20 --batch-size 10 --id-prefix "garden" --lang en
# python scripts/gen_products.py --categories " Office" --per-category 20 --batch-size 10 --id-prefix "office" --lang en
# python scripts/gen_products.py --categories " Travel" --per-category 20 --batch-size 10 --id-prefix "travel" --lang en
# python scripts/gen_products.py --categories " Other" --per-category 20 --batch-size 10 --id-prefix "other" --lang en