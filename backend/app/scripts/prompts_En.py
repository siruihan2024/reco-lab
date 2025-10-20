# scripts/prompts_En.py
from typing import List

CATEGORY_HINTS = {
    "Lifestyle": "cleaning/storage/daily essentials/personal care tools/stationery/home appliances",
    "Food": "snacks/beverages/instant food/grains & oils/dairy products/condiments",
    "Clothing": "T-shirts/shirts/jackets/pants/dresses/underwear/loungewear",
    "Beauty": "skincare/cosmetics/perfume/hair care/men's grooming/sunscreen",
    "Electronics": "phone accessories/headphones/power banks/camera accessories/wearables",
    "Appliances": "kitchen appliances/cleaning appliances/air conditioning/refrigerators & washers/personal care appliances",
    "Baby": "formula/diapers/baby clothing/feeding supplies/toys",
    "Sports": "sportswear/athletic shoes/outdoor gear/fitness equipment/cycling",
    "Home": "furniture/lighting/bedding/decorations/kitchenware",
    "Pets": "cat & dog food/treats/toys/cleaning/daily supplies",
    "Books": "fiction/non-fiction/textbooks/children's books/magazines/comics",
    "Music": "CDs/vinyl records/digital albums/musical instruments/audio equipment",
    "Movies": "DVDs/Blu-rays/streaming subscriptions/movie merchandise/posters",
    "Games": "video games/board games/card games/gaming consoles/gaming accessories",
    "Toys": "action figures/dolls/building blocks/educational toys/remote control toys",
    "Hobbies": "art supplies/craft materials/model kits/collectibles/DIY tools",
    "Automotive": "car accessories/maintenance products/car electronics/cleaning supplies/interior decorations",
    "Garden": "plants/seeds/gardening tools/fertilizers/outdoor furniture/decorations",
    "Office": "office furniture/desk accessories/printers/paper products/organizational tools",
    "Travel": "luggage/travel accessories/travel guides/camping gear/backpacks",
    "Other": "other products",
}

def build_generation_prompt(category: str, count: int) -> str:
    hint = CATEGORY_HINTS.get(category, "")
    return f"""You are an e-commerce product planner. Please generate {count} different English products for the category "{category}", output as a JSON array (strict JSON, no extra text).

Each product object must contain these fields:
- id: leave as empty string "" (we will assign it later)
- name: short English product name (≤60 characters)
- synonyms: 3-6 English synonyms or alternative names (array)
- category: fixed as "{category}"
- description: 50-150 character English description highlighting selling points
- tags: 3-8 keywords (array)
- price: numeric value, reasonable range (e.g., 9.99~9999.99)
- attributes: key attributes for this category (object, keys in English)

Category "{category}" may include: {hint}

Requirements:
- Avoid duplicate or overly similar products
- Output strict JSON array only, no explanatory text
- Fixed field names, properly escape quotes in strings
"""