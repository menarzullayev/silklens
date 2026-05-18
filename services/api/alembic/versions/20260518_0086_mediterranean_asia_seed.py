"""Mediterranean + Asia heritage seed — IT/GR/EG/MA/JP/KR/TH

FAZA 7 — Global expansion. Wave-8 Agent 2.

Seeds real heritage data for 7 countries:
- IT: 20 entries + 6 cities (Rome, Florence, Venice, Milan, Naples, Pompeii)
- GR: 15 entries + 4 cities (Athens, Thessaloniki, Delphi, Olympia)
- EG: 20 entries + 5 cities (Cairo, Luxor, Aswan, Alexandria, Giza)
- MA: 15 entries + 6 cities (Marrakech, Fez, Casablanca, Rabat, Meknes, Essaouira)
- JP: 20 entries + 5 cities (Tokyo, Kyoto, Nara, Hiroshima, Osaka)
- KR: 10 entries + 4 cities (Seoul, Gyeongju, Suwon, Andong)
- TH: 10 entries + 4 cities (Bangkok, Chiang Mai, Sukhothai, Ayutthaya)
- UNESCO inscriptions: ≥ 30 across all 7 countries
- Currencies: EUR, JPY, KRW, THB, EGP, MAD (ON CONFLICT DO NOTHING)
- Pricing zone: europe_apac covering [IT,GR,EG,MA,JP,KR,TH], PPP 0.80, USD
- Prices: premium_monthly $3.99, premium_yearly $39.99

Idempotent via ON CONFLICT DO NOTHING on pub_id / city slug / inscription_id.

Revision ID: 0086_mediterranean_asia_seed
Revises: 0081_central_asia_currencies
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0086_mediterranean_asia_seed"
down_revision: str | Sequence[str] | None = "0081_central_asia_currencies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- 1. Cities + geographic_admin_levels ----------------------------------
    op.execute(
        """
        WITH city_seeds(country_code, slug, name, lat, lng, population, is_capital, is_silk_road) AS (
            VALUES
                -- Italy
                ('IT','rome',
                    '{"en":"Rome","it":"Roma","fr":"Rome","zh":"罗马","ar":"روما"}'::jsonb,
                    41.902782, 12.496366, 2800000, true, false),
                ('IT','florence',
                    '{"en":"Florence","it":"Firenze","fr":"Florence","zh":"佛罗伦萨","ar":"فلورنسا"}'::jsonb,
                    43.769560, 11.255814, 380000, false, false),
                ('IT','venice',
                    '{"en":"Venice","it":"Venezia","fr":"Venise","zh":"威尼斯","ar":"البندقية"}'::jsonb,
                    45.440847, 12.315515, 255000, false, false),
                ('IT','milan',
                    '{"en":"Milan","it":"Milano","fr":"Milan","zh":"米兰","ar":"ميلانو"}'::jsonb,
                    45.464664, 9.188540, 1400000, false, false),
                ('IT','naples',
                    '{"en":"Naples","it":"Napoli","fr":"Naples","zh":"那不勒斯","ar":"نابولي"}'::jsonb,
                    40.851775, 14.268508, 970000, false, false),
                ('IT','pompeii',
                    '{"en":"Pompeii","it":"Pompei","fr":"Pompéi","zh":"庞贝","ar":"بومبي"}'::jsonb,
                    40.750000, 14.489444, 25000, false, false),

                -- Greece
                ('GR','athens',
                    '{"en":"Athens","el":"Αθήνα","fr":"Athènes","zh":"雅典","ar":"أثينا"}'::jsonb,
                    37.983810, 23.727539, 3150000, true, false),
                ('GR','thessaloniki',
                    '{"en":"Thessaloniki","el":"Θεσσαλονίκη","fr":"Thessalonique","zh":"塞萨洛尼基","ar":"ثيسالونيكي"}'::jsonb,
                    40.629269, 22.947412, 810000, false, false),
                ('GR','delphi',
                    '{"en":"Delphi","el":"Δελφοί","fr":"Delphes","zh":"德尔菲","ar":"دلفي"}'::jsonb,
                    38.482220, 22.501111, 15000, false, false),
                ('GR','olympia',
                    '{"en":"Olympia","el":"Ολυμπία","fr":"Olympie","zh":"奥林匹亚","ar":"أولمبيا"}'::jsonb,
                    37.638611, 21.630000, 14000, false, false),

                -- Egypt
                ('EG','cairo',
                    '{"en":"Cairo","ar":"القاهرة","fr":"Le Caire","zh":"开罗","tr":"Kahire"}'::jsonb,
                    30.044420, 31.235712, 20000000, true, false),
                ('EG','luxor',
                    '{"en":"Luxor","ar":"الأقصر","fr":"Louxor","zh":"卢克索","tr":"Luksor"}'::jsonb,
                    25.687243, 32.639637, 510000, false, false),
                ('EG','aswan',
                    '{"en":"Aswan","ar":"أسوان","fr":"Assouan","zh":"阿斯旺","tr":"Asvan"}'::jsonb,
                    24.088938, 32.899830, 290000, false, false),
                ('EG','alexandria',
                    '{"en":"Alexandria","ar":"الإسكندرية","fr":"Alexandrie","zh":"亚历山大港","tr":"İskenderiye"}'::jsonb,
                    31.200092, 29.918739, 5200000, false, false),
                ('EG','giza',
                    '{"en":"Giza","ar":"الجيزة","fr":"Gizeh","zh":"吉萨","tr":"Gize"}'::jsonb,
                    30.013056, 31.213333, 3630000, false, false),

                -- Morocco
                ('MA','marrakech',
                    '{"en":"Marrakech","ar":"مراكش","fr":"Marrakech","zh":"马拉喀什","es":"Marrakech"}'::jsonb,
                    31.628674, -7.992047, 928000, false, false),
                ('MA','fez',
                    '{"en":"Fez","ar":"فاس","fr":"Fès","zh":"非斯","es":"Fez"}'::jsonb,
                    34.033333, -5.000000, 1200000, false, false),
                ('MA','casablanca',
                    '{"en":"Casablanca","ar":"الدار البيضاء","fr":"Casablanca","zh":"卡萨布兰卡","es":"Casablanca"}'::jsonb,
                    33.589886, -7.603869, 3752000, false, false),
                ('MA','rabat',
                    '{"en":"Rabat","ar":"الرباط","fr":"Rabat","zh":"拉巴特","es":"Rabat"}'::jsonb,
                    34.020882, -6.841650, 577000, true, false),
                ('MA','meknes',
                    '{"en":"Meknes","ar":"مكناس","fr":"Meknès","zh":"梅克内斯","es":"Mequínez"}'::jsonb,
                    33.895278, -5.554722, 632000, false, false),
                ('MA','essaouira',
                    '{"en":"Essaouira","ar":"الصويرة","fr":"Essaouira","zh":"索维拉","es":"Mogador"}'::jsonb,
                    31.508590, -9.759337, 77000, false, false),

                -- Japan
                ('JP','tokyo',
                    '{"en":"Tokyo","ja":"東京","zh":"东京","ko":"도쿄","fr":"Tokyo"}'::jsonb,
                    35.689487, 139.691706, 13960000, true, false),
                ('JP','kyoto',
                    '{"en":"Kyoto","ja":"京都","zh":"京都","ko":"교토","fr":"Kyoto"}'::jsonb,
                    35.011636, 135.768029, 1470000, false, false),
                ('JP','nara',
                    '{"en":"Nara","ja":"奈良","zh":"奈良","ko":"나라","fr":"Nara"}'::jsonb,
                    34.685334, 135.804994, 361000, false, false),
                ('JP','hiroshima',
                    '{"en":"Hiroshima","ja":"広島","zh":"广岛","ko":"히로시마","fr":"Hiroshima"}'::jsonb,
                    34.385203, 132.455293, 1200000, false, false),
                ('JP','osaka',
                    '{"en":"Osaka","ja":"大阪","zh":"大阪","ko":"오사카","fr":"Osaka"}'::jsonb,
                    34.693738, 135.502165, 2750000, false, false),

                -- South Korea
                ('KR','seoul',
                    '{"en":"Seoul","ko":"서울","zh":"首尔","ja":"ソウル","fr":"Séoul"}'::jsonb,
                    37.566536, 126.977966, 9700000, true, false),
                ('KR','gyeongju',
                    '{"en":"Gyeongju","ko":"경주","zh":"庆州","ja":"慶州","fr":"Gyeongju"}'::jsonb,
                    35.856406, 129.224683, 252000, false, false),
                ('KR','suwon',
                    '{"en":"Suwon","ko":"수원","zh":"水原","ja":"水原","fr":"Suwon"}'::jsonb,
                    37.263573, 127.028601, 1180000, false, false),
                ('KR','andong',
                    '{"en":"Andong","ko":"안동","zh":"安东","ja":"安東","fr":"Andong"}'::jsonb,
                    36.568534, 128.729571, 157000, false, false),

                -- Thailand
                ('TH','bangkok',
                    '{"en":"Bangkok","th":"กรุงเทพมหานคร","zh":"曼谷","fr":"Bangkok","ko":"방콕"}'::jsonb,
                    13.756331, 100.501765, 10500000, true, false),
                ('TH','chiang_mai',
                    '{"en":"Chiang Mai","th":"เชียงใหม่","zh":"清迈","fr":"Chiang Maï","ko":"치앙마이"}'::jsonb,
                    18.787747, 98.993128, 1030000, false, false),
                ('TH','sukhothai',
                    '{"en":"Sukhothai","th":"สุโขทัย","zh":"素可泰","fr":"Sukhothaï","ko":"수코타이"}'::jsonb,
                    17.012000, 99.826000, 37000, false, false),
                ('TH','ayutthaya',
                    '{"en":"Ayutthaya","th":"พระนครศรีอยุธยา","zh":"大城","fr":"Ayutthaya","ko":"아유타야"}'::jsonb,
                    14.369444, 100.586944, 53000, false, false)
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

    # --- 2. Heritage objects --------------------------------------------------
    op.execute(
        """
        WITH default_tenant AS (
            SELECT id FROM tenants WHERE slug = 'default' LIMIT 1
        ),
        heritage_seeds(pub_id, kind_slug, name, country_code, city_slug,
                       lat, lng, period_start_year, unesco_id) AS (
            VALUES
                -- ===================== Italy (20) ==========================
                ('it-colosseum','monument',
                    '{"en":"Colosseum","it":"Colosseo","fr":"Colisée","zh":"罗马斗兽场","ar":"المدرج الروماني"}'::jsonb,
                    'IT','rome',41.890169,12.492269,80::smallint,'91'),
                ('it-roman-forum','archaeological_site',
                    '{"en":"Roman Forum and Palatine Hill","it":"Foro Romano e Palatino","fr":"Forum Romain","zh":"罗马广场","ar":"المنتدى الروماني"}'::jsonb,
                    'IT','rome',41.892500,12.485278,509::smallint,'91'),
                ('it-vatican-city','monument',
                    '{"en":"Vatican City","it":"Città del Vaticano","fr":"Cité du Vatican","zh":"梵蒂冈城","ar":"مدينة الفاتيكان"}'::jsonb,
                    'IT','rome',41.902916,12.453389,1929::smallint,'286'),
                ('it-florence-historic','monument',
                    '{"en":"Historic Centre of Florence","it":"Centro Storico di Firenze","fr":"Centre historique de Florence","zh":"佛罗伦萨历史中心","ar":"وسط فلورنسا التاريخي"}'::jsonb,
                    'IT','florence',43.768056,11.256111,1100::smallint,'174'),
                ('it-venice-lagoon','monument',
                    '{"en":"Venice and its Lagoon","it":"Venezia e la sua Laguna","fr":"Venise et sa Lagune","zh":"威尼斯及其潟湖","ar":"البندقية وبحيرتها"}'::jsonb,
                    'IT','venice',45.440847,12.315515,697::smallint,'394'),
                ('it-rome-historic','monument',
                    '{"en":"Historic Centre of Rome","it":"Centro Storico di Roma","fr":"Centre historique de Rome","zh":"罗马历史中心","ar":"مركز روما التاريخي"}'::jsonb,
                    'IT','rome',41.896000,12.482100,753::smallint,'91'),
                ('it-pompeii-site','archaeological_site',
                    '{"en":"Pompeii, Herculaneum and Torre Annunziata","it":"Pompei, Ercolano e Torre Annunziata","fr":"Pompéi, Herculanum","zh":"庞贝、赫库兰尼姆和托雷安农齐亚塔","ar":"بومبي وهيركولانيوم"}'::jsonb,
                    'IT','pompeii',40.750556,14.491944,-79::smallint,'829'),
                ('it-cinque-terre','monument',
                    '{"en":"Cinque Terre","it":"Cinque Terre","fr":"Cinque Terre","zh":"五渔村","ar":"تشينكوي تيري"}'::jsonb,
                    'IT','milan',44.129444,9.740000,1100::smallint,'826'),
                ('it-pisa-cathedral','monument',
                    '{"en":"Piazza del Duomo, Pisa","it":"Piazza del Duomo di Pisa","fr":"Cathédrale de Pise","zh":"比萨大教堂广场","ar":"ساحة دومو بيزا"}'::jsonb,
                    'IT','florence',43.722952,10.396597,1063::smallint,'395'),
                ('it-ravenna-mosaics','monument',
                    '{"en":"Early Christian Monuments of Ravenna","it":"Monumenti paleocristiani di Ravenna","fr":"Monuments paléochrétiens de Ravenne","zh":"拉文纳早期基督教遗迹","ar":"معالم المسيحية المبكرة في رافينا"}'::jsonb,
                    'IT','milan',44.416667,12.200000,402::smallint,'788'),
                ('it-amalfi-coast','monument',
                    '{"en":"Amalfi Coast","it":"Costiera Amalfitana","fr":"Côte Amalfitaine","zh":"阿马尔菲海岸","ar":"ساحل أمالفي"}'::jsonb,
                    'IT','naples',40.633333,14.600000,900::smallint,'830'),
                ('it-sistine-chapel','monument',
                    '{"en":"Sistine Chapel","it":"Cappella Sistina","fr":"Chapelle Sixtine","zh":"西斯廷礼拜堂","ar":"الكنيسة السيكستينية"}'::jsonb,
                    'IT','rome',41.902500,12.454167,1481::smallint,'286'),
                ('it-trevi-fountain','monument',
                    '{"en":"Trevi Fountain","it":"Fontana di Trevi","fr":"Fontaine de Trevi","zh":"特莱维喷泉","ar":"نافورة تريفي"}'::jsonb,
                    'IT','rome',41.900833,12.483333,1762::smallint,NULL),
                ('it-spanish-steps','monument',
                    '{"en":"Spanish Steps","it":"Scalinata di Trinità dei Monti","fr":"Escalier de la Trinité-des-Monts","zh":"西班牙阶梯","ar":"السلالم الإسبانية"}'::jsonb,
                    'IT','rome',41.905972,12.482460,1725::smallint,NULL),
                ('it-pantheon','monument',
                    '{"en":"Pantheon","it":"Pantheon","fr":"Panthéon","zh":"万神庙","ar":"البانثيون"}'::jsonb,
                    'IT','rome',41.898611,12.476944,125::smallint,'91'),
                ('it-uffizi-gallery','museum',
                    '{"en":"Uffizi Gallery","it":"Galleria degli Uffizi","fr":"Galerie des Offices","zh":"乌菲兹美术馆","ar":"غاليريا ديليه أوفيتشي"}'::jsonb,
                    'IT','florence',43.768611,11.255278,1581::smallint,NULL),
                ('it-grand-canal-venice','monument',
                    '{"en":"Grand Canal Venice","it":"Canal Grande","fr":"Grand Canal de Venise","zh":"大运河","ar":"القناة الكبرى"}'::jsonb,
                    'IT','venice',45.440556,12.326111,697::smallint,'394'),
                ('it-leaning-tower-pisa','monument',
                    '{"en":"Leaning Tower of Pisa","it":"Torre di Pisa","fr":"Tour de Pise","zh":"比萨斜塔","ar":"برج بيزا المائل"}'::jsonb,
                    'IT','florence',43.722952,10.396597,1173::smallint,'395'),
                ('it-herculaneum','archaeological_site',
                    '{"en":"Herculaneum","it":"Ercolano","fr":"Herculanum","zh":"赫库兰尼姆","ar":"هيركولانيوم"}'::jsonb,
                    'IT','naples',40.805833,14.348333,-79::smallint,'829'),
                ('it-last-supper-milan','monument',
                    '{"en":"The Last Supper — Santa Maria delle Grazie","it":"Cenacolo Vinciano","fr":"Cène de Léonard de Vinci","zh":"最后的晚餐","ar":"العشاء الأخير"}'::jsonb,
                    'IT','milan',45.466000,9.170556,1495::smallint,'93'),

                -- ===================== Greece (15) ==========================
                ('gr-acropolis','monument',
                    '{"en":"Acropolis of Athens","el":"Ακρόπολη Αθηνών","fr":"Acropole d''Athènes","zh":"雅典卫城","ar":"أكروبول أثينا"}'::jsonb,
                    'GR','athens',37.971389,23.726389,-447::smallint,'404'),
                ('gr-parthenon','monument',
                    '{"en":"Parthenon","el":"Παρθενώνας","fr":"Parthénon","zh":"帕特农神庙","ar":"البارثينون"}'::jsonb,
                    'GR','athens',37.971389,23.726389,-447::smallint,'404'),
                ('gr-delphi-site','archaeological_site',
                    '{"en":"Archaeological Site of Delphi","el":"Αρχαιολογικός χώρος Δελφών","fr":"Site archéologique de Delphes","zh":"德尔菲考古遗址","ar":"موقع دلفي الأثري"}'::jsonb,
                    'GR','delphi',38.482222,22.501111,-800::smallint,'393'),
                ('gr-ancient-olympia','archaeological_site',
                    '{"en":"Archaeological Site of Olympia","el":"Αρχαία Ολυμπία","fr":"Site archéologique d''Olympie","zh":"奥林匹亚考古遗址","ar":"موقع أولمبيا الأثري"}'::jsonb,
                    'GR','olympia',37.638611,21.630000,-776::smallint,'517'),
                ('gr-meteora','monument',
                    '{"en":"Meteora","el":"Μετέωρα","fr":"Météores","zh":"迈泰奥拉","ar":"ميتيورا"}'::jsonb,
                    'GR','thessaloniki',39.721944,21.627778,900::smallint,'455'),
                ('gr-vergina','archaeological_site',
                    '{"en":"Archaeological Site of Aigai (Vergina)","el":"Αιγές (Βεργίνα)","fr":"Vergina","zh":"埃盖 (维吉纳)","ar":"أيجي (فيرجينا)"}'::jsonb,
                    'GR','thessaloniki',40.483056,22.318056,-700::smallint,'794'),
                ('gr-rhodes-medieval','monument',
                    '{"en":"Medieval City of Rhodes","el":"Μεσαιωνική πόλη Ρόδου","fr":"Vieille ville de Rhodes","zh":"罗德岛中世纪城市","ar":"مدينة رودس القروسطية"}'::jsonb,
                    'GR','athens',36.444167,28.222778,1309::smallint,'395'),
                ('gr-mycenae-tiryns','archaeological_site',
                    '{"en":"Mycenae and Tiryns","el":"Μυκήνες και Τίρυνθα","fr":"Mycènes et Tirynthe","zh":"迈锡尼和梯林斯","ar":"ميسيني وتيرينز"}'::jsonb,
                    'GR','athens',37.730278,22.756389,-1600::smallint,'941'),
                ('gr-delos','archaeological_site',
                    '{"en":"Delos","el":"Δήλος","fr":"Délos","zh":"提洛斯","ar":"ديلوس"}'::jsonb,
                    'GR','athens',37.397500,25.269444,-900::smallint,'530'),
                ('gr-epidaurus','archaeological_site',
                    '{"en":"Sanctuary of Asklepios at Epidaurus","el":"Ιερό του Ασκληπιού στην Επίδαυρο","fr":"Sanctuaire d''Asclépios à Épidaure","zh":"埃皮道鲁斯阿斯克勒庇俄斯圣殿","ar":"معبد أسكلبيوس في إبيداوروس"}'::jsonb,
                    'GR','athens',37.596389,23.078333,-370::smallint,'491'),
                ('gr-thessaloniki-paleochristian','monument',
                    '{"en":"Paleochristian and Byzantine Monuments of Thessalonika","el":"Παλαιοχριστιανικά και Βυζαντινά μνημεία Θεσσαλονίκης","fr":"Monuments paléochrétiens et byzantins de Thessalonique","zh":"塞萨洛尼基早期基督教和拜占庭遗迹","ar":"المعالم المسيحية البيزنطية في ثيسالونيكي"}'::jsonb,
                    'GR','thessaloniki',40.632778,22.943611,306::smallint,'456'),
                ('gr-olympia-zeus','monument',
                    '{"en":"Temple of Zeus, Olympia","el":"Ναός του Διός Ολυμπίας","fr":"Temple de Zeus d''Olympie","zh":"奥林匹亚宙斯神庙","ar":"معبد زيوس الأوليمبي"}'::jsonb,
                    'GR','olympia',37.638611,21.630000,-472::smallint,'517'),
                ('gr-erechtheion','monument',
                    '{"en":"Erechtheion","el":"Ερέχθειο","fr":"Érechthéion","zh":"厄瑞克忒翁神庙","ar":"إريختيون"}'::jsonb,
                    'GR','athens',37.971944,23.726111,-421::smallint,'404'),
                ('gr-agora-athens','archaeological_site',
                    '{"en":"Ancient Agora of Athens","el":"Αρχαία Αγορά Αθηνών","fr":"Agora antique d''Athènes","zh":"雅典古集市","ar":"أغورا أثينا القديمة"}'::jsonb,
                    'GR','athens',37.975278,23.721944,-600::smallint,NULL),
                ('gr-national-museum','museum',
                    '{"en":"National Archaeological Museum of Athens","el":"Εθνικό Αρχαιολογικό Μουσείο","fr":"Musée national archéologique d''Athènes","zh":"雅典国家考古博物馆","ar":"المتحف الأثري الوطني بأثينا"}'::jsonb,
                    'GR','athens',37.989444,23.731389,1829::smallint,NULL),

                -- ===================== Egypt (20) ==========================
                ('eg-giza-pyramids','archaeological_site',
                    '{"en":"Memphis and its Necropolis — Giza Pyramids","ar":"ممفيس ومقابرها — أهرامات الجيزة","fr":"Memphis et sa nécropole","zh":"孟菲斯及其墓地群","tr":"Memphis ve Nekropolü"}'::jsonb,
                    'EG','giza',29.979167,31.134167,-2560::smallint,'86'),
                ('eg-great-pyramid','archaeological_site',
                    '{"en":"Great Pyramid of Giza","ar":"هرم خوفو الأكبر","fr":"Grande pyramide de Gizeh","zh":"吉萨大金字塔","tr":"Büyük Giza Piramidi"}'::jsonb,
                    'EG','giza',29.979167,31.134167,-2560::smallint,'86'),
                ('eg-sphinx','archaeological_site',
                    '{"en":"Great Sphinx of Giza","ar":"أبو الهول","fr":"Grand Sphinx de Gizeh","zh":"吉萨大狮身人面像","tr":"Büyük Sfenks"}'::jsonb,
                    'EG','giza',29.975278,31.137500,-2500::smallint,'86'),
                ('eg-ancient-thebes','archaeological_site',
                    '{"en":"Ancient Thebes with its Necropolis","ar":"طيبة القديمة وجبانتها","fr":"Thèbes antique","zh":"古底比斯","tr":"Antik Teb"}'::jsonb,
                    'EG','luxor',25.740278,32.601944,-1550::smallint,'87'),
                ('eg-karnak-temple','monument',
                    '{"en":"Karnak Temple Complex","ar":"معبد الكرنك","fr":"Complexe de Karnak","zh":"卡纳克神庙","tr":"Karnak Tapınağı"}'::jsonb,
                    'EG','luxor',25.718611,32.656111,-2055::smallint,'87'),
                ('eg-luxor-temple','monument',
                    '{"en":"Luxor Temple","ar":"معبد الأقصر","fr":"Temple de Louxor","zh":"卢克索神庙","tr":"Luksor Tapınağı"}'::jsonb,
                    'EG','luxor',25.699722,32.638889,-1400::smallint,'87'),
                ('eg-valley-of-kings','archaeological_site',
                    '{"en":"Valley of the Kings","ar":"وادي الملوك","fr":"Vallée des Rois","zh":"帝王谷","tr":"Krallar Vadisi"}'::jsonb,
                    'EG','luxor',25.740556,32.601389,-1550::smallint,'87'),
                ('eg-abu-simbel','monument',
                    '{"en":"Abu Simbel","ar":"أبو سمبل","fr":"Abou Simbel","zh":"阿布辛贝神庙","tr":"Ebu Simbel"}'::jsonb,
                    'EG','aswan',22.336389,31.625556,-1264::smallint,'88'),
                ('eg-islamic-cairo','monument',
                    '{"en":"Historic Cairo (Islamic Cairo)","ar":"القاهرة التاريخية","fr":"Le Caire historique","zh":"历史悠久的开罗","tr":"Tarihi Kahire"}'::jsonb,
                    'EG','cairo',30.046667,31.261667,969::smallint,'89'),
                ('eg-saint-catherines','monument',
                    '{"en":"Saint Catherine''s Monastery Sinai","ar":"دير سانت كاترين","fr":"Monastère Sainte-Catherine","zh":"圣凯瑟琳修道院","tr":"Aziz Katerina Manastırı"}'::jsonb,
                    'EG','aswan',28.555556,33.975556,565::smallint,'954'),
                ('eg-wadi-al-hitan','archaeological_site',
                    '{"en":"Wadi Al-Hitan (Whale Valley)","ar":"وادي الحيتان","fr":"Wadi Al-Hitan","zh":"鲸鱼谷","tr":"Balina Vadisi"}'::jsonb,
                    'EG','cairo',29.270833,30.041667,NULL::smallint,'1186'),
                ('eg-abu-mena','monument',
                    '{"en":"Abu Mena Early Christian Site","ar":"أبو مينا","fr":"Abou Ména","zh":"阿布美纳","tr":"Abu Mena"}'::jsonb,
                    'EG','alexandria',30.837500,29.663889,296::smallint,'90'),
                ('eg-philae-temple','monument',
                    '{"en":"Philae Temple","ar":"معبد فيلة","fr":"Temple de Philae","zh":"菲莱神庙","tr":"File Tapınağı"}'::jsonb,
                    'EG','aswan',24.023611,32.884167,-370::smallint,'88'),
                ('eg-colossi-memnon','monument',
                    '{"en":"Colossi of Memnon","ar":"تمثالا ممنون","fr":"Colosses de Memnon","zh":"门农巨像","tr":"Memnon Kolosları"}'::jsonb,
                    'EG','luxor',25.720833,32.611944,-1350::smallint,'87'),
                ('eg-hatshepsut-temple','monument',
                    '{"en":"Mortuary Temple of Hatshepsut","ar":"معبد حتشبسوت","fr":"Temple de Hatchepsout","zh":"哈特谢普苏特女王神庙","tr":"Hatşepsut Tapınağı"}'::jsonb,
                    'EG','luxor',25.737778,32.605556,-1479::smallint,'87'),
                ('eg-museum-cairo','museum',
                    '{"en":"Egyptian Museum Cairo","ar":"المتحف المصري","fr":"Musée égyptien du Caire","zh":"开罗埃及博物馆","tr":"Mısır Müzesi"}'::jsonb,
                    'EG','cairo',30.047778,31.233611,1902::smallint,NULL),
                ('eg-saqqara','archaeological_site',
                    '{"en":"Saqqara Necropolis","ar":"سقارة","fr":"Nécropole de Saqqarah","zh":"萨卡拉","tr":"Sakkara Nekropolü"}'::jsonb,
                    'EG','giza',29.871389,31.216111,-2650::smallint,'86'),
                ('eg-abydos','archaeological_site',
                    '{"en":"Abydos","ar":"أبيدوس","fr":"Abydos","zh":"阿拜多斯","tr":"Abidos"}'::jsonb,
                    'EG','luxor',26.183333,31.916667,-3200::smallint,NULL),
                ('eg-alexandria-library','monument',
                    '{"en":"Bibliotheca Alexandrina","ar":"مكتبة الإسكندرية","fr":"Bibliothèque d''Alexandrie","zh":"亚历山大图书馆","tr":"İskenderiye Kütüphanesi"}'::jsonb,
                    'EG','alexandria',31.208889,29.909444,2002::smallint,NULL),
                ('eg-aswan-high-dam','monument',
                    '{"en":"Aswan High Dam","ar":"السد العالي","fr":"Haut barrage d''Assouan","zh":"阿斯旺大坝","tr":"Asvan Yüksek Barajı"}'::jsonb,
                    'EG','aswan',23.970833,32.877778,1970::smallint,NULL),

                -- ===================== Morocco (15) =========================
                ('ma-medina-fez','monument',
                    '{"en":"Medina of Fez","ar":"المدينة القديمة لفاس","fr":"Médina de Fès","zh":"非斯老城","es":"Medina de Fez"}'::jsonb,
                    'MA','fez',34.065000,-4.972778,859::smallint,'170'),
                ('ma-ait-benhaddou','archaeological_site',
                    '{"en":"Ksar of Ait-Ben-Haddou","ar":"قصر آيت بن حدو","fr":"Ksar d''Aït-Ben-Haddou","zh":"艾本哈杜筑垒城","es":"Ksar de Ait Benhaddou"}'::jsonb,
                    'MA','marrakech',31.047222,-7.130000,700::smallint,'444'),
                ('ma-historic-meknes','monument',
                    '{"en":"Historic City of Meknes","ar":"المدينة التاريخية لمكناس","fr":"Ville historique de Meknès","zh":"梅克内斯历史城","es":"Ciudad histórica de Mequínez"}'::jsonb,
                    'MA','meknes',33.896111,-5.556111,1672::smallint,'793'),
                ('ma-medina-marrakech','monument',
                    '{"en":"Medina of Marrakech","ar":"مدينة مراكش","fr":"Médina de Marrakech","zh":"马拉喀什老城","es":"Medina de Marrakech"}'::jsonb,
                    'MA','marrakech',31.630556,-7.988333,1070::smallint,'331'),
                ('ma-volubilis','archaeological_site',
                    '{"en":"Archaeological Site of Volubilis","ar":"وليلي","fr":"Site archéologique de Volubilis","zh":"沃吕比利斯考古遗址","es":"Volúbilis"}'::jsonb,
                    'MA','meknes',34.073056,-5.555556,-25::smallint,'836'),
                ('ma-medina-essaouira','monument',
                    '{"en":"Medina of Essaouira (Mogador)","ar":"مدينة الصويرة","fr":"Médina d''Essaouira (Mogador)","zh":"索维拉古城","es":"Medina de Essaouira"}'::jsonb,
                    'MA','essaouira',31.511111,-9.770278,1765::smallint,'753'),
                ('ma-rabat-capital','monument',
                    '{"en":"Rabat Modern Capital and Historic City","ar":"الرباط","fr":"Rabat, capitale moderne et ville historique","zh":"拉巴特现代首都与历史名城","es":"Rabat, capital moderna"}'::jsonb,
                    'MA','rabat',34.020833,-6.841667,1150::smallint,'1401'),
                ('ma-koutoubia-mosque','mosque',
                    '{"en":"Koutoubia Mosque","ar":"مسجد الكتبية","fr":"Mosquée Koutoubia","zh":"库图比亚清真寺","es":"Mezquita de la Koutoubia"}'::jsonb,
                    'MA','marrakech',31.624167,-8.000000,1158::smallint,NULL),
                ('ma-hassan-ii-mosque','mosque',
                    '{"en":"Hassan II Mosque","ar":"مسجد الحسن الثاني","fr":"Mosquée Hassan II","zh":"哈桑二世清真寺","es":"Mezquita Hassan II"}'::jsonb,
                    'MA','casablanca',33.608056,-7.632500,1993::smallint,NULL),
                ('ma-bahia-palace','palace',
                    '{"en":"Bahia Palace","ar":"قصر الباهية","fr":"Palais de la Bahia","zh":"巴伊亚宫","es":"Palacio de la Bahía"}'::jsonb,
                    'MA','marrakech',31.621389,-7.986111,1900::smallint,NULL),
                ('ma-bou-inania-madrasa','madrasa',
                    '{"en":"Bou Inania Madrasa","ar":"المدرسة البوعنانية","fr":"Medersa Bou Inania","zh":"布伊纳尼亚神学院","es":"Madraza Bou Inania"}'::jsonb,
                    'MA','fez',34.066111,-4.973889,1350::smallint,NULL),
                ('ma-jemaa-el-fna','monument',
                    '{"en":"Jemaa el-Fna Square","ar":"ساحة جامع الفناء","fr":"Place Jemaa el-Fna","zh":"杰马·艾勒·夫纳广场","es":"Plaza Jemaa el-Fna"}'::jsonb,
                    'MA','marrakech',31.625833,-7.989167,1100::smallint,NULL),
                ('ma-mausoleum-mohammed-v','mausoleum',
                    '{"en":"Mausoleum of Mohammed V","ar":"ضريح محمد الخامس","fr":"Mausolée de Mohammed V","zh":"穆罕默德五世陵墓","es":"Mausoleo de Mohámed V"}'::jsonb,
                    'MA','rabat',34.022500,-6.833056,1971::smallint,NULL),
                ('ma-chefchaouen-medina','monument',
                    '{"en":"Chefchaouen Blue Medina","ar":"شفشاون","fr":"Chefchaouen","zh":"舍夫沙万蓝色旧城","es":"Chefchauen"}'::jsonb,
                    'MA','fez',35.171111,-5.264167,1471::smallint,NULL),
                ('ma-hassan-tower','monument',
                    '{"en":"Hassan Tower","ar":"صومعة حسان","fr":"Tour Hassan","zh":"哈桑塔","es":"Torre Hassan"}'::jsonb,
                    'MA','rabat',34.024167,-6.820278,1199::smallint,'1401'),

                -- ===================== Japan (20) ==========================
                ('jp-horyuji','monument',
                    '{"en":"Buddhist Monuments in the Horyu-ji Area","ja":"法隆寺地域の仏教建造物","fr":"Monuments bouddhiques de la région de Horyu-ji","zh":"法隆寺地区佛教建筑群","ko":"호류지 지역 불교 기념물"}'::jsonb,
                    'JP','nara',34.614444,135.734444,607::smallint,'660'),
                ('jp-himeji-castle','monument',
                    '{"en":"Himeji-jo Castle","ja":"姫路城","fr":"Château de Himeji","zh":"姬路城","ko":"히메지 성"}'::jsonb,
                    'JP','osaka',34.839167,134.693889,1333::smallint,'661'),
                ('jp-historic-kyoto','monument',
                    '{"en":"Historic Monuments of Ancient Kyoto","ja":"古都京都の文化財","fr":"Monuments historiques de l''ancienne Kyoto","zh":"古都京都的文化财","ko":"고도 교토의 문화재"}'::jsonb,
                    'JP','kyoto',35.017222,135.762222,794::smallint,'688'),
                ('jp-historic-nara','monument',
                    '{"en":"Historic Monuments of Ancient Nara","ja":"古都奈良の文化財","fr":"Monuments historiques de l''ancienne Nara","zh":"古都奈良的文化财","ko":"고도 나라의 문화재"}'::jsonb,
                    'JP','nara',34.681667,135.826667,710::smallint,'870'),
                ('jp-hiroshima-dome','monument',
                    '{"en":"Hiroshima Peace Memorial (Genbaku Dome)","ja":"広島平和記念碑（原爆ドーム）","fr":"Mémorial de la paix d''Hiroshima","zh":"广岛和平纪念公园","ko":"히로시마 평화기념관"}'::jsonb,
                    'JP','hiroshima',34.395278,132.453611,1945::smallint,'775'),
                ('jp-nikko','monument',
                    '{"en":"Shrines and Temples of Nikko","ja":"日光の社寺","fr":"Sanctuaires et temples de Nikko","zh":"日光的神社与寺庙","ko":"닛코의 신사와 사찰"}'::jsonb,
                    'JP','tokyo',36.758889,139.598889,1617::smallint,'913'),
                ('jp-itsukushima','monument',
                    '{"en":"Itsukushima Shinto Shrine","ja":"嚴島神社","fr":"Sanctuaire shinto d''Itsukushima","zh":"严岛神社","ko":"이쓰쿠시마 신사"}'::jsonb,
                    'JP','hiroshima',34.296111,132.319722,593::smallint,'776'),
                ('jp-mount-fuji','monument',
                    '{"en":"Fujisan, Sacred Place and Source of Artistic Inspiration","ja":"富士山－信仰の対象と芸術の源泉","fr":"Fujisan, lieu sacré","zh":"富士山","ko":"후지산"}'::jsonb,
                    'JP','tokyo',35.360556,138.727778,781::smallint,'1418'),
                ('jp-yoshino-kii','monument',
                    '{"en":"Sacred Sites and Pilgrimage Routes in the Kii Mountain Range","ja":"紀伊山地の霊場と参詣道","fr":"Sites sacrés et routes de pèlerinage dans les monts Kii","zh":"纪伊山地灵场与参拜道","ko":"기이산지의 영지와 참배 길"}'::jsonb,
                    'JP','osaka',34.241389,136.053889,1004::smallint,'1142'),
                ('jp-gion-district','monument',
                    '{"en":"Gion District Kyoto","ja":"祇園","fr":"Quartier de Gion à Kyoto","zh":"京都祗园区","ko":"기온 지구"}'::jsonb,
                    'JP','kyoto',35.003611,135.775556,794::smallint,'688'),
                ('jp-kinkakuji','monument',
                    '{"en":"Kinkaku-ji (Golden Pavilion)","ja":"金閣寺","fr":"Kinkaku-ji (Pavillon d''or)","zh":"金阁寺","ko":"킨카쿠지 (금각사)"}'::jsonb,
                    'JP','kyoto',35.039444,135.729167,1397::smallint,'688'),
                ('jp-todai-ji','monument',
                    '{"en":"Todai-ji Temple","ja":"東大寺","fr":"Temple Todai-ji","zh":"东大寺","ko":"도다이지"}'::jsonb,
                    'JP','nara',34.688889,135.839444,728::smallint,'870'),
                ('jp-fushimi-inari','monument',
                    '{"en":"Fushimi Inari Shrine","ja":"伏見稲荷大社","fr":"Sanctuaire Fushimi Inari","zh":"伏见稻荷大社","ko":"후시미이나리 신사"}'::jsonb,
                    'JP','kyoto',34.967222,135.772500,-711::smallint,NULL),
                ('jp-senso-ji','monument',
                    '{"en":"Senso-ji Temple","ja":"浅草寺","fr":"Temple Senso-ji","zh":"浅草寺","ko":"센소지"}'::jsonb,
                    'JP','tokyo',35.714722,139.796389,628::smallint,NULL),
                ('jp-shirakawa-go','monument',
                    '{"en":"Shirakawa-go Historic Villages","ja":"白川郷","fr":"Villages historiques de Shirakawa-go","zh":"白川乡历史村落","ko":"시라카와고 역사 마을"}'::jsonb,
                    'JP','tokyo',36.256667,136.906111,1776::smallint,'734'),
                ('jp-osaka-castle','monument',
                    '{"en":"Osaka Castle","ja":"大阪城","fr":"Château d''Osaka","zh":"大阪城","ko":"오사카성"}'::jsonb,
                    'JP','osaka',34.687500,135.526111,1583::smallint,NULL),
                ('jp-tsukiji-market','monument',
                    '{"en":"Tsukiji Outer Market","ja":"築地市場","fr":"Marché de Tsukiji","zh":"筑地市场","ko":"쓰키지 시장"}'::jsonb,
                    'JP','tokyo',35.665556,139.770556,1935::smallint,NULL),
                ('jp-bamboo-grove-arashiyama','monument',
                    '{"en":"Arashiyama Bamboo Grove","ja":"嵐山竹林","fr":"Forêt de bambous d''Arashiyama","zh":"岚山竹林","ko":"아라시야마 대나무 숲"}'::jsonb,
                    'JP','kyoto',35.016944,135.671111,800::smallint,NULL),
                ('jp-hiroshima-peace-park','monument',
                    '{"en":"Hiroshima Peace Memorial Park","ja":"広島平和記念公園","fr":"Parc commémoratif de la paix d''Hiroshima","zh":"广岛和平纪念公园","ko":"히로시마 평화 기념 공원"}'::jsonb,
                    'JP','hiroshima',34.394444,132.452500,1954::smallint,'775'),
                ('jp-nara-deer-park','monument',
                    '{"en":"Nara Deer Park and Kasuga-Taisha","ja":"奈良公園と春日大社","fr":"Parc de Nara et Kasuga-Taisha","zh":"奈良鹿苑和春日大社","ko":"나라 사슴 공원과 가스가 신사"}'::jsonb,
                    'JP','nara',34.681667,135.843056,768::smallint,'870'),

                -- ===================== South Korea (10) ====================
                ('kr-haeinsa','monument',
                    '{"en":"Haeinsa Temple Tripitaka Koreana","ko":"해인사 장경판전","fr":"Temple Haeinsa - Tripitaka Koreana","zh":"海印寺大藏经板殿","ja":"海印寺藏経板殿"}'::jsonb,
                    'KR','andong',35.800000,128.105278,802::smallint,'737'),
                ('kr-jongmyo-shrine','monument',
                    '{"en":"Jongmyo Shrine","ko":"종묘","fr":"Sanctuaire Jongmyo","zh":"宗庙","ja":"宗廟"}'::jsonb,
                    'KR','seoul',37.574722,126.994444,1394::smallint,'738'),
                ('kr-changdeokgung','palace',
                    '{"en":"Changdeokgung Palace Complex","ko":"창덕궁","fr":"Palais Changdeokgung","zh":"昌德宫","ja":"昌徳宮"}'::jsonb,
                    'KR','seoul',37.579722,126.990833,1405::smallint,'816'),
                ('kr-hwaseong-fortress','monument',
                    '{"en":"Hwaseong Fortress","ko":"수원 화성","fr":"Forteresse Hwaseong","zh":"华城","ja":"水原城"}'::jsonb,
                    'KR','suwon',37.287778,127.013889,1796::smallint,'817'),
                ('kr-gyeongju-historic','archaeological_site',
                    '{"en":"Gyeongju Historic Areas","ko":"경주역사유적지구","fr":"Sites historiques de Gyeongju","zh":"庆州历史区域","ja":"慶州歴史地域"}'::jsonb,
                    'KR','gyeongju',35.856667,129.225000,-57::smallint,'976'),
                ('kr-gochang-dolmen','archaeological_site',
                    '{"en":"Gochang, Hwasun and Ganghwa Dolmen Sites","ko":"고창, 화순, 강화 고인돌 유적","fr":"Sites de dolmens de Gochang, Hwasun et Ganghwa","zh":"高敞、和顺、江华支石墓遗址","ja":"高敞, 和順, 江華の支石墓"}'::jsonb,
                    'KR','andong',35.500000,126.600000,-1000::smallint,'977'),
                ('kr-jeju-volcanic','archaeological_site',
                    '{"en":"Jeju Volcanic Island and Lava Tubes","ko":"제주 화산섬과 용암 동굴","fr":"Île volcanique de Jeju","zh":"济州火山岛和熔岩洞穴","ja":"済州火山島と溶岩洞窟"}'::jsonb,
                    'KR','andong',33.364722,126.529444,NULL::smallint,'1264'),
                ('kr-gyeongbokgung','palace',
                    '{"en":"Gyeongbokgung Palace","ko":"경복궁","fr":"Palais Gyeongbokgung","zh":"景福宫","ja":"景福宮"}'::jsonb,
                    'KR','seoul',37.579722,126.977222,1395::smallint,NULL),
                ('kr-bukchon-hanok','monument',
                    '{"en":"Bukchon Hanok Village","ko":"북촌 한옥마을","fr":"Village Hanok de Bukchon","zh":"北村韩屋村","ja":"北村韓屋村"}'::jsonb,
                    'KR','seoul',37.582778,126.983056,600::smallint,NULL),
                ('kr-namdaemun-market','monument',
                    '{"en":"Namdaemun Gate and Market","ko":"남대문 숭례문","fr":"Porte Namdaemun et marché","zh":"崇礼门及南大门市场","ja":"崇礼門と南大門市場"}'::jsonb,
                    'KR','seoul',37.559722,126.975556,1398::smallint,NULL),

                -- ===================== Thailand (10) =======================
                ('th-sukhothai-historic','monument',
                    '{"en":"Historic Town of Sukhothai and Associated Historic Towns","th":"เมืองประวัติศาสตร์สุโขทัย","fr":"Ancienne ville de Sukhothaï","zh":"素可泰历史城镇","ko":"수코타이 역사 마을"}'::jsonb,
                    'TH','sukhothai',17.012222,99.826111,1238::smallint,'574'),
                ('th-ayutthaya-historic','monument',
                    '{"en":"Historic City of Ayutthaya","th":"นครประวัติศาสตร์พระนครศรีอยุธยา","fr":"Ancienne capitale Ayutthaya","zh":"大城历史城","ko":"아유타야 역사 도시"}'::jsonb,
                    'TH','ayutthaya',14.369444,100.586944,1350::smallint,'576'),
                ('th-ban-chiang','archaeological_site',
                    '{"en":"Ban Chiang Archaeological Site","th":"แหล่งโบราณคดีบ้านเชียง","fr":"Site archéologique de Ban Chiang","zh":"班清考古遗址","ko":"반 치앙 고고학 유적지"}'::jsonb,
                    'TH','chiang_mai',17.613333,103.151944,-3600::smallint,'575'),
                ('th-thungyai-wildlife','archaeological_site',
                    '{"en":"Thungyai-Huai Kha Khaeng Wildlife Sanctuaries","th":"ทุ่งใหญ่-ห้วยขาแข้ง","fr":"Sanctuaires naturels de Thungyai-Huai Kha Khaeng","zh":"通艾-华卡肯野生动物保护区","ko":"퉁야이-화이 카 컹 야생동물 보호구역"}'::jsonb,
                    'TH','chiang_mai',15.666667,99.000000,NULL::smallint,'591'),
                ('th-grand-palace-bangkok','monument',
                    '{"en":"Grand Palace Bangkok","th":"พระบรมมหาราชวัง","fr":"Grand Palais de Bangkok","zh":"曼谷大皇宫","ko":"방콕 왕궁"}'::jsonb,
                    'TH','bangkok',13.750556,100.492222,1782::smallint,NULL),
                ('th-wat-pho','monument',
                    '{"en":"Wat Pho Temple","th":"วัดโพธิ์","fr":"Temple Wat Pho","zh":"卧佛寺","ko":"왓 포 사원"}'::jsonb,
                    'TH','bangkok',13.746944,100.492778,1788::smallint,NULL),
                ('th-wat-arun','monument',
                    '{"en":"Wat Arun — Temple of Dawn","th":"วัดอรุณราชวราราม","fr":"Wat Arun — Temple de l''Aurore","zh":"黎明寺","ko":"왓 아룬"}'::jsonb,
                    'TH','bangkok',13.743611,100.488889,1656::smallint,NULL),
                ('th-doi-suthep-temple','monument',
                    '{"en":"Doi Suthep Temple Chiang Mai","th":"วัดพระธาตุดอยสุเทพ","fr":"Temple Doi Suthep","zh":"双龙寺","ko":"도이수텝 사원"}'::jsonb,
                    'TH','chiang_mai',18.804722,98.921667,1383::smallint,NULL),
                ('th-phetchaburi-palaces','monument',
                    '{"en":"Phetchaburi Royal Palaces","th":"พระราชวังเพชรบุรี","fr":"Palais royaux de Phetchaburi","zh":"碧武里皇宫","ko":"펫차부리 왕궁"}'::jsonb,
                    'TH','bangkok',13.113611,99.942222,1859::smallint,NULL),
                ('th-chatuchak-market','monument',
                    '{"en":"Chatuchak Weekend Market","th":"ตลาดนัดจตุจักร","fr":"Marché de Chatuchak","zh":"乍都乍周末市场","ko":"짜뚜짝 주말 시장"}'::jsonb,
                    'TH','bangkok',13.799722,100.550000,1982::smallint,NULL)
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
            80
        FROM heritage_seeds hs
        CROSS JOIN default_tenant dt
        LEFT JOIN site_levels sl
            ON sl.code = upper(hs.country_code) || '.' || upper(replace(hs.pub_id, '-', '_'))
        ON CONFLICT (pub_id) DO NOTHING;
        """
    )

    # --- 3. Currencies --------------------------------------------------------
    op.execute(
        """
        INSERT INTO currencies (code, name, symbol, decimal_places)
        VALUES
            ('EUR', '{"en":"Euro","fr":"Euro","de":"Euro"}'::jsonb,                     '€',   2),
            ('JPY', '{"en":"Japanese Yen","ja":"日本円","zh":"日元"}'::jsonb,            '¥',   0),
            ('KRW', '{"en":"South Korean Won","ko":"대한민국 원","zh":"韩元"}'::jsonb,   '₩',   0),
            ('THB', '{"en":"Thai Baht","th":"บาทไทย","zh":"泰铢"}'::jsonb,              '฿',   2),
            ('EGP', '{"en":"Egyptian Pound","ar":"جنيه مصري","fr":"Livre égyptienne"}'::jsonb, 'E£', 2),
            ('MAD', '{"en":"Moroccan Dirham","ar":"درهم مغربي","fr":"Dirham marocain"}'::jsonb, 'د.م.', 2)
        ON CONFLICT (code) DO NOTHING;
        """
    )

    # --- 4. UNESCO inscriptions -----------------------------------------------
    op.execute(
        """
        WITH unesco_seeds(pub_id, inscription_id, year, criteria, category,
                          area_ha, statement) AS (
            VALUES
                -- Italy
                ('it-rome-historic','91',1980::smallint,
                    ARRAY['i','ii','iii','iv','vi'], 'cultural',
                    1431.0::numeric,
                    '{"en":"The Historic Centre of Rome, with its imperial forums, churches and palaces, is one of the world''s great treasures."}'::jsonb),
                ('it-vatican-city','286',1984::smallint,
                    ARRAY['i','ii','iv','vi'], 'cultural',
                    44.0::numeric,
                    '{"en":"Vatican City is the world''s smallest state and the heart of Roman Catholicism, containing outstanding examples of Renaissance and Baroque art."}'::jsonb),
                ('it-florence-historic','174',1982::smallint,
                    ARRAY['i','ii','iii','iv','vi'], 'cultural',
                    505.0::numeric,
                    '{"en":"Florence was a major centre of medieval European trade and finance and one of the most brilliant cities in Western art."}'::jsonb),
                ('it-venice-lagoon','394',1987::smallint,
                    ARRAY['i','ii','iii','iv','v','vi'], 'cultural',
                    70176.4::numeric,
                    '{"en":"Founded in the 5th century, Venice was a major maritime power during the Middle Ages and Renaissance."}'::jsonb),
                ('it-pompeii-site','829',1997::smallint,
                    ARRAY['iii','iv','v'], 'cultural',
                    96.5::numeric,
                    '{"en":"Pompeii and Herculaneum, destroyed by Mount Vesuvius in AD 79, provide a unique testimony to Greco-Roman civilisation."}'::jsonb),
                ('it-cinque-terre','826',1997::smallint,
                    ARRAY['ii','iv','v'], 'cultural',
                    4683.0::numeric,
                    '{"en":"The Cinque Terre coastal area and the Ligurian hinterland represent an extraordinary example of the human interaction with nature and landscape."}'::jsonb),
                ('it-pisa-cathedral','395',1987::smallint,
                    ARRAY['i','ii','iv','vi'], 'cultural',
                    8.87::numeric,
                    '{"en":"The Piazza del Duomo of Pisa is an outstanding example of medieval architecture that had great influence on art and architecture."}'::jsonb),
                ('it-ravenna-mosaics','788',1996::smallint,
                    ARRAY['i','ii','iii','iv'], 'cultural',
                    2.49::numeric,
                    '{"en":"Ravenna was the seat of the Western Roman Empire and then of Byzantine Italy. Its mosaics are unique artistic masterpieces."}'::jsonb),
                ('it-amalfi-coast','830',1997::smallint,
                    ARRAY['ii','iv','v'], 'cultural',
                    11231.0::numeric,
                    '{"en":"The Amalfi Coast is an outstanding example of a Mediterranean landscape with great cultural and natural interest."}'::jsonb),
                -- Greece
                ('gr-acropolis','404',1987::smallint,
                    ARRAY['i','ii','iii','iv','vi'], 'cultural',
                    3.4::numeric,
                    '{"en":"The Acropolis of Athens, the symbol of classical Greek civilization, is a universal symbol of excellence."}'::jsonb),
                ('gr-delphi-site','393',1987::smallint,
                    ARRAY['i','ii','iii','iv','vi'], 'cultural',
                    69.1::numeric,
                    '{"en":"Delphi was the site of the Delphic oracle, the most important oracle in the classical Greek world."}'::jsonb),
                ('gr-ancient-olympia','517',1989::smallint,
                    ARRAY['i','ii','iii','iv','vi'], 'cultural',
                    105.4::numeric,
                    '{"en":"Olympia was the birthplace of the Olympic Games and has sanctuaries, temples and stadiums from 776 BC."}'::jsonb),
                ('gr-meteora','455',1988::smallint,
                    ARRAY['i','ii','iv','v','vii'], 'mixed',
                    3753.5::numeric,
                    '{"en":"The rock formations of Meteora carry communities of monks dating back to the 14th century."}'::jsonb),
                ('gr-vergina','794',1996::smallint,
                    ARRAY['i','ii','iii'], 'cultural',
                    334.0::numeric,
                    '{"en":"Aigai was the first capital of the Kingdom of Macedon, and contains the tomb of Philip II, father of Alexander the Great."}'::jsonb),
                ('gr-rhodes-medieval','395',1988::smallint,
                    ARRAY['ii','iv','v'], 'cultural',
                    105.0::numeric,
                    '{"en":"The medieval city of Rhodes is one of the best-preserved medieval towns in Europe."}'::jsonb),
                ('gr-mycenae-tiryns','941',1999::smallint,
                    ARRAY['i','ii','iii','iv','vi'], 'cultural',
                    58.1::numeric,
                    '{"en":"Mycenae and Tiryns are the most important witnesses to the development of Greek civilization during the Bronze Age."}'::jsonb),
                ('gr-delos','530',1990::smallint,
                    ARRAY['i','ii','iii','iv','vi'], 'cultural',
                    364.0::numeric,
                    '{"en":"Delos, one of the most important mythological, historical and archaeological sites in Greece."}'::jsonb),
                -- Egypt
                ('eg-giza-pyramids','86',1979::smallint,
                    ARRAY['i','iii','vi'], 'cultural',
                    16203.36::numeric,
                    '{"en":"Memphis and its necropolis with the field of pyramids, including the Great Pyramid of Giza, one of the Seven Wonders of the Ancient World."}'::jsonb),
                ('eg-ancient-thebes','87',1979::smallint,
                    ARRAY['i','iii','vi'], 'cultural',
                    7391.0::numeric,
                    '{"en":"Ancient Thebes with its Necropolis, temples and palaces on the banks of the Nile."}'::jsonb),
                ('eg-abu-simbel','88',1979::smallint,
                    ARRAY['i','iii','vi'], 'cultural',
                    37401.0::numeric,
                    '{"en":"Abu Simbel contains the two rock temples of Ramesses II. Saved by UNESCO-organised international campaign."}'::jsonb),
                ('eg-islamic-cairo','89',1979::smallint,
                    ARRAY['i','v','vi'], 'cultural',
                    524.0::numeric,
                    '{"en":"Cairo''s historic districts, spanning 1000 years of Islamic history with mosques, madrasas and mausoleums."}'::jsonb),
                ('eg-saint-catherines','954',2002::smallint,
                    ARRAY['i','ii','iii','iv','vi'], 'cultural',
                    6000.0::numeric,
                    '{"en":"Saint Catherine''s Monastery is a living monastery containing the world''s oldest continuously operating library."}'::jsonb),
                ('eg-wadi-al-hitan','1186',2005::smallint,
                    ARRAY['viii'], 'natural',
                    200015.0::numeric,
                    '{"en":"Wadi Al-Hitan contains invaluable fossil remains of the earliest and now extinct suborder of whales."}'::jsonb),
                ('eg-abu-mena','90',1979::smallint,
                    ARRAY['i','ii','iv'], 'cultural',
                    182.0::numeric,
                    '{"en":"Abu Mena was built over the tomb of the Egyptian martyr Menas, and became one of the great Christian pilgrimage sites."}'::jsonb),
                -- Morocco
                ('ma-medina-fez','170',1981::smallint,
                    ARRAY['ii','v'], 'cultural',
                    280.0::numeric,
                    '{"en":"Fez was founded in the 9th century and became the most important city of Morocco. The medina is the world''s largest living medieval city."}'::jsonb),
                ('ma-ait-benhaddou','444',1987::smallint,
                    ARRAY['iv','v'], 'cultural',
                    3.0::numeric,
                    '{"en":"Ksar is a group of earthen buildings surrounded by high walls, an outstanding example of southern Moroccan architecture."}'::jsonb),
                ('ma-historic-meknes','793',1996::smallint,
                    ARRAY['iv'], 'cultural',
                    280.0::numeric,
                    '{"en":"Meknes was founded in the 11th century by the Almoravids and became one of the four imperial cities of Morocco."}'::jsonb),
                ('ma-medina-marrakech','331',1985::smallint,
                    ARRAY['i','ii','iv','v'], 'cultural',
                    1700.0::numeric,
                    '{"en":"Marrakech was founded in 1070 by the Almoravids and became one of the major Islamic cities."}'::jsonb),
                ('ma-volubilis','836',1997::smallint,
                    ARRAY['ii','iii','iv','vi'], 'cultural',
                    42.0::numeric,
                    '{"en":"Volubilis is an exceptionally well-preserved example of a Roman settlement on the southern fringe of the Roman Empire."}'::jsonb),
                ('ma-medina-essaouira','753',2001::smallint,
                    ARRAY['ii','iv'], 'cultural',
                    30.0::numeric,
                    '{"en":"Essaouira is an 18th-century fortified town with a unique blend of European and Moroccan architectural influences."}'::jsonb),
                ('ma-rabat-capital','1401',2012::smallint,
                    ARRAY['i','ii','iv'], 'cultural',
                    1391.0::numeric,
                    '{"en":"Rabat is an outstanding example of 20th-century urban planning illustrating the modernist movement."}'::jsonb),
                -- Japan
                ('jp-horyuji','660',1993::smallint,
                    ARRAY['i','ii','iv','vi'], 'cultural',
                    579.0::numeric,
                    '{"en":"The Buddhist Monuments in the Horyu-ji Area contain the world''s oldest surviving wooden structures."}'::jsonb),
                ('jp-himeji-castle','661',1993::smallint,
                    ARRAY['i','iv'], 'cultural',
                    107.0::numeric,
                    '{"en":"Himeji Castle is the finest surviving example of early 17th-century Japanese castle architecture."}'::jsonb),
                ('jp-historic-kyoto','688',1994::smallint,
                    ARRAY['ii','iv'], 'cultural',
                    1657.6::numeric,
                    '{"en":"Kyoto was the imperial capital of Japan for over a millennium and contains 17 component Buddhist temples and Shinto shrines."}'::jsonb),
                ('jp-historic-nara','870',1998::smallint,
                    ARRAY['ii','iii','iv','vi'], 'cultural',
                    3317.0::numeric,
                    '{"en":"Ancient Nara was Japan''s first permanent capital and an outstanding example of cultural exchanges between China, Korea and Japan."}'::jsonb),
                ('jp-hiroshima-dome','775',1996::smallint,
                    ARRAY['vi'], 'cultural',
                    4.0::numeric,
                    '{"en":"The Hiroshima Peace Memorial is a universal symbol of the hope for world peace and the end to all nuclear weapons."}'::jsonb),
                ('jp-nikko','913',1999::smallint,
                    ARRAY['i','iv','vi'], 'cultural',
                    5077.7::numeric,
                    '{"en":"The shrines and temples of Nikko are a unique synthesis of Japanese religious art integrating architecture with its natural setting."}'::jsonb),
                ('jp-itsukushima','776',1996::smallint,
                    ARRAY['i','ii','iv','vi'], 'cultural',
                    431.0::numeric,
                    '{"en":"The island of Itsukushima in the Seto Inland Sea has been a holy place in the Shinto religion since the earliest times."}'::jsonb),
                ('jp-mount-fuji','1418',2013::smallint,
                    ARRAY['iii','vi'], 'cultural',
                    20702.0::numeric,
                    '{"en":"Mount Fuji, a stratovolcano sacred to the Japanese, has inspired artists and pilgrims alike for centuries."}'::jsonb),
                ('jp-yoshino-kii','1142',2004::smallint,
                    ARRAY['ii','iii','iv','vi'], 'cultural',
                    495.3::numeric,
                    '{"en":"The Sacred Sites and Pilgrimage Routes represent the religious traditions of Shintoism and Buddhism over more than 1,200 years."}'::jsonb),
                ('jp-shirakawa-go','734',1995::smallint,
                    ARRAY['iv','v'], 'cultural',
                    68.7::numeric,
                    '{"en":"The villages of Shirakawa-go and Gokayama are outstanding examples of a type of traditional domestic Japanese architecture."}'::jsonb),
                -- South Korea
                ('kr-haeinsa','737',1995::smallint,
                    ARRAY['iv','vi'], 'cultural',
                    32.7::numeric,
                    '{"en":"Haeinsa, a Buddhist temple on Mt. Gaya, houses the Tripitaka Koreana, the most complete collection of Buddhist texts, engraved on 81,000 woodblocks."}'::jsonb),
                ('kr-jongmyo-shrine','738',1995::smallint,
                    ARRAY['iv'], 'cultural',
                    19.3::numeric,
                    '{"en":"Jongmyo is the oldest and most authentic Confucian royal shrine preserved in the Far East."}'::jsonb),
                ('kr-changdeokgung','816',1997::smallint,
                    ARRAY['ii','iii','iv'], 'cultural',
                    584.7::numeric,
                    '{"en":"Changdeokgung Palace Complex was built as a secondary palace of the Joseon Dynasty (1405) and was well integrated with its natural setting."}'::jsonb),
                ('kr-hwaseong-fortress','817',1997::smallint,
                    ARRAY['ii','iii'], 'cultural',
                    130.7::numeric,
                    '{"en":"Hwaseong Fortress, built in 1796, represents a combination of defensive structures from the East and the West."}'::jsonb),
                ('kr-gyeongju-historic','976',2000::smallint,
                    ARRAY['ii','iii'], 'cultural',
                    3154.6::numeric,
                    '{"en":"Gyeongju, the ancient capital of the Silla Kingdom, contains a remarkable array of outstanding Buddhist art."}'::jsonb),
                ('kr-gochang-dolmen','977',2000::smallint,
                    ARRAY['iii'], 'cultural',
                    540.0::numeric,
                    '{"en":"The dolmen sites of Gochang, Hwasun and Ganghwa are the most important and densest concentration of dolmens in Korea."}'::jsonb),
                ('kr-jeju-volcanic','1264',2007::smallint,
                    ARRAY['vii','viii'], 'natural',
                    18846.0::numeric,
                    '{"en":"Jeju Volcanic Island and Lava Tubes is a site of outstanding geological interest, with its volcanic features and unique biodiversity."}'::jsonb),
                -- Thailand
                ('th-sukhothai-historic','574',1991::smallint,
                    ARRAY['i','iii'], 'cultural',
                    7000.0::numeric,
                    '{"en":"Sukhothai was the first capital of the Thai Kingdom (13th–14th centuries) and represents the first stages of Thai architecture and sculpture."}'::jsonb),
                ('th-ayutthaya-historic','576',1991::smallint,
                    ARRAY['iii'], 'cultural',
                    2967.0::numeric,
                    '{"en":"Ayutthaya was the Thai capital from 1350 to 1767 and its ruins show the grandeur of its civilisation."}'::jsonb),
                ('th-ban-chiang','575',1992::smallint,
                    ARRAY['iii'], 'cultural',
                    1315.0::numeric,
                    '{"en":"Ban Chiang is the most important prehistoric settlement yet discovered in Southeast Asia and changes the scholarly understanding of the origin of Bronze Age culture."}'::jsonb),
                ('th-thungyai-wildlife','591',1991::smallint,
                    ARRAY['vii','ix','x'], 'natural',
                    622200.0::numeric,
                    '{"en":"Thungyai-Huai Kha Khaeng Wildlife Sanctuaries contain the largest area of intact forest ecosystems in mainland Southeast Asia."}'::jsonb)
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

    # --- 5. Update heritage_objects.unesco_inscription_year ------------------
    op.execute(
        """
        UPDATE heritage_objects ho
        SET unesco_inscription_year = ui.inscription_year
        FROM unesco_inscriptions ui
        WHERE ui.heritage_id = ho.id
          AND ho.unesco_inscription_year IS NULL
          AND ho.country_code IN ('IT','GR','EG','MA','JP','KR','TH');
        """
    )

    # --- 6. Heritage facts (provenance) --------------------------------------
    op.execute(
        """
        INSERT INTO heritage_facts
            (heritage_id, predicate, object_value, confidence, is_winning, asserted_at)
        SELECT
            ui.heritage_id,
            'unesco_inscription_year',
            to_jsonb(ui.inscription_year),
            90,
            true,
            now()
        FROM unesco_inscriptions ui
        JOIN heritage_objects ho ON ho.id = ui.heritage_id
        WHERE ho.country_code IN ('IT','GR','EG','MA','JP','KR','TH')
          AND NOT EXISTS (
            SELECT 1 FROM heritage_facts hf
            WHERE hf.heritage_id = ui.heritage_id
              AND hf.predicate = 'unesco_inscription_year'
              AND hf.is_winning
              AND hf.superseded_at IS NULL
          );
        """
    )

    # --- 7. Fact provenance link ---------------------------------------------
    op.execute(
        """
        INSERT INTO fact_provenance (fact_id, provenance_id, confidence)
        SELECT hf.id, hp.id, 90
        FROM heritage_facts hf
        JOIN heritage_objects ho ON ho.id = hf.heritage_id
        JOIN heritage_provenance hp ON hp.slug = 'unesco_whc'
        WHERE hf.predicate = 'unesco_inscription_year'
          AND ho.country_code IN ('IT','GR','EG','MA','JP','KR','TH')
        ON CONFLICT (fact_id, provenance_id) DO NOTHING;
        """
    )

    # --- 8. Pricing zone: europe_apac ----------------------------------------
    op.execute(
        """
        INSERT INTO pricing_zones
            (slug, name, country_codes, default_currency, purchasing_power_index)
        VALUES
            ('europe_apac',
             '{"en":"Europe and Asia-Pacific","fr":"Europe et Asie-Pacifique","zh":"欧洲和亚太地区"}'::jsonb,
             ARRAY['IT','GR','EG','MA','JP','KR','TH']::char(2)[],
             'USD',
             0.80)
        ON CONFLICT (slug) DO NOTHING;
        """
    )

    # --- 9. Prices for europe_apac zone --------------------------------------
    op.execute(
        """
        INSERT INTO prices (plan_id, pricing_zone_id, currency, amount, is_active)
        SELECT pp.id, pz.id, 'USD', price_data.amount, true
        FROM (VALUES
            ('premium_monthly', 3.9900::numeric),
            ('premium_yearly',  39.9900::numeric)
        ) AS price_data(plan_slug, amount)
        JOIN product_plans pp ON pp.slug = price_data.plan_slug
        JOIN pricing_zones pz ON pz.slug = 'europe_apac'
        ON CONFLICT (plan_id, pricing_zone_id, currency, effective_from) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM heritage_objects
        WHERE country_code IN ('IT','GR','EG','MA','JP','KR','TH')
          AND (
            pub_id LIKE 'it-%' OR pub_id LIKE 'gr-%' OR pub_id LIKE 'eg-%'
            OR pub_id LIKE 'ma-%' OR pub_id LIKE 'jp-%'
            OR pub_id LIKE 'kr-%' OR pub_id LIKE 'th-%'
          );
        """
    )
    op.execute(
        """
        DELETE FROM geographic_admin_levels
        WHERE admin_level_type = 'site'
          AND country_code IN ('IT','GR','EG','MA','JP','KR','TH');
        """
    )
    op.execute(
        """
        DELETE FROM cities
        WHERE country_code IN ('IT','GR','EG','MA','JP','KR','TH')
          AND slug IN (
            'rome','florence','venice','milan','naples','pompeii',
            'athens','thessaloniki','delphi','olympia',
            'cairo','luxor','aswan','alexandria','giza',
            'marrakech','fez','casablanca','rabat','meknes','essaouira',
            'tokyo','kyoto','nara','hiroshima','osaka',
            'seoul','gyeongju','suwon','andong',
            'bangkok','chiang_mai','sukhothai','ayutthaya'
          );
        """
    )
    op.execute(
        """
        DELETE FROM geographic_admin_levels
        WHERE admin_level_type = 'city'
          AND country_code IN ('IT','GR','EG','MA','JP','KR','TH');
        """
    )
    op.execute(
        """
        DELETE FROM prices
        WHERE pricing_zone_id = (
            SELECT id FROM pricing_zones WHERE slug = 'europe_apac'
        );
        """
    )
    op.execute("DELETE FROM pricing_zones WHERE slug = 'europe_apac';")
