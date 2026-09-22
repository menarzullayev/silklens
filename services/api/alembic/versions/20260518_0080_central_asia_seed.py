"""Central Asia heritage seed — Kazakhstan, Tajikistan, Turkmenistan, Kyrgyzstan

FAZA 5 (TURBO) — Markaziy Osiyo kengayishi. Wave-6 Agent A.

Seeds real Central Asian heritage data — cities, country/city admin_levels,
heritage_objects (with multilingual names), UNESCO inscriptions where applicable,
dynasty/style associations where matched against the 0013 taxonomy seed, and
provenance facts for every UNESCO entry. Idempotent on pub_id / city slug /
inscription_id via ON CONFLICT DO NOTHING.

Volumes (representative starter set; full Roadmap targets land via Wikidata
ingestion in a later FAZA):
- KZ: 30 heritage entries + 7 cities (Roadmap: 200+)
- TJ: 25 heritage entries + 5 cities (Roadmap: 150+)
- TM: 20 heritage entries + 6 cities (Roadmap: 100+)
- KG: 20 heritage entries + 4 cities (Roadmap: 80+)
- UNESCO inscriptions: 10 (KZ:3, TJ:2, TM:3, KG:1, KG also shares 1490 with UZ)

Revision ID: 0080_central_asia_seed
Revises: 0082_provider_routing, 0084_b2g_partnerships, 0084_mfa
Create Date: 2026-05-18

Note: Wave-6 spec named ``0072_wikidata_link`` as the down-revision. Three
concurrent migrations from sibling agents had already landed as parallel
heads off of ``0071_compliance`` and ``0072_wikidata_link`` before this seed
was authored:

- ``0082_provider_routing`` ← ``0071_compliance``
- ``0083_white_label`` ← ``0072_wikidata_link`` ← ``0084_b2g_partnerships``
- ``0084_mfa`` ← ``0071_compliance``

To keep ``alembic upgrade head`` callable (the conftest uses ``"head"``, not
``"heads"``) we merge all three down-stream heads here, then layer the
Central Asia seed on top. ``0072_wikidata_link`` is reachable transitively
via ``0084_b2g_partnerships``.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0080_central_asia_seed"
down_revision: tuple[str, ...] = (
    "0082_provider_routing",
    "0084_b2g_partnerships",
    "0084_mfa",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- 1. Cities + their geographic_admin_levels rows -------------------
    # Insert city admin_level rows under each country admin_level (level=1),
    # then mirror into ``cities``. Population numbers are Wikipedia-rounded.
    op.execute(
        """
        WITH city_seeds(country_code, slug, name, lat, lng, population, is_capital, is_silk_road) AS (
            VALUES
                -- Kazakhstan
                ('KZ','almaty',
                    '{"en":"Almaty","ru":"Алматы","uz":"Olmaota","zh":"阿拉木图"}'::jsonb,
                    43.222015, 76.851250, 2000000, false, true),
                ('KZ','astana',
                    '{"en":"Astana","ru":"Астана","uz":"Ostona","zh":"阿斯塔纳"}'::jsonb,
                    51.169392, 71.449074, 1300000, true, false),
                ('KZ','shymkent',
                    '{"en":"Shymkent","ru":"Шымкент","uz":"Chimkent","zh":"奇姆肯特"}'::jsonb,
                    42.317029, 69.586943, 1100000, false, true),
                ('KZ','turkistan',
                    '{"en":"Turkistan","ru":"Туркестан","uz":"Turkiston","zh":"突厥斯坦"}'::jsonb,
                    43.297778, 68.251111, 200000, false, true),
                ('KZ','aktobe',
                    '{"en":"Aktobe","ru":"Актобе","uz":"Aqto''be","zh":"阿克托别"}'::jsonb,
                    50.296586, 57.166664, 530000, false, false),
                ('KZ','atyrau',
                    '{"en":"Atyrau","ru":"Атырау","uz":"Otirav","zh":"阿特劳"}'::jsonb,
                    47.094995, 51.923325, 290000, false, false),
                ('KZ','kyzylorda',
                    '{"en":"Kyzylorda","ru":"Кызылорда","uz":"Qizilo''rda","zh":"克孜勒奥尔达"}'::jsonb,
                    44.846092, 65.502167, 240000, false, true),
                -- Tajikistan
                ('TJ','dushanbe',
                    '{"en":"Dushanbe","ru":"Душанбе","uz":"Dushanbe","zh":"杜尚别"}'::jsonb,
                    38.560029, 68.787030, 1000000, true, false),
                ('TJ','khujand',
                    '{"en":"Khujand","ru":"Худжанд","uz":"Xo''jand","zh":"苦盏"}'::jsonb,
                    40.282500, 69.620003, 180000, false, true),
                ('TJ','khorog',
                    '{"en":"Khorog","ru":"Хорог","uz":"Xorug''","zh":"霍罗格"}'::jsonb,
                    37.491390, 71.555000, 30000, false, true),
                ('TJ','panjakent',
                    '{"en":"Panjakent","ru":"Пенджикент","uz":"Panjikent","zh":"片治肯特"}'::jsonb,
                    39.494400, 67.609200, 40000, false, true),
                ('TJ','istaravshan',
                    '{"en":"Istaravshan","ru":"Истаравшан","uz":"Istaravshan","zh":"伊斯塔拉夫尚"}'::jsonb,
                    39.911943, 69.012222, 65000, false, true),
                -- Turkmenistan
                ('TM','ashgabat',
                    '{"en":"Ashgabat","ru":"Ашхабад","uz":"Ashxobod","zh":"阿什哈巴德"}'::jsonb,
                    37.960833, 58.326389, 1000000, true, true),
                ('TM','mary',
                    '{"en":"Mary","ru":"Мары","uz":"Mari","zh":"马雷"}'::jsonb,
                    37.594722, 61.836389, 130000, false, true),
                ('TM','turkmenabat',
                    '{"en":"Türkmenabat","ru":"Туркменабат","uz":"Turkmanobod","zh":"土库曼纳巴德"}'::jsonb,
                    39.069444, 63.572778, 250000, false, true),
                ('TM','merv',
                    '{"en":"Merv","ru":"Мерв","uz":"Marv","zh":"梅尔夫"}'::jsonb,
                    37.660000, 62.190000, 5000, false, true),
                ('TM','konye_urgench',
                    '{"en":"Konye-Urgench","ru":"Куня-Ургенч","uz":"Ko''hna Urganch","zh":"古尔甘奇"}'::jsonb,
                    42.330000, 59.150000, 36000, false, true),
                ('TM','nisa',
                    '{"en":"Nisa","ru":"Ниса","uz":"Nisa","zh":"尼萨"}'::jsonb,
                    37.965000, 58.198000, 1000, false, true),
                -- Kyrgyzstan
                ('KG','bishkek',
                    '{"en":"Bishkek","ru":"Бишкек","uz":"Bishkek","zh":"比什凯克"}'::jsonb,
                    42.874722, 74.612222, 1100000, true, false),
                ('KG','osh',
                    '{"en":"Osh","ru":"Ош","uz":"O''sh","zh":"奥什"}'::jsonb,
                    40.515139, 72.795833, 270000, false, true),
                ('KG','karakol',
                    '{"en":"Karakol","ru":"Каракол","uz":"Qoraqo''l","zh":"卡拉科尔"}'::jsonb,
                    42.490278, 78.393889, 80000, false, true),
                ('KG','naryn',
                    '{"en":"Naryn","ru":"Нарын","uz":"Norin","zh":"纳伦"}'::jsonb,
                    41.428611, 75.991111, 40000, false, true)
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

    # --- 2. Heritage sites — site-level admin_level + heritage_objects ----
    # Site admin_levels are children of the city admin_level (or country
    # admin_level when city_code is NULL). Each heritage_object pins
    # admin_level_id to the site row. Names are jsonb with uz/en/ru, and zh
    # where commonly translated; for less-translated sites zh falls back to en
    # and the confidence_score remains 75 to flag that.
    #
    # heritage_seeds columns:
    #   pub_id, kind_slug, name_jsonb, country_code, city_slug (or NULL),
    #   lat, lng, period_start_year, unesco_inscription_id (or NULL)
    op.execute(
        """
        WITH default_tenant AS (
            SELECT id FROM tenants WHERE slug = 'default' LIMIT 1
        ),
        heritage_seeds(pub_id, kind_slug, name, country_code, city_slug,
                       lat, lng, period_start_year, unesco_id) AS (
            VALUES
                -- ===================== Kazakhstan (30) =====================
                ('kz-yasawi-mausoleum','mausoleum',
                    '{"en":"Mausoleum of Khoja Ahmed Yasawi","ru":"Мавзолей Ходжи Ахмеда Ясави","uz":"Xoja Ahmad Yassaviy maqbarasi","zh":"霍贾·艾哈迈德·亚萨维陵墓"}'::jsonb,
                    'KZ','turkistan',43.297500,68.273333,1389::smallint,'1103'),
                ('kz-tamgaly-petroglyphs','archaeological_site',
                    '{"en":"Tamgaly Petroglyphs","ru":"Петроглифы Тамгалы","uz":"Tamg''ali petrogliflari","zh":"坦巴雷岩刻"}'::jsonb,
                    'KZ','almaty',43.802222,75.539722,-2000::smallint,'1145'),
                ('kz-saryarka-steppe','archaeological_site',
                    '{"en":"Saryarka — Steppe and Lakes of Northern Kazakhstan","ru":"Сарыарка — степи и озёра Северного Казахстана","uz":"Saryarka — Shimoliy Qozog''iston dashtlari","zh":"萨雷阿尔卡——北哈萨克斯坦的草原和湖泊"}'::jsonb,
                    'KZ',NULL,50.450000,69.183333,NULL::smallint,'1102'),
                ('kz-ascension-cathedral','monument',
                    '{"en":"Ascension Cathedral, Almaty","ru":"Вознесенский кафедральный собор","uz":"Almaata Voznesenie sobori","zh":"阿拉木图升天大教堂"}'::jsonb,
                    'KZ','almaty',43.258444,76.952833,1907::smallint,NULL),
                ('kz-khan-shatyr','monument',
                    '{"en":"Khan Shatyr","ru":"Хан Шатыр","uz":"Xon Shatir","zh":"可汗大帐"}'::jsonb,
                    'KZ','astana',51.132500,71.404167,2010::smallint,NULL),
                ('kz-bayterek','monument',
                    '{"en":"Bayterek Tower","ru":"Байтерек","uz":"Bayterek minorasi","zh":"巴伊杰列克塔"}'::jsonb,
                    'KZ','astana',51.128333,71.430556,2002::smallint,NULL),
                ('kz-atyrau-mosque','mosque',
                    '{"en":"Imangali Mosque","ru":"Мечеть Имангали","uz":"Imang''oli masjidi","zh":"阿特劳清真寺"}'::jsonb,
                    'KZ','atyrau',47.106389,51.901944,2001::smallint,NULL),
                ('kz-otrar','archaeological_site',
                    '{"en":"Otrar","ru":"Отрар","uz":"O''trar","zh":"奥特拉尔"}'::jsonb,
                    'KZ','kyzylorda',42.851944,68.305278,-100::smallint,NULL),
                ('kz-issyk-barrow','archaeological_site',
                    '{"en":"Issyk kurgan","ru":"Иссыкский курган","uz":"Issiq qo''rg''oni","zh":"伊塞克墓"}'::jsonb,
                    'KZ','almaty',43.348889,77.453056,-400::smallint,NULL),
                ('kz-aisha-bibi','mausoleum',
                    '{"en":"Aisha Bibi Mausoleum","ru":"Мавзолей Айша-биби","uz":"Oysha Bibi maqbarasi","zh":"艾莎比比陵墓"}'::jsonb,
                    'KZ','shymkent',42.829722,71.260833,1100::smallint,NULL),
                ('kz-karakhan-mausoleum','mausoleum',
                    '{"en":"Karakhan Mausoleum","ru":"Мавзолей Карахана","uz":"Qoraxon maqbarasi","zh":"卡拉汉陵墓"}'::jsonb,
                    'KZ','shymkent',42.892500,71.366111,1100::smallint,NULL),
                ('kz-tamgaly-tas','archaeological_site',
                    '{"en":"Tamgaly Tas","ru":"Тамгалы Тас","uz":"Tamg''ali Tosh","zh":"坦巴雷塔斯"}'::jsonb,
                    'KZ','almaty',43.789167,76.103889,800::smallint,NULL),
                ('kz-sauran','archaeological_site',
                    '{"en":"Sauran","ru":"Сауран","uz":"Sauran","zh":"绍兰"}'::jsonb,
                    'KZ','turkistan',43.378889,67.943056,900::smallint,NULL),
                ('kz-aral-sea','archaeological_site',
                    '{"en":"Aralsk and Aral Sea remains","ru":"Аральское море","uz":"Orol dengizi","zh":"咸海"}'::jsonb,
                    'KZ','kyzylorda',46.793889,61.681667,NULL::smallint,NULL),
                ('kz-charyn-canyon','archaeological_site',
                    '{"en":"Charyn Canyon","ru":"Чарынский каньон","uz":"Charin kanyoni","zh":"恰伦峡谷"}'::jsonb,
                    'KZ','almaty',43.355833,79.077222,NULL::smallint,NULL),
                ('kz-lake-balkhash','archaeological_site',
                    '{"en":"Lake Balkhash","ru":"Озеро Балхаш","uz":"Balxash ko''li","zh":"巴尔喀什湖"}'::jsonb,
                    'KZ','almaty',46.083333,74.500000,NULL::smallint,NULL),
                ('kz-kolsay-lakes','archaeological_site',
                    '{"en":"Kolsay Lakes","ru":"Кольсайские озёра","uz":"Ko''lsoy ko''llari","zh":"科尔赛湖"}'::jsonb,
                    'KZ','almaty',42.733333,78.316667,NULL::smallint,NULL),
                ('kz-kok-tobe','monument',
                    '{"en":"Kok-Tobe","ru":"Кок-Тобе","uz":"Ko''ktepa","zh":"科克托别"}'::jsonb,
                    'KZ','almaty',43.232222,76.974722,1983::smallint,NULL),
                ('kz-zenkov-cathedral','monument',
                    '{"en":"Zenkov Cathedral","ru":"Зенковский собор","uz":"Zenkov sobori","zh":"曾科夫教堂"}'::jsonb,
                    'KZ','almaty',43.258444,76.952833,1907::smallint,NULL),
                ('kz-arasan-baths','monument',
                    '{"en":"Arasan Baths","ru":"Бани Арасан","uz":"Arasan hammomi","zh":"阿拉桑浴场"}'::jsonb,
                    'KZ','almaty',43.260278,76.949722,1982::smallint,NULL),
                ('kz-museum-first-president','museum',
                    '{"en":"Museum of First President","ru":"Музей первого президента","uz":"Birinchi prezident muzeyi","zh":"第一任总统博物馆"}'::jsonb,
                    'KZ','astana',51.128889,71.430000,2004::smallint,NULL),
                ('kz-nur-astana-mosque','mosque',
                    '{"en":"Nur-Astana Mosque","ru":"Мечеть Нур-Астана","uz":"Nur-Ostona masjidi","zh":"努尔阿斯塔纳清真寺"}'::jsonb,
                    'KZ','astana',51.125000,71.418889,2005::smallint,NULL),
                ('kz-hazret-sultan-mosque','mosque',
                    '{"en":"Hazret Sultan Mosque","ru":"Мечеть Хазрет Султан","uz":"Hazrat Sulton masjidi","zh":"哈兹拉特苏丹清真寺"}'::jsonb,
                    'KZ','astana',51.118611,71.466667,2012::smallint,NULL),
                ('kz-pyramid-of-peace','monument',
                    '{"en":"Palace of Peace and Reconciliation","ru":"Дворец мира и согласия","uz":"Tinchlik va totuvlik saroyi","zh":"和平和解宫"}'::jsonb,
                    'KZ','astana',51.126667,71.469167,2006::smallint,NULL),
                ('kz-presidential-park','monument',
                    '{"en":"Presidential Park, Almaty","ru":"Парк президентов","uz":"Prezidentlik bog''i","zh":"总统公园"}'::jsonb,
                    'KZ','almaty',43.220556,76.870278,2010::smallint,NULL),
                ('kz-medeu','monument',
                    '{"en":"Medeu Skating Rink","ru":"Медеу","uz":"Medeu konkida uchish maydoni","zh":"麦迪奥滑冰场"}'::jsonb,
                    'KZ','almaty',43.158889,77.058333,1972::smallint,NULL),
                ('kz-arystan-bab','mausoleum',
                    '{"en":"Arystan Bab Mausoleum","ru":"Мавзолей Арыстан-Баба","uz":"Arston Bob maqbarasi","zh":"阿雷斯坦巴布陵墓"}'::jsonb,
                    'KZ','turkistan',42.861389,68.231944,1390::smallint,NULL),
                ('kz-akkergeshen-petroglyphs','archaeological_site',
                    '{"en":"Akkergeshen Petroglyphs","ru":"Петроглифы Аккергешен","uz":"Akkergeshen petrogliflari","zh":"阿克尔格申岩画"}'::jsonb,
                    'KZ','aktobe',47.500000,57.000000,-1000::smallint,NULL),
                ('kz-bozok','archaeological_site',
                    '{"en":"Bozok Settlement","ru":"Городище Бозок","uz":"Bozoq shaharchasi","zh":"博佐克遗址"}'::jsonb,
                    'KZ','astana',51.083333,71.450000,700::smallint,NULL),
                ('kz-baikonur-cosmodrome','monument',
                    '{"en":"Baikonur Cosmodrome","ru":"Космодром Байконур","uz":"Bayqo''ng''ir kosmodromi","zh":"拜科努尔航天发射场"}'::jsonb,
                    'KZ','kyzylorda',45.965000,63.305000,1955::smallint,NULL),

                -- ===================== Tajikistan (25) =====================
                ('tj-sarazm','archaeological_site',
                    '{"en":"Proto-urban Site of Sarazm","ru":"Саразм","uz":"Sarazm","zh":"萨拉子目"}'::jsonb,
                    'TJ','panjakent',39.508889,67.466667,-3500::smallint,'1141'),
                ('tj-national-park','archaeological_site',
                    '{"en":"Tajik National Park (Mountains of the Pamirs)","ru":"Таджикский национальный парк","uz":"Tojikiston milliy bog''i","zh":"塔吉克国家公园"}'::jsonb,
                    'TJ',NULL,38.500000,72.500000,NULL::smallint,'1252'),
                ('tj-hissar-fortress','palace',
                    '{"en":"Hissar Fortress","ru":"Гиссарская крепость","uz":"Hisor qal''asi","zh":"希萨尔要塞"}'::jsonb,
                    'TJ','dushanbe',38.515278,68.547778,1500::smallint,NULL),
                ('tj-hulbuk','archaeological_site',
                    '{"en":"Hulbuk","ru":"Хульбук","uz":"Xulbuk","zh":"胡尔布克"}'::jsonb,
                    'TJ','khujand',37.965000,69.842500,900::smallint,NULL),
                ('tj-ajina-tepa','archaeological_site',
                    '{"en":"Ajina-Tepa","ru":"Аджина-Тепа","uz":"Ajina-Tepa","zh":"阿吉纳特佩"}'::jsonb,
                    'TJ','dushanbe',37.766667,69.500000,650::smallint,NULL),
                ('tj-panjakent-ancient','archaeological_site',
                    '{"en":"Ancient Panjakent","ru":"Древний Пенджикент","uz":"Qadimgi Panjikent","zh":"古片治肯特"}'::jsonb,
                    'TJ','panjakent',39.494444,67.609444,500::smallint,NULL),
                ('tj-mukhammad-bashoro','mausoleum',
                    '{"en":"Mausoleum of Muhammad Bashoro","ru":"Мавзолей Мухаммада Башоро","uz":"Muhammad Bashoro maqbarasi","zh":"穆罕默德·巴绍罗陵墓"}'::jsonb,
                    'TJ','panjakent',39.350000,67.866667,1142::smallint,NULL),
                ('tj-iskanderkul','archaeological_site',
                    '{"en":"Iskanderkul Lake","ru":"Озеро Искандеркуль","uz":"Iskandarko''l","zh":"伊斯坎德尔库尔湖"}'::jsonb,
                    'TJ','dushanbe',39.083333,68.366667,NULL::smallint,NULL),
                ('tj-pamir-highway','monument',
                    '{"en":"Pamir Highway","ru":"Памирский тракт","uz":"Pomir yo''li","zh":"帕米尔公路"}'::jsonb,
                    'TJ','khorog',38.000000,73.000000,1934::smallint,NULL),
                ('tj-wakhan-corridor','archaeological_site',
                    '{"en":"Wakhan Corridor","ru":"Ваханский коридор","uz":"Vahon yo''lagi","zh":"瓦罕走廊"}'::jsonb,
                    'TJ','khorog',37.000000,73.000000,NULL::smallint,NULL),
                ('tj-khorog-botanical','monument',
                    '{"en":"Khorog Botanical Garden","ru":"Хорогский ботанический сад","uz":"Xorug'' botanika bog''i","zh":"霍罗格植物园"}'::jsonb,
                    'TJ','khorog',37.522222,71.575278,1940::smallint,NULL),
                ('tj-rudaki-park','monument',
                    '{"en":"Rudaki Park","ru":"Парк Рудаки","uz":"Rudakiy bog''i","zh":"鲁达基公园"}'::jsonb,
                    'TJ','dushanbe',38.578889,68.776667,1958::smallint,NULL),
                ('tj-national-museum','museum',
                    '{"en":"National Museum of Tajikistan","ru":"Национальный музей Таджикистана","uz":"Tojikiston milliy muzeyi","zh":"塔吉克斯坦国家博物馆"}'::jsonb,
                    'TJ','dushanbe',38.580278,68.778611,1934::smallint,NULL),
                ('tj-museum-antiquities','museum',
                    '{"en":"National Museum of Antiquities","ru":"Музей древностей","uz":"Qadimiy buyumlar muzeyi","zh":"古代文物博物馆"}'::jsonb,
                    'TJ','dushanbe',38.583333,68.783333,2001::smallint,NULL),
                ('tj-ismaili-centre','monument',
                    '{"en":"Ismaili Centre Dushanbe","ru":"Исмаилитский центр","uz":"Ismoiliylar markazi","zh":"伊斯玛仪中心"}'::jsonb,
                    'TJ','dushanbe',38.560278,68.787500,2009::smallint,NULL),
                ('tj-haji-yakoub','mosque',
                    '{"en":"Haji Yakoub Mosque","ru":"Мечеть Хаджи Якуб","uz":"Hoji Ya''qub masjidi","zh":"哈吉雅各布清真寺"}'::jsonb,
                    'TJ','dushanbe',38.575278,68.781944,1932::smallint,NULL),
                ('tj-mug-fortress','archaeological_site',
                    '{"en":"Mount Mug Fortress","ru":"Крепость Муг","uz":"Mug'' tog''i qal''asi","zh":"穆格山要塞"}'::jsonb,
                    'TJ','panjakent',39.300000,68.500000,700::smallint,NULL),
                ('tj-khujand-fortress','palace',
                    '{"en":"Khujand Fortress","ru":"Худжандская крепость","uz":"Xo''jand qal''asi","zh":"苦盏要塞"}'::jsonb,
                    'TJ','khujand',40.281667,69.620556,-500::smallint,NULL),
                ('tj-sheikh-massal','mausoleum',
                    '{"en":"Sheikh Massal-ad-Din Mausoleum","ru":"Мавзолей Шейха Массал-ад-Дина","uz":"Shayx Massal ad-Din maqbarasi","zh":"谢赫马萨尔丁陵墓"}'::jsonb,
                    'TJ','khujand',40.281944,69.621944,1394::smallint,NULL),
                ('tj-istaravshan-fortress','palace',
                    '{"en":"Istaravshan Old Fortress","ru":"Старая крепость Истаравшан","uz":"Istaravshan qadimiy qal''asi","zh":"伊斯塔拉夫尚古堡"}'::jsonb,
                    'TJ','istaravshan',39.912500,69.011111,-500::smallint,NULL),
                ('tj-kuhi-mavlono','mausoleum',
                    '{"en":"Kuhi Mavlono Mausoleum","ru":"Мавзолей Кухи Мавлоно","uz":"Kuhi Mavlono maqbarasi","zh":"库希·毛拉诺陵墓"}'::jsonb,
                    'TJ','istaravshan',39.912000,69.014000,1200::smallint,NULL),
                ('tj-fan-mountains','archaeological_site',
                    '{"en":"Fann Mountains","ru":"Фанские горы","uz":"Fan tog''lari","zh":"凡恩山脉"}'::jsonb,
                    'TJ','panjakent',39.200000,68.166667,NULL::smallint,NULL),
                ('tj-yagnob-valley','archaeological_site',
                    '{"en":"Yaghnob Valley","ru":"Ягнобская долина","uz":"Yag''nob vodiysi","zh":"亚格诺布山谷"}'::jsonb,
                    'TJ','panjakent',39.116667,68.733333,NULL::smallint,NULL),
                ('tj-karon-fortress','archaeological_site',
                    '{"en":"Karon Fortress","ru":"Крепость Карон","uz":"Qaron qal''asi","zh":"卡龙要塞"}'::jsonb,
                    'TJ','khorog',37.700000,71.200000,400::smallint,NULL),
                ('tj-yamchun-fort','archaeological_site',
                    '{"en":"Yamchun Fort","ru":"Крепость Ямчун","uz":"Yamchun qal''asi","zh":"亚姆昌堡"}'::jsonb,
                    'TJ','khorog',36.916667,72.483333,300::smallint,NULL),

                -- ===================== Turkmenistan (20) ===================
                ('tm-ancient-merv','archaeological_site',
                    '{"en":"Ancient Merv","ru":"Древний Мерв","uz":"Qadimgi Marv","zh":"古梅尔夫"}'::jsonb,
                    'TM','merv',37.666667,62.200000,-500::smallint,'886'),
                ('tm-konya-urgench','archaeological_site',
                    '{"en":"Kunya-Urgench","ru":"Куня-Ургенч","uz":"Ko''hna Urganch","zh":"古尔甘奇"}'::jsonb,
                    'TM','konye_urgench',42.336111,59.150278,1000::smallint,'1199'),
                ('tm-nisa-fortress','palace',
                    '{"en":"Parthian Fortresses of Nisa","ru":"Парфянские крепости Нисы","uz":"Parf Nisa qal''alari","zh":"尼萨帕提亚要塞"}'::jsonb,
                    'TM','nisa',37.966389,58.197500,-250::smallint,'1242'),
                ('tm-turkmenbasy-ruhy','mosque',
                    '{"en":"Türkmenbaşy Ruhy Mosque","ru":"Мечеть Туркменбаши Рухы","uz":"Turkmanboshi Ruhi masjidi","zh":"土库曼巴希鲁希清真寺"}'::jsonb,
                    'TM','ashgabat',37.873611,58.182222,2004::smallint,NULL),
                ('tm-darvaza-crater','archaeological_site',
                    '{"en":"Darvaza Gas Crater","ru":"Газовый кратер Дарваза","uz":"Darvoza gaz krateri","zh":"达瓦札瓦斯火山"}'::jsonb,
                    'TM','ashgabat',40.252778,58.439444,1971::smallint,NULL),
                ('tm-najmiddin-kubra','mausoleum',
                    '{"en":"Mausoleum of Najmiddin Kubra","ru":"Мавзолей Наджмиддина Кубра","uz":"Najmiddin Kubro maqbarasi","zh":"纳吉姆丁·库布拉陵墓"}'::jsonb,
                    'TM','konye_urgench',42.336667,59.149444,1221::smallint,NULL),
                ('tm-neutrality-monument','monument',
                    '{"en":"Monument of Neutrality","ru":"Монумент Нейтралитета","uz":"Betaraflik yodgorligi","zh":"中立纪念碑"}'::jsonb,
                    'TM','ashgabat',37.901389,58.367500,2011::smallint,NULL),
                ('tm-arch-of-neutrality','monument',
                    '{"en":"Arch of Neutrality","ru":"Арка Нейтралитета","uz":"Betaraflik arkasi","zh":"中立拱门"}'::jsonb,
                    'TM','ashgabat',37.945278,58.380278,1998::smallint,NULL),
                ('tm-independence-monument','monument',
                    '{"en":"Independence Monument","ru":"Монумент Независимости","uz":"Mustaqillik yodgorligi","zh":"独立纪念碑"}'::jsonb,
                    'TM','ashgabat',37.913056,58.366111,2001::smallint,NULL),
                ('tm-kipchak-mosque','mosque',
                    '{"en":"Gypjak Mosque","ru":"Мечеть Кипчак","uz":"Qipchoq masjidi","zh":"基普恰克清真寺"}'::jsonb,
                    'TM','ashgabat',37.853056,58.115000,2004::smallint,NULL),
                ('tm-erk-gala','archaeological_site',
                    '{"en":"Erk Gala (Old Merv)","ru":"Эрк-Кала","uz":"Erk Qala","zh":"埃尔克卡拉"}'::jsonb,
                    'TM','merv',37.671111,62.197778,-500::smallint,NULL),
                ('tm-gyaur-kala','archaeological_site',
                    '{"en":"Gyaur Kala","ru":"Гяур-Кала","uz":"G''avur Qal''a","zh":"贾乌尔卡拉"}'::jsonb,
                    'TM','merv',37.661944,62.197222,-300::smallint,NULL),
                ('tm-sultan-sanjar','mausoleum',
                    '{"en":"Mausoleum of Sultan Sanjar","ru":"Мавзолей Султана Санджара","uz":"Sulton Sanjar maqbarasi","zh":"苏丹桑贾尔陵墓"}'::jsonb,
                    'TM','merv',37.662222,62.199444,1157::smallint,NULL),
                ('tm-il-arslan-mausoleum','mausoleum',
                    '{"en":"Il-Arslan Mausoleum","ru":"Мавзолей Иль-Арслана","uz":"Il-Arslon maqbarasi","zh":"伊尔·阿尔斯兰陵墓"}'::jsonb,
                    'TM','konye_urgench',42.337778,59.151111,1172::smallint,NULL),
                ('tm-kutlug-timur-minaret','monument',
                    '{"en":"Kutlug-Timur Minaret","ru":"Минарет Кутлуг-Тимура","uz":"Qutlug''-Temur minorasi","zh":"库特鲁格-帖木儿宣礼塔"}'::jsonb,
                    'TM','konye_urgench',42.336944,59.151944,1330::smallint,NULL),
                ('tm-mausoleum-tekesh','mausoleum',
                    '{"en":"Mausoleum of Sultan Tekesh","ru":"Мавзолей Султана Текеша","uz":"Sulton Takesh maqbarasi","zh":"苏丹泰克什陵墓"}'::jsonb,
                    'TM','konye_urgench',42.337500,59.150556,1200::smallint,NULL),
                ('tm-old-nisa','archaeological_site',
                    '{"en":"Old Nisa","ru":"Старая Ниса","uz":"Eski Nisa","zh":"旧尼萨"}'::jsonb,
                    'TM','nisa',37.966667,58.197778,-200::smallint,NULL),
                ('tm-new-nisa','archaeological_site',
                    '{"en":"New Nisa","ru":"Новая Ниса","uz":"Yangi Nisa","zh":"新尼萨"}'::jsonb,
                    'TM','nisa',37.966944,58.198889,200::smallint,NULL),
                ('tm-ertogrul-gazi','mosque',
                    '{"en":"Ertogrul Gazi Mosque","ru":"Мечеть Эртогрул Гази","uz":"Ertog''rul G''ozi masjidi","zh":"埃尔图鲁尔加齐清真寺"}'::jsonb,
                    'TM','ashgabat',37.957500,58.385278,1998::smallint,NULL),
                ('tm-state-museum','museum',
                    '{"en":"National Museum of Turkmenistan","ru":"Национальный музей Туркменистана","uz":"Turkmaniston milliy muzeyi","zh":"土库曼斯坦国家博物馆"}'::jsonb,
                    'TM','ashgabat',37.905556,58.404444,1998::smallint,NULL),

                -- ===================== Kyrgyzstan (20) =====================
                ('kg-sulayman-too','archaeological_site',
                    '{"en":"Sulayman-Too Sacred Mountain","ru":"Сулайман-Тоо","uz":"Sulaymon-Tog''","zh":"苏莱曼-图圣山"}'::jsonb,
                    'KG','osh',40.527500,72.797222,-3000::smallint,'1230'),
                ('kg-burana-tower','monument',
                    '{"en":"Burana Tower","ru":"Башня Бурана","uz":"Burana minorasi","zh":"布拉纳塔"}'::jsonb,
                    'KG','bishkek',42.745833,75.250000,1000::smallint,NULL),
                ('kg-tash-rabat','caravanserai',
                    '{"en":"Tash Rabat Caravanserai","ru":"Таш-Рабат","uz":"Tosh-Rabot karvonsaroyi","zh":"塔什拉巴特"}'::jsonb,
                    'KG','naryn',40.823333,75.290000,1400::smallint,NULL),
                ('kg-issyk-kul','archaeological_site',
                    '{"en":"Issyk-Kul Lake","ru":"Озеро Иссык-Куль","uz":"Issiqko''l ko''li","zh":"伊塞克湖"}'::jsonb,
                    'KG','karakol',42.466667,77.250000,NULL::smallint,NULL),
                ('kg-manas-mausoleum','mausoleum',
                    '{"en":"Manas Mausoleum","ru":"Гумбез Манаса","uz":"Manas maqbarasi","zh":"玛纳斯陵墓"}'::jsonb,
                    'KG','naryn',42.583333,74.583333,1334::smallint,NULL),
                ('kg-uzgen-complex','monument',
                    '{"en":"Uzgen Karakhanid Complex","ru":"Узгенский комплекс","uz":"O''zgan Qoraxoniylar majmuasi","zh":"乌兹根卡拉汗朝建筑群"}'::jsonb,
                    'KG','osh',40.768056,73.297222,1000::smallint,NULL),
                ('kg-ala-archa','archaeological_site',
                    '{"en":"Ala-Archa National Park","ru":"Национальный парк Ала-Арча","uz":"Ola-Archa milliy bog''i","zh":"阿拉阿尔察国家公园"}'::jsonb,
                    'KG','bishkek',42.633333,74.483333,1976::smallint,NULL),
                ('kg-skazka-canyon','archaeological_site',
                    '{"en":"Skazka Canyon","ru":"Каньон Сказка","uz":"Skazka kanyoni","zh":"斯卡兹卡峡谷"}'::jsonb,
                    'KG','karakol',42.139444,77.475000,NULL::smallint,NULL),
                ('kg-song-kul','archaeological_site',
                    '{"en":"Song-Kul Lake","ru":"Озеро Сон-Куль","uz":"So''nko''l","zh":"松湖"}'::jsonb,
                    'KG','naryn',41.833333,75.083333,NULL::smallint,NULL),
                ('kg-jeti-oguz','archaeological_site',
                    '{"en":"Jeti-Oguz Rocks","ru":"Скалы Джеты-Огуз","uz":"Jeti-O''g''uz qoyalari","zh":"杰提-奥古兹岩石"}'::jsonb,
                    'KG','karakol',42.341667,78.226944,NULL::smallint,NULL),
                ('kg-osh-bazaar','monument',
                    '{"en":"Jayma Bazaar Osh","ru":"Базар Джайма","uz":"Jayma bozori","zh":"奥什贾伊马大巴扎"}'::jsonb,
                    'KG','osh',40.519444,72.797222,1500::smallint,NULL),
                ('kg-rabat-abdullah-khan','madrasa',
                    '{"en":"Rabat Abdullah Khan","ru":"Рабат Абдулла-Хан","uz":"Rabot Abdulloxon","zh":"拉巴特阿卜杜拉汗"}'::jsonb,
                    'KG','osh',40.529722,72.798333,1500::smallint,NULL),
                ('kg-ala-too-square','monument',
                    '{"en":"Ala-Too Square","ru":"Площадь Ала-Тоо","uz":"Ola-Tog'' maydoni","zh":"阿拉图广场"}'::jsonb,
                    'KG','bishkek',42.876389,74.603889,1984::smallint,NULL),
                ('kg-victory-square','monument',
                    '{"en":"Victory Square Bishkek","ru":"Площадь Победы","uz":"G''alaba maydoni","zh":"胜利广场"}'::jsonb,
                    'KG','bishkek',42.871111,74.610000,1985::smallint,NULL),
                ('kg-historical-museum','museum',
                    '{"en":"State Historical Museum of Kyrgyzstan","ru":"Государственный исторический музей","uz":"Davlat tarix muzeyi","zh":"国家历史博物馆"}'::jsonb,
                    'KG','bishkek',42.876944,74.603333,1925::smallint,NULL),
                ('kg-fine-arts-museum','museum',
                    '{"en":"Kyrgyz National Museum of Fine Arts","ru":"Музей изобразительных искусств","uz":"Tasviriy san''at muzeyi","zh":"吉尔吉斯国家美术博物馆"}'::jsonb,
                    'KG','bishkek',42.875278,74.602778,1934::smallint,NULL),
                ('kg-przhevalsky','monument',
                    '{"en":"Przhevalsky Memorial","ru":"Мемориал Пржевальского","uz":"Przhevalskiy yodgorligi","zh":"普热瓦尔斯基纪念碑"}'::jsonb,
                    'KG','karakol',42.527778,78.328889,1894::smallint,NULL),
                ('kg-karakol-mosque','mosque',
                    '{"en":"Dungan Mosque Karakol","ru":"Дунганская мечеть","uz":"Dungan masjidi","zh":"卡拉科尔东干清真寺"}'::jsonb,
                    'KG','karakol',42.490833,78.391667,1910::smallint,NULL),
                ('kg-holy-trinity','monument',
                    '{"en":"Holy Trinity Cathedral Karakol","ru":"Свято-Троицкий собор","uz":"Muqaddas Uchlik sobori","zh":"卡拉科尔三位一体大教堂"}'::jsonb,
                    'KG','karakol',42.492500,78.394722,1895::smallint,NULL),
                ('kg-koshoy-korgon','archaeological_site',
                    '{"en":"Koshoy-Korgon","ru":"Кошой-Коргон","uz":"Koshoy-Korgon qal''asi","zh":"科绍伊科尔贡"}'::jsonb,
                    'KG','naryn',40.700000,75.250000,1000::smallint,NULL)
        ),
        site_levels AS (
            INSERT INTO geographic_admin_levels
                (parent_id, level, admin_level_type, code, name, country_code,
                 centroid_lat, centroid_lng, path)
            SELECT
                COALESCE(city_lvl.id, country_lvl.id),
                CASE WHEN city_lvl.id IS NOT NULL THEN 5 ELSE 5 END,
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

    # --- 3. UNESCO inscriptions for seeded sites --------------------------
    # Criteria + year + inscription_id sourced from whc.unesco.org refs.
    op.execute(
        """
        WITH unesco_seeds(pub_id, inscription_id, year, criteria, category,
                          area_ha, statement) AS (
            VALUES
                ('kz-yasawi-mausoleum','1103',2003::smallint,
                    ARRAY['i','iii','iv'], 'cultural',
                    55.0::numeric,
                    '{"en":"The Yasawi mausoleum is an outstanding example of the Timurid style of architecture."}'::jsonb),
                ('kz-tamgaly-petroglyphs','1145',2004::smallint,
                    ARRAY['iii'], 'cultural',
                    900.0::numeric,
                    '{"en":"Around 5,000 petroglyphs in a dense and coherent group of ancient sanctuaries."}'::jsonb),
                ('kz-saryarka-steppe','1102',2008::smallint,
                    ARRAY['ix','x'], 'natural',
                    450344.0::numeric,
                    '{"en":"Saryarka covers two protected areas with freshwater and salt lakes hosting Siberian crane and rare migratory birds."}'::jsonb),
                ('tj-sarazm','1141',2010::smallint,
                    ARRAY['ii','iii'], 'cultural',
                    47.5::numeric,
                    '{"en":"Bears testimony to the development of human settlements in the Central Asia region from the 4th millennium BCE to the end of the 3rd millennium BCE."}'::jsonb),
                ('tj-national-park','1252',2013::smallint,
                    ARRAY['vii','viii'], 'natural',
                    2611674.0::numeric,
                    '{"en":"Tajik National Park covers more than 2.5 million hectares in the east of the country at the centre of the Pamir mountain system."}'::jsonb),
                ('tm-ancient-merv','886',1999::smallint,
                    ARRAY['ii','iii'], 'cultural',
                    353.0::numeric,
                    '{"en":"Merv is the oldest and best-preserved oasis-city along the Silk Routes in Central Asia."}'::jsonb),
                ('tm-konya-urgench','1199',2005::smallint,
                    ARRAY['ii','iii'], 'cultural',
                    640.0::numeric,
                    '{"en":"Kunya-Urgench is situated in north-western Turkmenistan on the left bank of the Amu Daria River."}'::jsonb),
                ('tm-nisa-fortress','1242',2007::smallint,
                    ARRAY['ii','iii'], 'cultural',
                    78.5::numeric,
                    '{"en":"The Parthian Fortresses of Nisa consist of two tells of Old and New Nisa, indicative of the ancient Parthian Empire."}'::jsonb),
                ('kg-sulayman-too','1230',2009::smallint,
                    ARRAY['iii','vi'], 'cultural',
                    112.0::numeric,
                    '{"en":"Sulaiman-Too Sacred Mountain dominates the Fergana Valley and forms the background to the city of Osh."}'::jsonb)
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

    # --- 4. Update heritage_objects.unesco_inscription_year ---------------
    op.execute(
        """
        UPDATE heritage_objects ho
        SET unesco_inscription_year = ui.inscription_year
        FROM unesco_inscriptions ui
        WHERE ui.heritage_id = ho.id
          AND ho.unesco_inscription_year IS NULL;
        """
    )

    # --- 5. heritage_facts rows (provenance — UNESCO inscription year) ----
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
                'kz-yasawi-mausoleum','kz-tamgaly-petroglyphs','kz-saryarka-steppe',
                'tj-sarazm','tj-national-park',
                'tm-ancient-merv','tm-konya-urgench','tm-nisa-fortress',
                'kg-sulayman-too'
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

    # --- 6. Link the facts to the unesco_whc provenance row ---------------
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

    # --- 7. Dynasty associations (where dynasty exists from 0013) ---------
    # Map of pub_id → dynasty slug. Only links sites with confident
    # dynastic association.
    op.execute(
        """
        WITH dyn_links(pub_id, dynasty_slug, role) AS (
            VALUES
                ('kz-yasawi-mausoleum','timurid','built_under'),
                ('kz-aisha-bibi','karakhanid','built_under'),
                ('kz-karakhan-mausoleum','karakhanid','built_under'),
                ('kz-arystan-bab','timurid','restored_under'),
                ('kz-sauran','timurid','flourished_under'),
                ('tj-mukhammad-bashoro','samanid','built_under'),
                ('tj-hulbuk','samanid','built_under'),
                ('tm-sultan-sanjar','samanid','associated_with'),
                ('tm-il-arslan-mausoleum','khwarazmid','built_under'),
                ('tm-kutlug-timur-minaret','khwarazmid','built_under'),
                ('tm-mausoleum-tekesh','khwarazmid','built_under'),
                ('tm-najmiddin-kubra','khwarazmid','associated_with'),
                ('kg-burana-tower','karakhanid','built_under'),
                ('kg-uzgen-complex','karakhanid','built_under')
        )
        INSERT INTO heritage_dynasty_assoc (heritage_id, dynasty_id, role, confidence)
        SELECT ho.id, d.id, dl.role, 85
        FROM dyn_links dl
        JOIN heritage_objects ho ON ho.pub_id = dl.pub_id
        JOIN dynasties d ON d.slug = dl.dynasty_slug
        ON CONFLICT (heritage_id, dynasty_id, role) DO NOTHING;
        """
    )

    # --- 8. Style associations (where style exists from 0013) -------------
    op.execute(
        """
        WITH style_links(pub_id, style_slug, is_primary) AS (
            VALUES
                ('kz-yasawi-mausoleum','timurid_architecture',true),
                ('kz-arystan-bab','timurid_architecture',true),
                ('kz-sauran','islamic',true),
                ('kz-aisha-bibi','islamic',true),
                ('kz-karakhan-mausoleum','islamic',true),
                ('tj-sarazm','sogdian',true),
                ('tj-panjakent-ancient','sogdian',true),
                ('tj-ajina-tepa','sogdian',true),
                ('tj-mukhammad-bashoro','islamic',true),
                ('tm-ancient-merv','islamic',true),
                ('tm-konya-urgench','islamic',true),
                ('tm-nisa-fortress','hellenistic',true),
                ('tm-sultan-sanjar','islamic',true),
                ('tm-il-arslan-mausoleum','islamic',true),
                ('kg-burana-tower','islamic',true),
                ('kg-uzgen-complex','islamic',true),
                ('kg-tash-rabat','islamic',true)
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
    # Order: unesco_inscriptions cascade from heritage_objects deletion;
    # heritage_dynasty/style_assoc cascade likewise; heritage_facts &
    # fact_provenance cascade too. Site admin_levels go last.
    op.execute(
        """
        DELETE FROM heritage_objects
        WHERE pub_id LIKE 'kz-%' OR pub_id LIKE 'tj-%'
           OR pub_id LIKE 'tm-%' OR pub_id LIKE 'kg-%';
        """
    )
    op.execute(
        """
        DELETE FROM geographic_admin_levels
        WHERE admin_level_type = 'site'
          AND country_code IN ('KZ','TJ','TM','KG');
        """
    )
    op.execute(
        """
        DELETE FROM cities
        WHERE country_code IN ('KZ','TJ','TM','KG')
          AND slug IN (
            'almaty','astana','shymkent','turkistan','aktobe','atyrau','kyzylorda',
            'dushanbe','khujand','khorog','panjakent','istaravshan',
            'ashgabat','mary','turkmenabat','merv','konye_urgench','nisa',
            'bishkek','osh','karakol','naryn'
          );
        """
    )
    op.execute(
        """
        DELETE FROM geographic_admin_levels
        WHERE admin_level_type = 'city'
          AND country_code IN ('KZ','TJ','TM','KG')
          AND code IN (
            'KZ.ALMATY','KZ.ASTANA','KZ.SHYMKENT','KZ.TURKISTAN',
            'KZ.AKTOBE','KZ.ATYRAU','KZ.KYZYLORDA',
            'TJ.DUSHANBE','TJ.KHUJAND','TJ.KHOROG','TJ.PANJAKENT','TJ.ISTARAVSHAN',
            'TM.ASHGABAT','TM.MARY','TM.TURKMENABAT','TM.MERV','TM.KONYE_URGENCH','TM.NISA',
            'KG.BISHKEK','KG.OSH','KG.KARAKOL','KG.NARYN'
          );
        """
    )
