"""Guess a cuisine for every shop listed now, from its sign.

    python pipeline/cuisine.py            # writes data/cuisine.json (unit id -> label)

The licence lists carry no cuisine, so this is a guess from the shop's name, in two passes:
keyword rules on the Chinese and English sign, then labels read by hand from the names the
rules miss (data/cuisine_manual.json, keyed by the sign text). Anything still unclear stays
"unknown". The app always says the label was guessed from the name.
"""
import json
import re

from ingest import ROOT

LABELS = {
    "cha_chaan_teng": "Hong Kong style & cha chaan teng",
    "noodles": "Noodles & congee",
    "chinese": "Chinese",
    "japanese": "Japanese",
    "korean": "Korean",
    "se_asian": "Southeast Asian",
    "south_asian": "South Asian & Middle Eastern",
    "western": "Western",
    "fast_food": "Fast food & chains",
    "cafe": "Coffee, dessert & bakery",
    "hotpot_bbq": "Hot pot & barbecue",
    "bar": "Bar & nightlife",
    "hotel": "Hotel restaurant & banquet",
    "unknown": "Unclear from the name",
}

# Order matters: the first rule that matches wins, most specific first.
RULES = [
    ("fast_food", r"麥當勞|MCDONALD|肯德基|\bK ?F ?C\b|大家樂|CAFE DE CORAL|大快活|FAIRWOOD|美心MX|\bMX\b|吉野家|YOSHINOYA|"
                  r"BURGER KING|漢堡王|SUBWAY|PIZZA HUT|必勝客|DOMINO|迪自由|快餐|譚仔|TAMJAI|TAM JAI|三哥|SAMGOR|"
                  r"MOS BURGER|SHAKE SHACK|TACO BELL|JOLLIBEE|DIM SUM SQUARE|一蘭"),
    ("hotpot_bbq", r"火鍋|打邊爐|HOT ?POT|燒烤|串燒|烤肉|BBQ|BARBECUE|鍋物|SHABU|麻辣燙|雞煲|海底撈"),
    ("japanese", r"壽司|SUSHI|天井|拉麵|RAMEN|居酒屋|IZAKAYA|燒肉|YAKINIKU|鐵板燒|TEPPAN|丼|\bDON\b|日本|JAPAN|和食|割烹|"
                 r"天婦羅|TEMPURA|烏冬|UDON|丸龜|MARUGAME|吉列|TONKATSU|豚|蕎麥|SOBA|料理|鮨|OMAKASE|YAKITORI|日式|元気"),
    ("korean", r"韓|KOREA|SEOUL|首爾|部隊|BIBIMBAP|KIMCHI|泡菜"),
    ("se_asian", r"泰|THAI|越南|VIETNAM|\bPHO\b|河粉|馬來|MALAY|星加坡|新加坡|SINGAPORE|印尼|INDONESIA|BALI|海南雞|"
                 r"喇沙|LAKSA|菲律賓|FILIPINO|PINOY|緬甸|MYANMAR|BURMESE"),
    ("south_asian", r"印度|INDIA|TANDOOR|CURRY HOUSE|BIRYANI|NEPAL|尼泊爾|PAKISTAN|BANGLA|HALAL|清真|TURK|KEBAB|"
                    r"LEBAN|PERSIA|ARAB|MIDDLE EAST|MEDITERR|GREEK|SRI LANKA|KASHMIR|PUNJAB|YETI|HIMALAYA|THAKALI|SWAGAT"),
    ("bar", r"\bBAR\b|酒吧|\bPUB\b|LOUNGE|卡拉 ?OK|KARAOKE|夜總會|NIGHT ?CLUB|CLUB\b|會所|BREW|TAVERN|WINE|威士忌|"
            r"WHISK|COCKTAIL|SPEAKEASY|啤酒|BEER|SALOON"),
    ("cafe", r"咖啡|COFFEE|STARBUCKS|PACIFIC COFFEE|ESPRESSO|甜品|糖水|DESSERT|BAKERY|BAKE|麵包|西餅|餅店|CAKE|PATISSERIE|"
             r"GELATO|ICE CREAM|雪糕|茶飲|BUBBLE|奶茶專門|TEA HOUSE|TEA BAR|貢茶|一芳|COMEBUY|CHAGEE|喜茶|DONUT|"
             r"WAFFLE|CREPE|豆花|BOBA|% ARABICA|BLUE BOTTLE|BREAD|CROISSANT|PAN DE"),
    ("cha_chaan_teng", r"茶餐廳|冰室|冰廳|餐室|茶室|CAFE DE|CHA CHAAN|CHA CHAN|士多|STORE ROOM|快餐廳"),
    ("noodles", r"粉麵|麵家|麵館|麵店|麵檔|粥|米線|雲吞|牛腩|車仔麵|魚蛋|NOODLE|CONGEE|WONTON|狗仔粉|粉店|麵屋|拌麵|"
                r"刀削|蘭州|牛肉麵|酸辣粉|小籠|餃子|DUMPLING|腸粉|小麵"),
    ("western", r"STEAK|扒房|牛扒|PIZZA|薄餅|PASTA|意粉|ITALIAN|意大利|TRATTORIA|OSTERIA|FRENCH|法國|法式|BISTRO|BRASSERIE|"
                r"BURGER|漢堡|GRILL|MEXICAN|墨西哥|TACO|SPANISH|西班牙|TAPAS|AMERICAN|美式|DINER|西餐|SPAGHETTI|"
                r"GERMAN|德國|BRITISH|英式|PORTUGUESE|葡國|RUSSIAN|俄|EUROPEAN|歐陸|BRUNCH"),
    ("chinese", r"酒家|酒樓|中菜|小廚|小館|飯店|燒臘|燒味|燒鵝|點心|DIM SUM|海鮮|SEAFOOD|潮州|川菜|四川|SICHUAN|湘|上海|"
                r"SHANGHAI|北京|PEKING|客家|順德|粵|CANTONESE|CHINESE|中國|素食|齋|VEGETARIAN|飯館|食堂|大排檔|私房|"
                r"雞|鵝|鴨|魚|蝦|蟹|煲仔|小炒|家常|酒館|樓|軒|閣|苑|宴|麵|飯|粉"),
]
COMPILED = [(k, re.compile(p, re.I)) for k, p in RULES]
PLACEHOLDER = re.compile(r"^\(?\s*(no record( found)?|沒有記錄|没有記錄|沒有紀錄|---+|-|n/?a|nil)\s*\)?$", re.I)


def classify(names):
    text = " ".join(n for n in names if n and not PLACEHOLDER.match(n.strip()))
    if not text:
        return None
    for label, rx in COMPILED:
        if rx.search(text):
            return label
    return None


def current_names(rec):
    """Signs of the history listed now, newest first."""
    h = next((h for h in reversed(rec["sign_histories"]) if h["listed_in_latest_snapshot"]), None)
    if not h:
        return None
    s = h["signs"][-1]
    return [s["tc"], s["en"]]


def main():
    from export import DISTRICTS
    manual_path = ROOT / "data" / "cuisine_manual.json"
    manual = json.load(open(manual_path)) if manual_path.exists() else {}
    out, unmatched, by_rule, by_hand = {}, [], 0, 0
    for line in open(ROOT / "data" / "histories.jsonl"):
        rec = json.loads(line)
        if rec["dist"] not in DISTRICTS or rec["lat"] is None:
            continue
        names = current_names(rec)
        if not names:
            continue
        key = " · ".join(dict.fromkeys(n for n in names if n))
        label = manual.get(key)
        if label:
            by_hand += 1
        else:
            label = classify(names)
            if label:
                by_rule += 1
            else:
                unmatched.append(key)
                label = "unknown"
        out[rec["unit_id"]] = label
    json.dump(out, open(ROOT / "data" / "cuisine.json", "w"), ensure_ascii=False, indent=0)
    json.dump(sorted(set(unmatched)), open(ROOT / "data" / "cuisine_unmatched.json", "w"), ensure_ascii=False, indent=0)
    counts = {}
    for v in out.values():
        counts[v] = counts.get(v, 0) + 1
    print(f"{len(out)} shops listed now: {by_rule} by rule, {by_hand} by hand, {len(unmatched)} unclear")
    print(sorted(counts.items(), key=lambda x: -x[1]))


if __name__ == "__main__":
    main()
