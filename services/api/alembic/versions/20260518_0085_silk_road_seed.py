"""Silk Road corridor heritage seed — China, Iran, Turkey, India

FAZA 6 (VELOCITY) — Wave-8 Agent 1.

Seeds real Silk Road corridor heritage data across four major civilisations:
- CN: 30 heritage entries + 11 cities
- IR: 30 heritage entries + 10 cities
- TR: 30 heritage entries + 10 cities
- IN: 30 heritage entries + 10 cities
- UNESCO inscriptions: 15 (CN:4, IR:4, TR:4, IN:3)

Revision ID: 0085_silk_road_seed
Revises: 0081_central_asia_currencies
Create Date: 2026-05-18

Idempotent: ON CONFLICT DO NOTHING throughout.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0085_silk_road_seed"
down_revision: str | Sequence[str] | None = "0081_central_asia_currencies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- 1. Currencies (CNY, IRR, TRY, INR) ----------------------------------
    op.execute(
        """
        INSERT INTO currencies (code, name, symbol, decimal_places) VALUES
            ('CNY', '{"en":"Chinese Yuan Renminbi","ru":"Китайский юань","uz":"Xitoy yuani","zh":"人民币"}'::jsonb,     '¥', 2),
            ('IRR', '{"en":"Iranian Rial","ru":"Иранский риал","uz":"Eron riyoli","zh":"伊朗里亚尔"}'::jsonb,           '﷼', 2),
            ('TRY', '{"en":"Turkish Lira","ru":"Турецкая лира","uz":"Turk lirasi","zh":"土耳其里拉"}'::jsonb,           '₺', 2),
            ('INR', '{"en":"Indian Rupee","ru":"Индийская рупия","uz":"Hindiston rupiyasi","zh":"印度卢比"}'::jsonb,    '₹', 2)
        ON CONFLICT (code) DO NOTHING;
        """
    )

    # --- 2. silk_road_corridor pricing zone ----------------------------------
    op.execute(
        """
        INSERT INTO pricing_zones
            (slug, name, country_codes, default_currency, purchasing_power_index)
        VALUES
            ('silk_road_corridor',
             '{"en":"Silk Road Corridor","ru":"Коридор Шёлкового пути","uz":"Ipak yo''li koridori","zh":"丝绸之路走廊"}'::jsonb,
             ARRAY['CN','IR','TR','IN']::char(2)[],
             'USD',
             0.55)
        ON CONFLICT (slug) DO NOTHING;
        """
    )

    # --- 3. Prices for silk_road_corridor ------------------------------------
    op.execute(
        """
        INSERT INTO prices
            (plan_id, pricing_zone_id, currency, amount, is_active)
        SELECT pp.id, pz.id, 'USD', 2.9900, true
        FROM product_plans pp
        JOIN pricing_zones pz ON pz.slug = 'silk_road_corridor'
        WHERE pp.slug = 'premium_monthly'
        ON CONFLICT (plan_id, pricing_zone_id, currency, effective_from) DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO prices
            (plan_id, pricing_zone_id, currency, amount, is_active)
        SELECT pp.id, pz.id, 'USD', 29.9900, true
        FROM product_plans pp
        JOIN pricing_zones pz ON pz.slug = 'silk_road_corridor'
        WHERE pp.slug = 'premium_yearly'
        ON CONFLICT (plan_id, pricing_zone_id, currency, effective_from) DO NOTHING;
        """
    )

    # --- 4. Cities + geographic_admin_levels ---------------------------------
    op.execute(
        """
        WITH city_seeds(country_code, slug, name, lat, lng, population, is_capital, is_silk_road) AS (
            VALUES
                -- China
                ('CN','xian',
                    '{"en":"Xi''an","ru":"Сиань","uz":"Sian","zh":"西安"}'::jsonb,
                    34.341574, 108.939774, 13000000, false, true),
                ('CN','dunhuang',
                    '{"en":"Dunhuang","ru":"Дуньхуан","uz":"Dunxuan","zh":"敦煌"}'::jsonb,
                    40.142000, 94.662000, 190000, false, true),
                ('CN','urumqi',
                    '{"en":"Ürümqi","ru":"Урумчи","uz":"Urumchi","zh":"乌鲁木齐"}'::jsonb,
                    43.793743, 87.628586, 3500000, false, true),
                ('CN','beijing',
                    '{"en":"Beijing","ru":"Пекин","uz":"Pekin","zh":"北京"}'::jsonb,
                    39.904202, 116.407394, 21700000, true, false),
                ('CN','luoyang',
                    '{"en":"Luoyang","ru":"Лоян","uz":"Luoyan","zh":"洛阳"}'::jsonb,
                    34.618570, 112.454192, 7200000, false, true),
                ('CN','zhangye',
                    '{"en":"Zhangye","ru":"Чжанъе","uz":"Jangye","zh":"张掖"}'::jsonb,
                    38.925882, 100.455100, 1200000, false, true),
                ('CN','kashgar',
                    '{"en":"Kashgar","ru":"Кашгар","uz":"Qoshg''ar","zh":"喀什"}'::jsonb,
                    39.470400, 75.989500, 700000, false, true),
                ('CN','turpan',
                    '{"en":"Turpan","ru":"Турфан","uz":"Turfon","zh":"吐鲁番"}'::jsonb,
                    42.947600, 89.184200, 650000, false, true),
                ('CN','hangzhou',
                    '{"en":"Hangzhou","ru":"Ханчжоу","uz":"Xanjou","zh":"杭州"}'::jsonb,
                    30.274218, 120.155070, 12200000, false, false),
                ('CN','chengdu',
                    '{"en":"Chengdu","ru":"Чэнду","uz":"Chengdu","zh":"成都"}'::jsonb,
                    30.659462, 104.065735, 21000000, false, false),
                ('CN','suzhou',
                    '{"en":"Suzhou","ru":"Сучжоу","uz":"Suzou","zh":"苏州"}'::jsonb,
                    31.298886, 120.585316, 10700000, false, false),
                -- Iran
                ('IR','isfahan',
                    '{"en":"Isfahan","ru":"Исфахан","uz":"Isfahon","zh":"伊斯法罕"}'::jsonb,
                    32.661343, 51.680374, 2200000, false, true),
                ('IR','shiraz',
                    '{"en":"Shiraz","ru":"Шираз","uz":"Sheroz","zh":"设拉子"}'::jsonb,
                    29.591768, 52.583698, 1900000, false, true),
                ('IR','tehran',
                    '{"en":"Tehran","ru":"Тегеран","uz":"Tehron","zh":"德黑兰"}'::jsonb,
                    35.689197, 51.388974, 9200000, true, false),
                ('IR','yazd',
                    '{"en":"Yazd","ru":"Йезд","uz":"Yazd","zh":"亚兹德"}'::jsonb,
                    31.897474, 54.357696, 600000, false, true),
                ('IR','tabriz',
                    '{"en":"Tabriz","ru":"Тебриз","uz":"Tabriz","zh":"大不里士"}'::jsonb,
                    38.080111, 46.299370, 1700000, false, true),
                ('IR','persepolis',
                    '{"en":"Persepolis","ru":"Персеполь","uz":"Persepol","zh":"波斯波利斯"}'::jsonb,
                    29.935158, 52.891113, 5000, false, true),
                ('IR','mashhad',
                    '{"en":"Mashhad","ru":"Мешхед","uz":"Mashhad","zh":"马什哈德"}'::jsonb,
                    36.297022, 59.605911, 3600000, false, true),
                ('IR','kashan',
                    '{"en":"Kashan","ru":"Кашан","uz":"Koshan","zh":"卡尚"}'::jsonb,
                    33.987214, 51.010094, 370000, false, true),
                ('IR','kerman',
                    '{"en":"Kerman","ru":"Керман","uz":"Kerman","zh":"克尔曼"}'::jsonb,
                    30.283901, 57.078780, 820000, false, true),
                ('IR','bam',
                    '{"en":"Bam","ru":"Бам","uz":"Bam","zh":"巴姆"}'::jsonb,
                    29.105278, 58.357222, 200000, false, true),
                -- Turkey
                ('TR','istanbul',
                    '{"en":"Istanbul","ru":"Стамбул","uz":"Istanbul","zh":"伊斯坦布尔"}'::jsonb,
                    41.013611, 28.955000, 15460000, false, true),
                ('TR','ankara',
                    '{"en":"Ankara","ru":"Анкара","uz":"Anqara","zh":"安卡拉"}'::jsonb,
                    39.933363, 32.859742, 5700000, true, false),
                ('TR','izmir',
                    '{"en":"İzmir","ru":"Измир","uz":"Izmir","zh":"伊兹密尔"}'::jsonb,
                    38.423734, 27.142826, 4400000, false, false),
                ('TR','konya',
                    '{"en":"Konya","ru":"Конья","uz":"Konya","zh":"科尼亚"}'::jsonb,
                    37.874560, 32.493156, 2300000, false, true),
                ('TR','bursa',
                    '{"en":"Bursa","ru":"Бурса","uz":"Bursa","zh":"布尔萨"}'::jsonb,
                    40.182559, 29.066315, 3100000, false, true),
                ('TR','edirne',
                    '{"en":"Edirne","ru":"Эдирне","uz":"Edirne","zh":"埃迪尔内"}'::jsonb,
                    41.677283, 26.555771, 430000, false, true),
                ('TR','antalya',
                    '{"en":"Antalya","ru":"Анталья","uz":"Antalya","zh":"安塔利亚"}'::jsonb,
                    36.896891, 30.713324, 2600000, false, true),
                ('TR','goreme',
                    '{"en":"Göreme / Cappadocia","ru":"Гёреме","uz":"Goreme","zh":"格雷梅/卡帕多西亚"}'::jsonb,
                    38.643889, 34.854722, 15000, false, true),
                ('TR','gaziantep',
                    '{"en":"Gaziantep","ru":"Газиантеп","uz":"Gaziantep","zh":"加济安泰普"}'::jsonb,
                    37.066667, 37.383333, 2100000, false, true),
                ('TR','trabzon',
                    '{"en":"Trabzon","ru":"Трабзон","uz":"Trabzon","zh":"特拉布宗"}'::jsonb,
                    41.002697, 39.716763, 800000, false, false),
                -- India
                ('IN','agra',
                    '{"en":"Agra","ru":"Агра","uz":"Agra","zh":"阿格拉"}'::jsonb,
                    27.176670, 78.008072, 1800000, false, true),
                ('IN','delhi',
                    '{"en":"New Delhi","ru":"Нью-Дели","uz":"Yangi Dehli","zh":"新德里"}'::jsonb,
                    28.613939, 77.209021, 32900000, true, true),
                ('IN','jaipur',
                    '{"en":"Jaipur","ru":"Джайпур","uz":"Jaypur","zh":"斋浦尔"}'::jsonb,
                    26.912434, 75.787270, 3700000, false, false),
                ('IN','varanasi',
                    '{"en":"Varanasi","ru":"Варанаси","uz":"Varanasi","zh":"瓦拉纳西"}'::jsonb,
                    25.317645, 82.973915, 1500000, false, true),
                ('IN','mumbai',
                    '{"en":"Mumbai","ru":"Мумбаи","uz":"Mumbay","zh":"孟买"}'::jsonb,
                    19.076090, 72.877426, 20700000, false, false),
                ('IN','ajanta',
                    '{"en":"Ajanta","ru":"Аджанта","uz":"Ajanta","zh":"阿旃陀"}'::jsonb,
                    20.551900, 75.700100, 20000, false, true),
                ('IN','hampi',
                    '{"en":"Hampi","ru":"Хампи","uz":"Xampi","zh":"亨比"}'::jsonb,
                    15.335000, 76.462200, 3000, false, true),
                ('IN','khajuraho',
                    '{"en":"Khajuraho","ru":"Кхаджурахо","uz":"Xajuraxo","zh":"克久拉霍"}'::jsonb,
                    24.851700, 79.921700, 25000, false, false),
                ('IN','kolkata',
                    '{"en":"Kolkata","ru":"Калькутта","uz":"Kalkutta","zh":"加尔各答"}'::jsonb,
                    22.572645, 88.363892, 15000000, false, false),
                ('IN','chennai',
                    '{"en":"Chennai","ru":"Ченнаи","uz":"Chennai","zh":"钦奈"}'::jsonb,
                    13.082680, 80.270721, 11000000, false, false)
        ),
        new_city_levels AS (
            INSERT INTO geographic_admin_levels
                (parent_id, level, admin_level_type, code, name, country_code,
                 centroid_lat, centroid_lng, population, path)
            SELECT
                country_lvl.id,
                3,
                'city',
                upper(cs.country_code) || '.' || upper(cs.slug),
                cs.name,
                cs.country_code,
                cs.lat,
                cs.lng,
                cs.population,
                (country_lvl.path::text || '.' || cs.slug)::ltree
            FROM city_seeds cs
            JOIN geographic_admin_levels country_lvl ON
                country_lvl.country_code = cs.country_code
                AND country_lvl.admin_level_type = 'country'
            WHERE NOT EXISTS (
                SELECT 1 FROM geographic_admin_levels existing
                WHERE existing.code = upper(cs.country_code) || '.' || upper(cs.slug)
                  AND existing.admin_level_type = 'city'
            )
            RETURNING id, country_code, code
        )
        INSERT INTO cities
            (admin_level_id, country_code, slug, name, lat, lng,
             population, is_capital, is_silk_road)
        SELECT
            ncl.id,
            cs.country_code,
            cs.slug,
            cs.name,
            cs.lat,
            cs.lng,
            cs.population,
            cs.is_capital,
            cs.is_silk_road
        FROM city_seeds cs
        JOIN new_city_levels ncl ON
            ncl.country_code = cs.country_code
            AND ncl.code = upper(cs.country_code) || '.' || upper(cs.slug)
        ON CONFLICT (country_code, slug) DO NOTHING;
        """
    )

    # --- 5. Heritage objects + site admin_levels ------------------------------
    op.execute(
        """
        WITH default_tenant AS (
            SELECT id FROM tenants WHERE slug = 'default' LIMIT 1
        ),
        heritage_seeds(pub_id, kind_slug, name, country_code, city_slug,
                       lat, lng, period_start_year, unesco_id) AS (
            VALUES
                -- ===================== China (30) ===========================
                ('cn-great-wall-beijing','monument',
                    '{"en":"Great Wall — Mutianyu / Beijing section","ru":"Великая Китайская стена — участок Мутяньюй","uz":"Xitoy buyuk devori — Mutianyu","zh":"长城·慕田峪段"}'::jsonb,
                    'CN','beijing',40.432410,116.565590,-221::smallint,'438'),
                ('cn-great-wall-jiayuguan','monument',
                    '{"en":"Great Wall — Jiayuguan Pass (western terminus)","ru":"Великая Китайская стена — застава Цзяюйгуань","uz":"Xitoy buyuk devori — G''arbiy uchi Jiayuguan","zh":"长城·嘉峪关"}'::jsonb,
                    'CN','zhangye',39.819500,98.301400,-200::smallint,'438'),
                ('cn-mogao-caves','cave',
                    '{"en":"Mogao Caves, Dunhuang","ru":"Пещеры Могао","uz":"Mogao g''orlari","zh":"莫高窟"}'::jsonb,
                    'CN','dunhuang',40.036389,94.808056,366::smallint,'440'),
                ('cn-silk-road-changan-tianshan','archaeological_site',
                    '{"en":"Silk Roads: Chang''an–Tianshan Corridor","ru":"Шёлковый путь: коридор Чанъань–Тяньшань","uz":"Ipak yo''li: Changan–Tianshan yo''lagi","zh":"丝绸之路：长安—天山廊道路网"}'::jsonb,
                    'CN','xian',34.341574,108.939774,200::smallint,'1442'),
                ('cn-terracotta-army','archaeological_site',
                    '{"en":"Mausoleum of the First Qin Emperor & Terracotta Army","ru":"Мавзолей первого императора Цинь и Терракотовая армия","uz":"Birinchi Xitoy imperatori maqbarasi va Terrakota armiyasi","zh":"秦始皇陵及兵马俑"}'::jsonb,
                    'CN','xian',34.384852,109.273550,-210::smallint,'441'),
                ('cn-giant-wild-goose-pagoda','monument',
                    '{"en":"Giant Wild Goose Pagoda, Xi''an","ru":"Большая Пагода Диких Гусей","uz":"Katta Yovvoyi G''oz Pagodasi","zh":"大雁塔"}'::jsonb,
                    'CN','xian',34.222176,108.959900,652::smallint,NULL),
                ('cn-small-wild-goose-pagoda','monument',
                    '{"en":"Small Wild Goose Pagoda, Xi''an","ru":"Малая Пагода Диких Гусей","uz":"Kichik Yovvoyi G''oz Pagodasi","zh":"小雁塔"}'::jsonb,
                    'CN','xian',34.230920,108.951200,707::smallint,NULL),
                ('cn-xuanquanzhi-relay','archaeological_site',
                    '{"en":"Xuanquanzhi Relay Station (Han Dynasty postal hub)","ru":"Ямская станция Сюаньцюаньчжи (Хань)","uz":"Xuanquanzhi pochta stantsiyasi (Xan sulolasi)","zh":"悬泉置遗址"}'::jsonb,
                    'CN','dunhuang',40.263300,95.637300,-100::smallint,NULL),
                ('cn-zhangye-rainbow-mountains','archaeological_site',
                    '{"en":"Zhangye Danxia — Rainbow Mountains","ru":"Скалы Данься Чжанъе","uz":"Jangye Dansia kamalak tog''lari","zh":"张掖丹霞地貌"}'::jsonb,
                    'CN','zhangye',38.941900,100.107300,NULL::smallint,NULL),
                ('cn-turpan-ancient-city','archaeological_site',
                    '{"en":"Gaochang Ancient City, Turpan","ru":"Древний город Гаочан","uz":"Gaochang qadimgi shahri","zh":"高昌故城"}'::jsonb,
                    'CN','turpan',42.852800,89.497600,327::smallint,NULL),
                ('cn-jiaohe-ruins','archaeological_site',
                    '{"en":"Jiaohe Ruins, Turpan","ru":"Руины Цзяохэ","uz":"Jiaohe xarobalari","zh":"交河故城"}'::jsonb,
                    'CN','turpan',42.952200,89.040500,-108::smallint,NULL),
                ('cn-kashgar-id-kah','mosque',
                    '{"en":"Id Kah Mosque, Kashgar","ru":"Мечеть Ид Ках, Кашгар","uz":"Id Qah masjidi, Qoshg''ar","zh":"艾提尕尔清真寺"}'::jsonb,
                    'CN','kashgar',39.472100,76.002200,1442::smallint,NULL),
                ('cn-kashgar-abakh-khoja','mausoleum',
                    '{"en":"Abakh Khoja Mausoleum, Kashgar","ru":"Мавзолей Афака Ходжи","uz":"Afaq Xo''ja maqbarasi","zh":"阿帕克霍加麻扎"}'::jsonb,
                    'CN','kashgar',39.498900,75.968100,1640::smallint,NULL),
                ('cn-huanghuacheng-great-wall','monument',
                    '{"en":"Huanghuacheng Great Wall section","ru":"Участок Великой стены Хуанхуачэн","uz":"Huanxuacheng Buyuk devori","zh":"黄花城水长城"}'::jsonb,
                    'CN','beijing',40.555300,116.332700,-200::smallint,NULL),
                ('cn-temple-heaven','temple',
                    '{"en":"Temple of Heaven, Beijing","ru":"Храм Неба, Пекин","uz":"Osmon ibodatxonasi, Pekin","zh":"天坛"}'::jsonb,
                    'CN','beijing',39.882800,116.405700,1420::smallint,'881'),
                ('cn-summer-palace','palace',
                    '{"en":"Summer Palace, Beijing","ru":"Летний дворец, Пекин","uz":"Yozgi saroy, Pekin","zh":"颐和园"}'::jsonb,
                    'CN','beijing',40.000000,116.275000,1750::smallint,'880'),
                ('cn-forbidden-city','palace',
                    '{"en":"Imperial Palace — Forbidden City, Beijing","ru":"Запретный город, Пекин","uz":"Taqiqlangan shahar, Pekin","zh":"故宫"}'::jsonb,
                    'CN','beijing',39.916668,116.390495,1420::smallint,'439'),
                ('cn-longmen-grottoes','cave',
                    '{"en":"Longmen Grottoes, Luoyang","ru":"Пещеры Лунмэнь","uz":"Lungmen g''orlari","zh":"龙门石窟"}'::jsonb,
                    'CN','luoyang',34.562500,112.472500,493::smallint,'621'),
                ('cn-shaolin-monastery','monastery',
                    '{"en":"Shaolin Monastery — Historic Monuments of Dengfeng","ru":"Монастырь Шаолинь","uz":"Shaolin monastiri","zh":"少林寺"}'::jsonb,
                    'CN','luoyang',34.506389,112.933333,495::smallint,'1305'),
                ('cn-leshan-giant-buddha','monument',
                    '{"en":"Leshan Giant Buddha","ru":"Гигантская статуя Будды в Лэшане","uz":"Leshan buyuk Budda haykali","zh":"乐山大佛"}'::jsonb,
                    'CN','chengdu',29.543700,103.771700,713::smallint,'779'),
                ('cn-west-lake-hangzhou','monument',
                    '{"en":"West Lake Cultural Landscape, Hangzhou","ru":"Культурный ландшафт Западного озера","uz":"G''arbiy ko''l madaniy manzarasi","zh":"杭州西湖文化景观"}'::jsonb,
                    'CN','hangzhou',30.242800,120.131700,1000::smallint,'1334'),
                ('cn-suzhou-classical-gardens','monument',
                    '{"en":"Classical Gardens of Suzhou","ru":"Классические сады Сучжоу","uz":"Suzou klassik bog''lari","zh":"苏州古典园林"}'::jsonb,
                    'CN','suzhou',31.316700,120.633300,1350::smallint,'813'),
                ('cn-ming-tombs','mausoleum',
                    '{"en":"Ming Tombs, Beijing","ru":"Мин лин — гробницы Мин","uz":"Min sulolasi qabristonlari","zh":"明十三陵"}'::jsonb,
                    'CN','beijing',40.244200,116.219900,1409::smallint,NULL),
                ('cn-old-town-lijiang','monument',
                    '{"en":"Old Town of Lijiang","ru":"Старый город Лицзян","uz":"Lijyan qadimiy shahri","zh":"丽江古城"}'::jsonb,
                    'CN','chengdu',26.872100,100.233300,1400::smallint,'811'),
                ('cn-jingde-zhen-kilns','archaeological_site',
                    '{"en":"Jingdezhen Ancient Kilns","ru":"Фарфоровые печи Цзиндэчжэнь","uz":"Jingdezhen qadimiy pechklari","zh":"景德镇陶瓷窑址"}'::jsonb,
                    'CN','suzhou',29.291700,117.183300,583::smallint,NULL),
                ('cn-xian-city-wall','monument',
                    '{"en":"Xi''an Ancient City Wall","ru":"Древняя городская стена Сиань","uz":"Sian qadimiy shahar devori","zh":"西安古城墙"}'::jsonb,
                    'CN','xian',34.263900,108.953000,1370::smallint,NULL),
                ('cn-forest-of-stone-steles','museum',
                    '{"en":"Forest of Stone Steles Museum, Xi''an","ru":"Музей леса каменных стел","uz":"Tosh Bitigtoshlar o''rmoni muzeyi","zh":"西安碑林博物馆"}'::jsonb,
                    'CN','xian',34.256700,108.945300,1090::smallint,NULL),
                ('cn-famen-temple','temple',
                    '{"en":"Famen Temple & Underground Palace, Xi''an","ru":"Храм Фамэнь","uz":"Famen ibodatxonasi","zh":"法门寺"}'::jsonb,
                    'CN','xian',34.510600,107.865300,147::smallint,NULL),
                ('cn-dunhuang-yumen-pass','archaeological_site',
                    '{"en":"Yumen Pass (Jade Gate Pass), Dunhuang","ru":"Проход Юймэнь-гуань (Яшмовые ворота)","uz":"Yumenguan dovoni","zh":"玉门关"}'::jsonb,
                    'CN','dunhuang',40.367200,93.864400,-111::smallint,NULL),
                ('cn-zhangye-giant-buddha','temple',
                    '{"en":"Zhangye Giant Buddha Temple","ru":"Храм Гигантского Будды в Чжанъе","uz":"Jangye Buyuk Budda ibodatxonasi","zh":"张掖大佛寺"}'::jsonb,
                    'CN','zhangye',38.930300,100.449200,1098::smallint,NULL),

                -- ===================== Iran (30) ============================
                ('ir-persepolis','archaeological_site',
                    '{"en":"Persepolis","ru":"Персеполь","uz":"Persepol","zh":"波斯波利斯"}'::jsonb,
                    'IR','persepolis',29.935158,52.891113,-518::smallint,'114'),
                ('ir-pasargadae','archaeological_site',
                    '{"en":"Pasargadae — Tomb of Cyrus the Great","ru":"Пасаргады — Гробница Кира Великого","uz":"Pasargadae — Kir Buyuk maqbarasi","zh":"帕萨尔加德"}'::jsonb,
                    'IR','persepolis',30.193400,53.166700,-550::smallint,'1106'),
                ('ir-meidan-emam-isfahan','monument',
                    '{"en":"Meidan Emam (Naqsh-e Jahan Square), Isfahan","ru":"Площадь Нагш-э-Джахан (Майдан-э-Имам)","uz":"Naqsh-e Jahon maydoni, Isfahon","zh":"伊玛目广场"}'::jsonb,
                    'IR','isfahan',32.657028,51.677322,1598::smallint,'115'),
                ('ir-tabriz-bazaar','monument',
                    '{"en":"Tabriz Historic Bazaar Complex","ru":"Исторический базар Тебриза","uz":"Tabriz tarixiy bozori","zh":"大不里士历史集市"}'::jsonb,
                    'IR','tabriz',38.080800,46.297500,1000::smallint,'1346'),
                ('ir-naqsh-e-rostam','archaeological_site',
                    '{"en":"Naqsh-e Rostam — Achaemenid Royal Necropolis","ru":"Накш-э-Рустам — ахеменидский некрополь","uz":"Naqsh-e Rustam — Axemeniylar nekropoli","zh":"纳克希·鲁斯塔姆"}'::jsonb,
                    'IR','persepolis',29.993100,52.876400,-480::smallint,NULL),
                ('ir-ali-qapu-palace','palace',
                    '{"en":"Ali Qapu Palace, Isfahan","ru":"Дворец Али Капу","uz":"Ali Qapu saroyi","zh":"阿里卡普宫"}'::jsonb,
                    'IR','isfahan',32.657400,51.676100,1597::smallint,NULL),
                ('ir-sheikh-lotfollah-mosque','mosque',
                    '{"en":"Sheikh Lotfollah Mosque, Isfahan","ru":"Мечеть Шейха Лютфуллы","uz":"Shayx Lutfulloh masjidi","zh":"谢赫鲁特法拉清真寺"}'::jsonb,
                    'IR','isfahan',32.657500,51.678300,1618::smallint,NULL),
                ('ir-imam-mosque-isfahan','mosque',
                    '{"en":"Imam Mosque (Shah Mosque), Isfahan","ru":"Мечеть Имама (Мечеть Шаха)","uz":"Imom masjidi (Shoh masjidi)","zh":"伊玛目清真寺"}'::jsonb,
                    'IR','isfahan',32.655800,51.677600,1629::smallint,NULL),
                ('ir-chehel-sotoun','palace',
                    '{"en":"Chehel Sotoun Pavilion, Isfahan","ru":"Павильон Чехель Сотун","uz":"Chehel Sotun paviloni","zh":"四十柱宫"}'::jsonb,
                    'IR','isfahan',32.661400,51.666200,1647::smallint,NULL),
                ('ir-si-o-seh-pol','monument',
                    '{"en":"Si-o-Seh Pol (33-Arch Bridge), Isfahan","ru":"Мост Си-о-Сех Поль","uz":"Si-o-Seh Pol ko''prigi","zh":"33孔桥"}'::jsonb,
                    'IR','isfahan',32.637200,51.660600,1602::smallint,NULL),
                ('ir-nasir-ol-molk-mosque','mosque',
                    '{"en":"Nasir ol-Molk Mosque (Pink Mosque), Shiraz","ru":"Мечеть Насир уль-Мульк (Розовая мечеть)","uz":"Nosir ul-Mulk masjidi","zh":"纳西尔古兰清真寺"}'::jsonb,
                    'IR','shiraz',29.607700,52.531700,1888::smallint,NULL),
                ('ir-arg-e-bam','archaeological_site',
                    '{"en":"Arg-e Bam (Bam Citadel)","ru":"Арк Бам — цитадель Бам","uz":"Arg-e Bam qal''asi","zh":"巴姆古城"}'::jsonb,
                    'IR','bam',29.118600,58.369200,500::smallint,'1208'),
                ('ir-shushtar-hydraulics','archaeological_site',
                    '{"en":"Shushtar Historical Hydraulic System","ru":"Историческая гидравлическая система Шуштара","uz":"Shushtar tarixiy gidravlik tizimi","zh":"舒什塔尔历史水利系统"}'::jsonb,
                    'IR','isfahan',32.034900,48.856600,-400::smallint,'1315'),
                ('ir-golestan-palace','palace',
                    '{"en":"Golestan Palace, Tehran","ru":"Дворец Голестан","uz":"Guliston saroyi, Tehron","zh":"古列斯坦宫"}'::jsonb,
                    'IR','tehran',35.680556,51.414167,1524::smallint,'1422'),
                ('ir-persian-qanats','archaeological_site',
                    '{"en":"Persian Qanats — Ancient Underground Irrigation","ru":"Персидские каризы","uz":"Fors qorezlari","zh":"波斯坎儿井"}'::jsonb,
                    'IR','yazd',32.668400,54.356200,-1000::smallint,'1506'),
                ('ir-yazd-old-city','monument',
                    '{"en":"Historic City of Yazd","ru":"Исторический город Йезд","uz":"Yazd tarixiy shahri","zh":"亚兹德历史古城"}'::jsonb,
                    'IR','yazd',31.897200,54.358100,500::smallint,'1544'),
                ('ir-isfahan-jameh-mosque','mosque',
                    '{"en":"Jameh Mosque of Isfahan","ru":"Соборная мечеть Исфахана","uz":"Isfahon Jome masjidi","zh":"伊斯法罕聚礼清真寺"}'::jsonb,
                    'IR','isfahan',32.669700,51.686300,771::smallint,'1397'),
                ('ir-tomb-of-hafez','mausoleum',
                    '{"en":"Tomb of Hafez, Shiraz","ru":"Мавзолей Хафиза, Шираз","uz":"Hofiz maqbarasi, Sheroz","zh":"哈菲兹陵墓"}'::jsonb,
                    'IR','shiraz',29.617600,52.525800,1389::smallint,NULL),
                ('ir-eram-garden','monument',
                    '{"en":"Eram Garden, Shiraz","ru":"Сад Эрам","uz":"Eram bog''i","zh":"伊拉姆花园"}'::jsonb,
                    'IR','shiraz',29.626900,52.514700,1000::smallint,NULL),
                ('ir-tomb-cyrus','mausoleum',
                    '{"en":"Tomb of Cyrus — Pasargadae","ru":"Гробница Кира, Пасаргады","uz":"Kir qabri, Pasargadae","zh":"居鲁士之墓"}'::jsonb,
                    'IR','persepolis',30.193389,53.166611,-530::smallint,NULL),
                ('ir-mashhad-shrine','mosque',
                    '{"en":"Imam Reza Shrine Complex, Mashhad","ru":"Комплекс мечети Имама Резы","uz":"Imom Rizo ibodatxona kompleksi","zh":"伊玛目礼萨神殿"}'::jsonb,
                    'IR','mashhad',36.284800,59.616400,818::smallint,NULL),
                ('ir-kashan-fin-garden','monument',
                    '{"en":"Fin Garden, Kashan","ru":"Сад Фин, Кашан","uz":"Fin bog''i, Koshan","zh":"芬恩花园"}'::jsonb,
                    'IR','kashan',33.981400,51.004200,1587::smallint,NULL),
                ('ir-ganjali-khan-complex','monument',
                    '{"en":"Ganjali Khan Complex, Kerman","ru":"Комплекс Ганджали Хан, Керман","uz":"Ganjali Xon kompleksi, Kerman","zh":"甘贾利汗建筑群"}'::jsonb,
                    'IR','kerman',30.282200,57.078400,1596::smallint,NULL),
                ('ir-apadana-susa','archaeological_site',
                    '{"en":"Susa — Apadana Palace","ru":"Суза — Дворец Ападана","uz":"Suza — Apadana saroyi","zh":"苏萨阿帕达纳宫"}'::jsonb,
                    'IR','tehran',32.188300,48.257500,-521::smallint,NULL),
                ('ir-mount-damavand','monument',
                    '{"en":"Mount Damavand (sacred volcano)","ru":"Гора Дамаванд","uz":"Damavand tog''i","zh":"达马万德峰"}'::jsonb,
                    'IR','tehran',35.953400,52.109200,NULL::smallint,NULL),
                ('ir-badab-e-surt','monument',
                    '{"en":"Badab-e Surt Terraced Springs","ru":"Терассовые источники Бадаб-э-Сурт","uz":"Badab-e Surt basamali buloqlari","zh":"巴达布苏尔特台地泉"}'::jsonb,
                    'IR','tehran',36.017000,53.440000,NULL::smallint,NULL),
                ('ir-abarqu-cypress','monument',
                    '{"en":"Sarv-e Abarqu (4000-year-old cypress)","ru":"Кипарис Абаркух","uz":"Abarqu semiraga daraxti","zh":"阿巴尔库古柏树"}'::jsonb,
                    'IR','yazd',31.120600,53.278100,-2000::smallint,NULL),
                ('ir-tabriz-blue-mosque','mosque',
                    '{"en":"Blue Mosque (Masjid-i-Kabud), Tabriz","ru":"Голубая мечеть Тебриза","uz":"Tabriz Ko''k masjidi","zh":"大不里士蓝色清真寺"}'::jsonb,
                    'IR','tabriz',38.083300,46.296700,1465::smallint,NULL),
                ('ir-gombad-e-qabus','monument',
                    '{"en":"Gonbad-e Qabus Tower","ru":"Башня Гумбед-э-Кабус","uz":"Gumbad-e Qabus minorasi","zh":"卡布斯塔"}'::jsonb,
                    'IR','tehran',37.250000,55.166700,1006::smallint,'1398'),
                ('ir-shahr-i-sokhta','archaeological_site',
                    '{"en":"Shahr-i Sokhta — Burnt City","ru":"Шахри-Сохта — Сожжённый город","uz":"Shaxri Suxta — Yongan shahar","zh":"沙赫里索克塔"}'::jsonb,
                    'IR','tehran',30.585600,61.400800,-3200::smallint,'1456'),

                -- ===================== Turkey (30) ==========================
                ('tr-goreme-national-park','cave',
                    '{"en":"Göreme National Park & Rock Sites of Cappadocia","ru":"Национальный парк Гёреме и скальные объекты Каппадокии","uz":"Goreme milliy parki va Kappadokiya tosh shaharlari","zh":"格雷梅国家公园和卡帕多西亚石窟"}'::jsonb,
                    'TR','goreme',38.671389,34.829167,200::smallint,'357'),
                ('tr-historic-areas-istanbul','monument',
                    '{"en":"Historic Areas of Istanbul","ru":"Исторические места Стамбула","uz":"Istanbul tarixiy joylari","zh":"伊斯坦布尔历史区域"}'::jsonb,
                    'TR','istanbul',41.005278,28.976111,1000::smallint,'356'),
                ('tr-divrigi-mosque','mosque',
                    '{"en":"Great Mosque and Hospital of Divrigi","ru":"Большая мечеть и больница Дивриги","uz":"Divrigi ulug'' masjidi va kasalxonasi","zh":"迪夫里伊大清真寺和医院"}'::jsonb,
                    'TR','ankara',39.372700,38.122500,1228::smallint,'358'),
                ('tr-hattusha','archaeological_site',
                    '{"en":"Hattusha — Hittite Capital","ru":"Хаттуша — столица хеттов","uz":"Xattusha — Xetlar poytaxti","zh":"哈图沙——赫梯首都"}'::jsonb,
                    'TR','ankara',40.016300,34.615100,-1800::smallint,'377'),
                ('tr-nemrut-dag','monument',
                    '{"en":"Nemrut Dağ — Commagene Royal Sanctuary","ru":"Немрут-Даг — царское святилище Коммагены","uz":"Nemrut tog'' — Kommagen qirollik ziyoratgohi","zh":"内姆鲁特山"}'::jsonb,
                    'TR','gaziantep',37.980800,38.740900,-62::smallint,'448'),
                ('tr-xanthos-letoon','archaeological_site',
                    '{"en":"Xanthos-Letoon","ru":"Ксанф-Летоон","uz":"Ksanf-Letuon","zh":"希散托斯和勒托恩"}'::jsonb,
                    'TR','antalya',36.355100,29.319900,-700::smallint,'484'),
                ('tr-hierapolis-pamukkale','monument',
                    '{"en":"Hierapolis-Pamukkale","ru":"Иераполис-Памуккале","uz":"Gerapol-Pamukkale","zh":"希拉波利斯-棉花堡"}'::jsonb,
                    'TR','izmir',37.920600,29.121300,-190::smallint,'485'),
                ('tr-troy','archaeological_site',
                    '{"en":"Troy (Troia)","ru":"Троя","uz":"Troya","zh":"特洛伊"}'::jsonb,
                    'TR','istanbul',39.957300,26.238900,-3000::smallint,'849'),
                ('tr-selimiye-mosque-edirne','mosque',
                    '{"en":"Selimiye Mosque, Edirne","ru":"Мечеть Селимие, Эдирне","uz":"Selimiya masjidi, Edirne","zh":"塞利米耶清真寺"}'::jsonb,
                    'TR','edirne',41.677400,26.557200,1575::smallint,'1366'),
                ('tr-catalhoyuk','archaeological_site',
                    '{"en":"Çatalhöyük Neolithic Site","ru":"Неолитическое поселение Чатал-Хёюк","uz":"Chatalhoyuk neolit shahri","zh":"恰塔尔赫于克"}'::jsonb,
                    'TR','konya',37.668300,32.827400,-7500::smallint,'1405'),
                ('tr-pergamon','archaeological_site',
                    '{"en":"Pergamon and its Multi-Layered Cultural Landscape","ru":"Пергам и его многослойный культурный ландшафт","uz":"Pergamon va uning ko''p qatlamli madaniy manzarasi","zh":"帕加马及其多层次文化景观"}'::jsonb,
                    'TR','izmir',39.131400,27.183500,-283::smallint,'1412'),
                ('tr-ephesus','archaeological_site',
                    '{"en":"Ephesus","ru":"Эфес","uz":"Efes","zh":"以弗所"}'::jsonb,
                    'TR','izmir',37.939200,27.341900,-1000::smallint,'1060'),
                ('tr-aphrodisias','archaeological_site',
                    '{"en":"Aphrodisias","ru":"Афродисиас","uz":"Afrodisias","zh":"阿弗罗迪西亚斯"}'::jsonb,
                    'TR','izmir',37.708000,28.722000,-500::smallint,'1455'),
                ('tr-arslantepe','archaeological_site',
                    '{"en":"Arslantepe Mound — Bronze Age Urban Complex","ru":"Курган Арслантепе","uz":"Arslantepe tepasi","zh":"阿尔斯兰特佩"}'::jsonb,
                    'TR','gaziantep',38.373600,38.391400,-4000::smallint,'1622'),
                ('tr-gordion','archaeological_site',
                    '{"en":"Gordion — Phrygian Capital","ru":"Гордион — столица фригийцев","uz":"Gordon — Frig poytaxti","zh":"戈尔迪温"}'::jsonb,
                    'TR','ankara',39.652800,31.998600,-900::smallint,'1658'),
                ('tr-sultanahmet-blue-mosque','mosque',
                    '{"en":"Sultan Ahmed Mosque (Blue Mosque), Istanbul","ru":"Мечеть Султанахмет (Голубая мечеть)","uz":"Sulton Ahmad masjidi (Ko''k masjid)","zh":"苏丹艾哈迈德清真寺"}'::jsonb,
                    'TR','istanbul',41.005278,28.976111,1616::smallint,NULL),
                ('tr-hagia-sophia','monument',
                    '{"en":"Hagia Sophia, Istanbul","ru":"Собор Святой Софии, Стамбул","uz":"Ayo Sofiya sobori, Istanbul","zh":"圣索菲亚大教堂"}'::jsonb,
                    'TR','istanbul',41.008583,28.980175,537::smallint,NULL),
                ('tr-topkapi-palace','palace',
                    '{"en":"Topkapi Palace, Istanbul","ru":"Дворец Топкапы","uz":"Topqapi saroyi","zh":"托普卡匹宫"}'::jsonb,
                    'TR','istanbul',41.011667,28.983333,1465::smallint,NULL),
                ('tr-galata-tower','monument',
                    '{"en":"Galata Tower, Istanbul","ru":"Галатская башня","uz":"Galata minorasi","zh":"加拉太塔"}'::jsonb,
                    'TR','istanbul',41.025700,28.974000,1348::smallint,NULL),
                ('tr-basilica-cistern','monument',
                    '{"en":"Basilica Cistern, Istanbul","ru":"Базиликальная цистерна","uz":"Bazilika suv ombori","zh":"地下宫殿水库"}'::jsonb,
                    'TR','istanbul',41.008500,28.977800,532::smallint,NULL),
                ('tr-dolmabahce-palace','palace',
                    '{"en":"Dolmabahçe Palace, Istanbul","ru":"Дворец Долмабахче","uz":"Dolmabahe saroyi","zh":"多尔马巴赫切宫"}'::jsonb,
                    'TR','istanbul',41.039200,29.000600,1856::smallint,NULL),
                ('tr-mevlana-museum-konya','museum',
                    '{"en":"Mevlâna Museum (Rumi Mausoleum), Konya","ru":"Музей Мевлана, Конья","uz":"Mavlono muzeyi, Konya","zh":"梅夫拉纳博物馆"}'::jsonb,
                    'TR','konya',37.871100,32.504900,1274::smallint,NULL),
                ('tr-bursa-green-mosque','mosque',
                    '{"en":"Green Mosque and Tomb, Bursa","ru":"Зелёная мечеть и усыпальница, Бурса","uz":"Yashil masjid va qabriston, Bursa","zh":"布尔萨绿色清真寺"}'::jsonb,
                    'TR','bursa',40.184400,29.072200,1421::smallint,NULL),
                ('tr-ani-ruins','archaeological_site',
                    '{"en":"Archaeological Site of Ani","ru":"Археологический сайт Ани","uz":"Ani arxeologik maydoni","zh":"阿尼遗址"}'::jsonb,
                    'TR','trabzon',40.508900,43.573400,961::smallint,'1518'),
                ('tr-diyarbakir-fortress','monument',
                    '{"en":"Diyarbakır Fortress & Hevsel Gardens","ru":"Крепость Диярбакыр и сады Хевсель","uz":"Diyarbakar qal''asi va Xevsel bog''lari","zh":"迪亚巴克尔城堡和赫夫塞尔花园"}'::jsonb,
                    'TR','gaziantep',37.912300,40.228800,-900::smallint,'1488'),
                ('tr-sumela-monastery','monastery',
                    '{"en":"Sumela Monastery, Trabzon","ru":"Монастырь Сумела","uz":"Sumela monastiri","zh":"苏美拉修道院"}'::jsonb,
                    'TR','trabzon',40.691100,39.660300,386::smallint,NULL),
                ('tr-aspendos-theatre','monument',
                    '{"en":"Aspendos Roman Theatre","ru":"Римский театр Аспенд","uz":"Aspendos Rim teatri","zh":"阿斯彭多斯罗马剧场"}'::jsonb,
                    'TR','antalya',36.938100,31.170600,155::smallint,NULL),
                ('tr-library-celsus','monument',
                    '{"en":"Library of Celsus, Ephesus","ru":"Библиотека Цельса, Эфес","uz":"Tsels kutubxonasi, Efes","zh":"塞尔苏斯图书馆"}'::jsonb,
                    'TR','izmir',37.939700,27.341200,117::smallint,NULL),
                ('tr-urfa-gobekli-tepe','archaeological_site',
                    '{"en":"Göbekli Tepe — World''s Oldest Temple","ru":"Гёбекли-Тепе — старейший храм мира","uz":"Gobeklitepa — dunyodagi eng qadimgi ibodatxona","zh":"哥贝克力石阵"}'::jsonb,
                    'TR','gaziantep',37.223100,38.922500,-9600::smallint,'1572'),
                ('tr-troy-museum','museum',
                    '{"en":"Troy Museum, Çanakkale","ru":"Музей Трои, Чанаккале","uz":"Troya muzeyi","zh":"特洛伊博物馆"}'::jsonb,
                    'TR','istanbul',39.988900,26.348900,2018::smallint,NULL),

                -- ===================== India (30) ===========================
                ('in-taj-mahal','mausoleum',
                    '{"en":"Taj Mahal, Agra","ru":"Тадж-Махал, Агра","uz":"Toj Maxal, Agra","zh":"泰姬陵"}'::jsonb,
                    'IN','agra',27.175015,78.042155,1648::smallint,'252'),
                ('in-agra-fort','palace',
                    '{"en":"Agra Fort","ru":"Форт Агра","uz":"Agra qal''asi","zh":"阿格拉堡"}'::jsonb,
                    'IN','agra',27.179872,78.021851,1565::smallint,'251'),
                ('in-fatehpur-sikri','monument',
                    '{"en":"Fatehpur Sikri","ru":"Фатехпур-Сикри","uz":"Fatehpur Sikri","zh":"法塔赫布尔西格里"}'::jsonb,
                    'IN','agra',27.094444,77.660278,1571::smallint,'255'),
                ('in-humayuns-tomb','mausoleum',
                    '{"en":"Humayun''s Tomb, Delhi","ru":"Гробница Хумаюна","uz":"Humoyun maqbarasi, Dehli","zh":"胡马雍陵"}'::jsonb,
                    'IN','delhi',28.593261,77.250640,1570::smallint,'232'),
                ('in-qutb-minar','monument',
                    '{"en":"Qutb Minar and its Monuments, Delhi","ru":"Кутб-Минар и связанные памятники","uz":"Qutb Minar va uning yodgorliklari","zh":"顾特卜塔"}'::jsonb,
                    'IN','delhi',28.524403,77.185532,1193::smallint,'233'),
                ('in-red-fort-delhi','palace',
                    '{"en":"Red Fort Complex, Delhi","ru":"Красный форт, Дели","uz":"Qizil qal''a, Dehli","zh":"红堡"}'::jsonb,
                    'IN','delhi',28.656159,77.241006,1648::smallint,'231'),
                ('in-mahabalipuram','archaeological_site',
                    '{"en":"Group of Monuments at Mahabalipuram","ru":"Группа памятников Махабалипурам","uz":"Maxabalipuram yodgorliklari","zh":"默哈伯利布勒姆建筑群"}'::jsonb,
                    'IN','chennai',12.616700,80.199700,700::smallint,'249'),
                ('in-ajanta-caves','cave',
                    '{"en":"Ajanta Caves","ru":"Пещеры Аджанта","uz":"Ajanta g''orlari","zh":"阿旃陀石窟"}'::jsonb,
                    'IN','ajanta',20.551900,75.700100,-200::smallint,'242'),
                ('in-ellora-caves','cave',
                    '{"en":"Ellora Caves","ru":"Пещеры Эллора","uz":"Ellora g''orlari","zh":"埃洛拉石窟"}'::jsonb,
                    'IN','ajanta',20.026900,75.177900,600::smallint,'243'),
                ('in-elephanta-caves','cave',
                    '{"en":"Elephanta Caves, Mumbai","ru":"Пещеры Элефанта, Мумбай","uz":"Elefanta g''orlari","zh":"象岛石窟"}'::jsonb,
                    'IN','mumbai',18.963600,72.931600,550::smallint,'244'),
                ('in-hampi-ruins','archaeological_site',
                    '{"en":"Group of Monuments at Hampi","ru":"Группа памятников в Хампи","uz":"Xampi yodgorliklari","zh":"亨比建筑群"}'::jsonb,
                    'IN','hampi',15.335000,76.462200,1336::smallint,'241'),
                ('in-pattadakal','monument',
                    '{"en":"Group of Monuments at Pattadakal","ru":"Группа памятников Паттадакала","uz":"Pattadakal yodgorliklari","zh":"帕塔达卡尔建筑群"}'::jsonb,
                    'IN','hampi',15.948800,75.818600,740::smallint,'239'),
                ('in-khajuraho-temples','temple',
                    '{"en":"Khajuraho Group of Monuments","ru":"Группа памятников Кхаджурахо","uz":"Xajuraxo yodgorliklari","zh":"卡朱拉霍建筑群"}'::jsonb,
                    'IN','khajuraho',24.851700,79.921700,950::smallint,'240'),
                ('in-konarak-sun-temple','temple',
                    '{"en":"Sun Temple, Konark","ru":"Храм Солнца, Конарк","uz":"Quyosh ibodatxonasi, Konark","zh":"科纳克太阳神庙"}'::jsonb,
                    'IN','kolkata',19.887600,86.094500,1255::smallint,'246'),
                ('in-sanchi-stupa','monument',
                    '{"en":"Buddhist Monuments at Sanchi","ru":"Буддийские памятники Санчи","uz":"Sanchi buddaviy yodgorliklari","zh":"桑奇佛教古迹"}'::jsonb,
                    'IN','delhi',23.479200,77.740600,-300::smallint,'524'),
                ('in-rani-ki-vav','monument',
                    '{"en":"Rani-ki-Vav (the Queen''s Stepwell)","ru":"Рани-ки-Вав — «Колодец королевы»","uz":"Rani-ki-Vav — Qirolicha qudugi","zh":"拉尼基瓦夫阶梯井"}'::jsonb,
                    'IN','delhi',23.858100,72.101300,1063::smallint,'922'),
                ('in-nalanda-mahavihara','archaeological_site',
                    '{"en":"Nalanda Mahavihara Archaeological Site","ru":"Археологический памятник Наланда","uz":"Nalanda Maxavikhara arxeologik maydoni","zh":"那烂陀寺考古遗址"}'::jsonb,
                    'IN','kolkata',25.135800,85.443600,427::smallint,'1502'),
                ('in-jaipur-walled-city','monument',
                    '{"en":"Jaipur — the Walled City","ru":"Джайпур — город-крепость","uz":"Jaypur — devorli shahar","zh":"斋浦尔围城"}'::jsonb,
                    'IN','jaipur',26.912434,75.787270,1727::smallint,'1603'),
                ('in-amber-fort','palace',
                    '{"en":"Amber Fort, Jaipur","ru":"Форт Амбер, Джайпур","uz":"Amber qal''asi, Jaypur","zh":"琥珀宫"}'::jsonb,
                    'IN','jaipur',26.985498,75.850693,1592::smallint,NULL),
                ('in-hawa-mahal','palace',
                    '{"en":"Hawa Mahal (Palace of Winds), Jaipur","ru":"Хава-Махал (Дворец ветров)","uz":"Hava Maxal (Shamollar saroyi)","zh":"风之宫殿"}'::jsonb,
                    'IN','jaipur',26.923889,75.826669,1799::smallint,NULL),
                ('in-varanasi-ghats','monument',
                    '{"en":"Ghats of Varanasi (Kashi)","ru":"Гхаты Варанаси","uz":"Varanasi (Koshi) gxatlari","zh":"瓦拉纳西河坛"}'::jsonb,
                    'IN','varanasi',25.309500,83.013700,-1000::smallint,NULL),
                ('in-golden-temple-amritsar','temple',
                    '{"en":"Harmandir Sahib (Golden Temple), Amritsar","ru":"Золотой Храм, Амритсар","uz":"Oltin ibodatxona, Amritsar","zh":"哈曼底尔萨希布黄金神庙"}'::jsonb,
                    'IN','delhi',31.620000,74.876100,1577::smallint,NULL),
                ('in-victoria-memorial-kolkata','monument',
                    '{"en":"Victoria Memorial, Kolkata","ru":"Мемориал Виктории, Калькутта","uz":"Viktoriya memoriali, Kalkutta","zh":"维多利亚纪念馆"}'::jsonb,
                    'IN','kolkata',22.544900,88.342700,1906::smallint,NULL),
                ('in-gateway-of-india','monument',
                    '{"en":"Gateway of India, Mumbai","ru":"Ворота Индии, Мумбай","uz":"Hindiston darvozasi, Mumbay","zh":"印度门"}'::jsonb,
                    'IN','mumbai',18.921900,72.834700,1924::smallint,NULL),
                ('in-chhatrapati-shivaji-terminus','monument',
                    '{"en":"Chhatrapati Shivaji Maharaj Terminus, Mumbai","ru":"Терминал Чхатрапати Шиваджи","uz":"Chxatrapati Shivaji terminali","zh":"贾特拉帕蒂·希瓦吉终点站"}'::jsonb,
                    'IN','mumbai',18.940200,72.835600,1887::smallint,'945'),
                ('in-sun-temple-modhera','temple',
                    '{"en":"Sun Temple, Modhera, Gujarat","ru":"Храм Солнца, Модхера","uz":"Quyosh ibodatxonasi, Modhera","zh":"莫德拉太阳神庙"}'::jsonb,
                    'IN','delhi',23.579300,72.129200,1026::smallint,NULL),
                ('in-bodh-gaya','monument',
                    '{"en":"Mahabodhi Temple Complex, Bodh Gaya","ru":"Буддийский комплекс Бодх-Гая","uz":"Maxabodxi ibodatxona kompleksi, Bodxi-Gaya","zh":"摩诃菩提寺"}'::jsonb,
                    'IN','kolkata',24.695800,84.991400,-500::smallint,'1056'),
                ('in-kailasa-temple-ellora','temple',
                    '{"en":"Kailasa Temple, Ellora Caves","ru":"Храм Кайласа, пещеры Эллора","uz":"Kaylasa ibodatxonasi, Ellora","zh":"凯拉萨神庙"}'::jsonb,
                    'IN','ajanta',20.023500,75.178900,757::smallint,NULL),
                ('in-meenakshi-temple','temple',
                    '{"en":"Meenakshi Amman Temple, Madurai","ru":"Храм Минакши, Мадурай","uz":"Minakshi ibodatxonasi, Madurai","zh":"米纳克希神庙"}'::jsonb,
                    'IN','chennai',9.919900,78.119500,1600::smallint,NULL),
                ('in-golconda-fort','palace',
                    '{"en":"Golconda Fort, Hyderabad","ru":"Форт Голконда, Хайдарабад","uz":"Golkonda qal''asi, Haydarobod","zh":"戈尔孔达堡"}'::jsonb,
                    'IN','chennai',17.383100,78.402000,1143::smallint,NULL),
                ('in-padmanabhapuram-palace','palace',
                    '{"en":"Padmanabhapuram Palace, Kerala","ru":"Дворец Падманабхапурам","uz":"Padmanabxapuram saroyi","zh":"帕德玛纳巴普拉姆宫"}'::jsonb,
                    'IN','chennai',8.249900,77.326100,1601::smallint,NULL)
        ),
        site_levels AS (
            INSERT INTO geographic_admin_levels
                (parent_id, level, admin_level_type, code, name, country_code,
                 centroid_lat, centroid_lng, path)
            SELECT
                COALESCE(city_lvl.id, country_lvl.id),
                5,
                'site',
                upper(hs.country_code) || '.' || upper(replace(hs.pub_id, '-', '_')),
                hs.name,
                hs.country_code,
                hs.lat,
                hs.lng,
                (
                    COALESCE(city_lvl.path::text, country_lvl.path::text)
                    || '.' || replace(hs.pub_id, '-', '_')
                )::ltree
            FROM heritage_seeds hs
            JOIN geographic_admin_levels country_lvl ON
                country_lvl.country_code = hs.country_code
                AND country_lvl.admin_level_type = 'country'
            LEFT JOIN geographic_admin_levels city_lvl ON
                hs.city_slug IS NOT NULL
                AND city_lvl.admin_level_type = 'city'
                AND city_lvl.country_code = hs.country_code
                AND city_lvl.code = upper(hs.country_code) || '.' || upper(hs.city_slug)
            WHERE NOT EXISTS (
                SELECT 1 FROM geographic_admin_levels existing
                WHERE existing.code = upper(hs.country_code) || '.' || upper(replace(hs.pub_id, '-', '_'))
                  AND existing.admin_level_type = 'site'
            )
            RETURNING id, code
        )
        INSERT INTO heritage_objects
            (tenant_id, pub_id, kind_slug, name, country_code, latitude, longitude,
             period_start_year, status, admin_level_id, confidence_score)
        SELECT
            dt.id,
            hs.pub_id,
            hs.kind_slug,
            hs.name,
            hs.country_code,
            hs.lat,
            hs.lng,
            hs.period_start_year,
            'published',
            sl.id,
            75
        FROM heritage_seeds hs
        CROSS JOIN default_tenant dt
        LEFT JOIN site_levels sl
            ON sl.code = upper(hs.country_code) || '.' || upper(replace(hs.pub_id, '-', '_'))
        ON CONFLICT (pub_id) DO NOTHING;
        """
    )

    # --- 6. UNESCO inscriptions -----------------------------------------------
    op.execute(
        """
        WITH unesco_seeds(pub_id, inscription_id, year, criteria, category,
                          area_ha, statement) AS (
            VALUES
                -- China
                ('cn-great-wall-beijing','438',1987::smallint,
                    ARRAY['i','ii','iii','iv','vi'], 'cultural',
                    23500.0::numeric,
                    '{"en":"The Great Wall was built to protect China from nomadic invasions; it stretches more than 6,700 km."}'::jsonb),
                ('cn-mogao-caves','440',1987::smallint,
                    ARRAY['i','ii','iii','iv','v','vi'], 'cultural',
                    38.8::numeric,
                    '{"en":"Located along the Silk Road, the Mogao Caves are the finest example of Buddhist art spanning 1,000 years."}'::jsonb),
                ('cn-silk-road-changan-tianshan','1442',2014::smallint,
                    ARRAY['ii','iii','v','vi'], 'cultural',
                    42668.0::numeric,
                    '{"en":"The Chang''an-Tianshan Corridor is the best-preserved section of the ancient Silk Roads."}'::jsonb),
                ('cn-terracotta-army','441',1987::smallint,
                    ARRAY['i','iii','iv','vi'], 'cultural',
                    2.13::numeric,
                    '{"en":"The Mausoleum of the First Qin Emperor with the terracotta warriors is an outstanding example of ancient Chinese civilization."}'::jsonb),
                -- Iran
                ('ir-persepolis','114',1979::smallint,
                    ARRAY['i','iii','vi'], 'cultural',
                    1340.0::numeric,
                    '{"en":"Persepolis was the capital of the Achaemenid Empire and is one of the finest examples of ancient ceremonial architecture."}'::jsonb),
                ('ir-pasargadae','1106',2004::smallint,
                    ARRAY['i','ii','iii','iv'], 'cultural',
                    160.0::numeric,
                    '{"en":"Pasargadae was the first dynastic capital of the Achaemenid Empire; the Tomb of Cyrus is an outstanding monument."}'::jsonb),
                ('ir-meidan-emam-isfahan','115',1979::smallint,
                    ARRAY['i','v','vi'], 'cultural',
                    490.0::numeric,
                    '{"en":"Naqsh-e Jahan Square in Isfahan is one of the largest public squares in the world and an outstanding example of Islamic architecture."}'::jsonb),
                ('ir-tabriz-bazaar','1346',2010::smallint,
                    ARRAY['ii','iii','iv'], 'cultural',
                    39.7::numeric,
                    '{"en":"Tabriz Historic Bazaar Complex is one of the oldest bazaars in the Middle East and a major trading hub on the Silk Road."}'::jsonb),
                -- Turkey
                ('tr-goreme-national-park','357',1985::smallint,
                    ARRAY['i','iii','v','vii'], 'mixed',
                    9576.0::numeric,
                    '{"en":"Göreme National Park contains rock-hewn sanctuaries that provide an incomparable view of Byzantine art."}'::jsonb),
                ('tr-historic-areas-istanbul','356',1985::smallint,
                    ARRAY['i','ii','iii','iv'], 'cultural',
                    765.0::numeric,
                    '{"en":"Istanbul''s historic areas include some of the world''s greatest architectural masterpieces."}'::jsonb),
                ('tr-hierapolis-pamukkale','485',1988::smallint,
                    ARRAY['iii','iv','vii'], 'mixed',
                    10762.0::numeric,
                    '{"en":"Hierapolis-Pamukkale features stunning white travertine terraces and an ancient Greco-Roman city."}'::jsonb),
                ('tr-ephesus','1060',2015::smallint,
                    ARRAY['iii','iv','vi'], 'cultural',
                    2100.0::numeric,
                    '{"en":"Ephesus contains the largest collection of Roman ruins in the eastern Mediterranean."}'::jsonb),
                -- India
                ('in-taj-mahal','252',1983::smallint,
                    ARRAY['i'], 'cultural',
                    170.0::numeric,
                    '{"en":"The Taj Mahal is one of the universally admired masterpieces of the world''s heritage."}'::jsonb),
                ('in-ajanta-caves','242',1983::smallint,
                    ARRAY['i','ii','iii','vi'], 'cultural',
                    3.7::numeric,
                    '{"en":"The Ajanta Caves are the finest surviving examples of ancient Indian art and the earliest Buddhist cave paintings."}'::jsonb),
                ('in-humayuns-tomb','232',1993::smallint,
                    ARRAY['ii','iv'], 'cultural',
                    11.56::numeric,
                    '{"en":"Humayun''s Tomb was the first garden-tomb on the Indian subcontinent and inspired several major architectural innovations."}'::jsonb)
        )
        INSERT INTO unesco_inscriptions
            (heritage_id, inscription_id, inscription_year, criteria, category,
             status, area_hectares, statement, official_url)
        SELECT
            ho.id,
            us.inscription_id,
            us.year,
            us.criteria,
            us.category,
            'inscribed',
            us.area_ha,
            us.statement,
            'https://whc.unesco.org/en/list/' || us.inscription_id
        FROM unesco_seeds us
        JOIN heritage_objects ho ON ho.pub_id = us.pub_id
        ON CONFLICT (inscription_id) DO NOTHING;
        """
    )

    # --- 7. Update heritage_objects.unesco_inscription_year ------------------
    op.execute(
        """
        UPDATE heritage_objects ho
        SET unesco_inscription_year = ui.inscription_year
        FROM unesco_inscriptions ui
        WHERE ui.heritage_id = ho.id
          AND ho.unesco_inscription_year IS NULL;
        """
    )

    # --- 8. Heritage facts (provenance — UNESCO inscription year) ------------
    op.execute(
        """
        INSERT INTO heritage_facts
            (heritage_id, predicate, object_value, confidence, is_winning, asserted_at)
        SELECT
            ui.heritage_id,
            'unesco_inscription_year',
            to_jsonb(ui.inscription_year),
            95,
            true,
            now()
        FROM unesco_inscriptions ui
        WHERE EXISTS (
            SELECT 1 FROM heritage_objects ho
            WHERE ho.id = ui.heritage_id
              AND ho.pub_id IN (
                'cn-great-wall-beijing','cn-mogao-caves',
                'cn-silk-road-changan-tianshan','cn-terracotta-army',
                'ir-persepolis','ir-pasargadae',
                'ir-meidan-emam-isfahan','ir-tabriz-bazaar',
                'tr-goreme-national-park','tr-historic-areas-istanbul',
                'tr-hierapolis-pamukkale','tr-ephesus',
                'in-taj-mahal','in-ajanta-caves','in-humayuns-tomb'
              )
        )
          AND NOT EXISTS (
            SELECT 1 FROM heritage_facts hf
            WHERE hf.heritage_id = ui.heritage_id
              AND hf.predicate = 'unesco_inscription_year'
              AND hf.is_winning
              AND hf.superseded_at IS NULL
          );
        """
    )

    # --- 9. Fact provenance links ---------------------------------------------
    op.execute(
        """
        INSERT INTO fact_provenance (fact_id, provenance_id, confidence)
        SELECT
            hf.id,
            hp.id,
            95
        FROM heritage_facts hf
        JOIN heritage_provenance hp ON hp.slug = 'unesco_whc'
        WHERE hf.predicate = 'unesco_inscription_year'
        ON CONFLICT (fact_id, provenance_id) DO NOTHING;
        """
    )

    # --- 10. Dynasty associations -------------------------------------------
    op.execute(
        """
        WITH dyn_links(pub_id, dynasty_slug, role) AS (
            VALUES
                ('cn-terracotta-army','qin','built_under'),
                ('cn-forbidden-city','ming','built_under'),
                ('cn-summer-palace','qing','built_under'),
                ('cn-ming-tombs','ming','built_under'),
                ('cn-silk-road-changan-tianshan','tang','flourished_under'),
                ('cn-giant-wild-goose-pagoda','tang','built_under'),
                ('cn-small-wild-goose-pagoda','tang','built_under'),
                ('cn-longmen-grottoes','tang','flourished_under'),
                ('cn-kashgar-abakh-khoja','timurid','associated_with'),
                ('ir-persepolis','achaemenid','built_under'),
                ('ir-pasargadae','achaemenid','built_under'),
                ('ir-naqsh-e-rostam','achaemenid','built_under'),
                ('ir-meidan-emam-isfahan','safavid','built_under'),
                ('ir-ali-qapu-palace','safavid','built_under'),
                ('ir-imam-mosque-isfahan','safavid','built_under'),
                ('ir-sheikh-lotfollah-mosque','safavid','built_under'),
                ('ir-golestan-palace','qajar','built_under'),
                ('in-taj-mahal','mughal','built_under'),
                ('in-agra-fort','mughal','built_under'),
                ('in-red-fort-delhi','mughal','built_under'),
                ('in-humayuns-tomb','mughal','built_under'),
                ('in-fatehpur-sikri','mughal','built_under'),
                ('in-qutb-minar','delhi_sultanate','built_under'),
                ('tr-topkapi-palace','ottoman','built_under'),
                ('tr-sultanahmet-blue-mosque','ottoman','built_under'),
                ('tr-selimiye-mosque-edirne','ottoman','built_under'),
                ('tr-hagia-sophia','byzantine','built_under'),
                ('tr-hattusha','hittite','built_under')
        )
        INSERT INTO heritage_dynasty_assoc (heritage_id, dynasty_id, role, confidence)
        SELECT ho.id, d.id, dl.role, 85
        FROM dyn_links dl
        JOIN heritage_objects ho ON ho.pub_id = dl.pub_id
        JOIN dynasties d ON d.slug = dl.dynasty_slug
        ON CONFLICT (heritage_id, dynasty_id, role) DO NOTHING;
        """
    )

    # --- 11. Style associations ----------------------------------------------
    op.execute(
        """
        WITH style_links(pub_id, style_slug, is_primary) AS (
            VALUES
                ('cn-mogao-caves','buddhist',true),
                ('cn-longmen-grottoes','buddhist',true),
                ('cn-great-wall-beijing','chinese_imperial',true),
                ('cn-great-wall-jiayuguan','chinese_imperial',true),
                ('cn-forbidden-city','chinese_imperial',true),
                ('cn-summer-palace','chinese_imperial',true),
                ('cn-giant-wild-goose-pagoda','buddhist',true),
                ('cn-kashgar-id-kah','islamic',true),
                ('cn-kashgar-abakh-khoja','islamic',true),
                ('ir-persepolis','achaemenid_architecture',true),
                ('ir-pasargadae','achaemenid_architecture',true),
                ('ir-meidan-emam-isfahan','islamic',true),
                ('ir-ali-qapu-palace','safavid_architecture',true),
                ('ir-imam-mosque-isfahan','safavid_architecture',true),
                ('ir-sheikh-lotfollah-mosque','safavid_architecture',true),
                ('ir-golestan-palace','islamic',true),
                ('ir-nasir-ol-molk-mosque','islamic',true),
                ('tr-hagia-sophia','byzantine',true),
                ('tr-sultanahmet-blue-mosque','ottoman_architecture',true),
                ('tr-topkapi-palace','ottoman_architecture',true),
                ('tr-selimiye-mosque-edirne','ottoman_architecture',true),
                ('tr-hattusha','hittite_architecture',true),
                ('tr-hierapolis-pamukkale','hellenistic',true),
                ('tr-ephesus','hellenistic',true),
                ('in-taj-mahal','mughal_architecture',true),
                ('in-agra-fort','mughal_architecture',true),
                ('in-humayuns-tomb','mughal_architecture',true),
                ('in-fatehpur-sikri','mughal_architecture',true),
                ('in-qutb-minar','islamic',true),
                ('in-khajuraho-temples','hindu',true),
                ('in-konarak-sun-temple','hindu',true),
                ('in-ajanta-caves','buddhist',true),
                ('in-ellora-caves','buddhist',true),
                ('in-elephanta-caves','hindu',true)
        )
        INSERT INTO heritage_style_assoc (heritage_id, style_id, is_primary, confidence)
        SELECT ho.id, s.id, sl.is_primary, 85
        FROM style_links sl
        JOIN heritage_objects ho ON ho.pub_id = sl.pub_id
        JOIN architectural_styles s ON s.slug = sl.style_slug
        ON CONFLICT (heritage_id, style_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM heritage_objects
        WHERE pub_id LIKE 'cn-%' OR pub_id LIKE 'ir-%'
           OR pub_id LIKE 'tr-%' OR pub_id LIKE 'in-%';
        """
    )
    op.execute(
        """
        DELETE FROM geographic_admin_levels
        WHERE admin_level_type = 'site'
          AND country_code IN ('CN','IR','TR','IN');
        """
    )
    op.execute(
        """
        DELETE FROM cities
        WHERE country_code IN ('CN','IR','TR','IN')
          AND slug IN (
            'xian','dunhuang','urumqi','beijing','luoyang','zhangye','kashgar',
            'turpan','hangzhou','chengdu','suzhou',
            'isfahan','shiraz','tehran','yazd','tabriz','persepolis','mashhad','kashan','kerman','bam',
            'istanbul','ankara','izmir','konya','bursa','edirne','antalya','goreme','gaziantep','trabzon',
            'agra','delhi','jaipur','varanasi','mumbai','ajanta','hampi','khajuraho','kolkata','chennai'
          );
        """
    )
    op.execute(
        """
        DELETE FROM geographic_admin_levels
        WHERE admin_level_type = 'city'
          AND country_code IN ('CN','IR','TR','IN');
        """
    )
    op.execute("DELETE FROM prices WHERE pricing_zone_id IN (SELECT id FROM pricing_zones WHERE slug = 'silk_road_corridor');")
    op.execute("DELETE FROM pricing_zones WHERE slug = 'silk_road_corridor';")
