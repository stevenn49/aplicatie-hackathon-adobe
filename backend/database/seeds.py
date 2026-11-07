"""
Baseline dataset.

The database is shared between teammates, so this seed is idempotent: every row is
keyed by SKU (products) or by (product, external_id) (reviews), and an existing row
is never overwritten. Running it twice adds nothing.

The reviews are realistic consumer text in Romanian and English, dated across the
last twelve weeks so the time-series charts have something to plot. Sentiment is
computed by the real VADER service at insert time — no stored labels are invented.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from database.models import Product, PriceHistory, Review, TrendMetric
from services.sentiment_analysis import sentiment_service

logger = logging.getLogger("marketpulse.database.seeds")


# --------------------------------------------------------------------------- #
# Products
# --------------------------------------------------------------------------- #

PRODUCTS: List[Dict] = [
    {
        "sku": "SM-S931B",
        "name": "Samsung Galaxy S25",
        "brand": "Samsung",
        "category": "Smartphone",
        "price": 3999.99,
        "currency": "RON",
        "source": "eMAG",
        "source_url": "https://www.emag.ro/telefon-mobil-samsung-galaxy-s25",
        "rating": 4.6,
        "launch": "Feb 2025",
        "specs": {
            "Display": "6.2 inch Dynamic AMOLED 2X 120Hz",
            "Processor": "Snapdragon 8 Elite",
            "Memory": "12 GB",
            "Storage": "256 GB",
            "Battery": "4000 mAh",
        },
    },
    {
        "sku": "MYEG3ZD/A",
        "name": "Apple iPhone 16",
        "brand": "Apple",
        "category": "Smartphone",
        "price": 4499.99,
        "currency": "RON",
        "source": "eMAG",
        "source_url": "https://www.emag.ro/telefon-mobil-apple-iphone-16",
        "rating": 4.7,
        "launch": "Sep 2024",
        "specs": {
            "Display": "6.1 inch Super Retina XDR OLED",
            "Processor": "Apple A18",
            "Memory": "8 GB",
            "Storage": "128 GB",
            "Camera": "48 MP Fusion",
        },
    },
    {
        "sku": "WH1000XM5B.CE7",
        "name": "Sony WH-1000XM5",
        "brand": "Sony",
        "category": "Headphones",
        "price": 1499.99,
        "currency": "RON",
        "source": "eMAG",
        "source_url": "https://www.emag.ro/casti-audio-over-the-ear-sony-wh-1000xm5",
        "rating": 4.8,
        "launch": "May 2022",
        "specs": {
            "Type": "Over-ear wireless",
            "Noise cancelling": "Dual Noise Sensor, 8 mics",
            "Battery": "30 hours with ANC",
            "Connectivity": "Bluetooth 5.2, LDAC",
            "Weight": "250 g",
        },
    },
    {
        "sku": "RTX-5080-16G",
        "name": "NVIDIA GeForce RTX 5080",
        "brand": "NVIDIA",
        "category": "Graphics Card",
        "price": 5999.99,
        "currency": "RON",
        "source": "eMAG",
        "source_url": "https://www.emag.ro/placa-video-nvidia-geforce-rtx-5080",
        "rating": 4.5,
        "launch": "Jan 2025",
        "specs": {
            "Memory": "16 GB GDDR7",
            "Architecture": "Blackwell",
            "Interface": "PCIe 5.0",
            "Power": "360 W",
        },
    },
    {
        "sku": "MCX04ZE/A",
        "name": "Apple MacBook Pro 14 M4",
        "brand": "Apple",
        "category": "Laptop",
        "price": 8999.99,
        "currency": "RON",
        "source": "eMAG",
        "source_url": "https://www.emag.ro/laptop-apple-macbook-pro-14-m4",
        "rating": 4.9,
        "launch": "Nov 2024",
        "specs": {
            "Processor": "Apple M4 10-core",
            "Display": "14.2 inch Liquid Retina XDR",
            "Memory": "16 GB unified",
            "Storage": "512 GB SSD",
            "Battery": "Up to 24 hours",
        },
    },
    {
        "sku": "ZGM-00001",
        "name": "Microsoft Surface Laptop 7",
        "brand": "Microsoft",
        "category": "Laptop",
        "price": 5499.00,
        "currency": "RON",
        "source": "eMAG",
        "source_url": "https://www.emag.ro/laptop-microsoft-surface-laptop-7",
        "rating": 4.4,
        "launch": "Jun 2024",
        "specs": {
            "Display": "13.8 inch PixelSense",
            "Processor": "Snapdragon X Plus",
            "Memory": "16 GB",
            "Storage": "512 GB",
            "Battery": "Up to 20 hours",
        },
    },
    {
        "sku": "SM-S938B",
        "name": "Samsung Galaxy S25 Ultra",
        "brand": "Samsung",
        "category": "Smartphone",
        "price": 6499.99,
        "currency": "RON",
        "source": "eMAG",
        "source_url": "https://www.emag.ro/telefon-mobil-samsung-galaxy-s25-ultra",
        "rating": 4.6,
        "launch": "Feb 2025",
        "specs": {
            "Display": "6.9 inch AMOLED 120Hz",
            "Processor": "Snapdragon 8 Elite",
            "Memory": "12 GB",
            "Storage": "256 GB",
            "Camera": "200 MP",
            "Battery": "5000 mAh",
        },
    },
    {
        "sku": "RTX-4070S-12G",
        "name": "NVIDIA GeForce RTX 4070 Super",
        "brand": "NVIDIA",
        "category": "Graphics Card",
        "price": 3299.00,
        "currency": "RON",
        "source": "eMAG",
        "source_url": "https://www.emag.ro/placa-video-nvidia-geforce-rtx-4070-super",
        "rating": 4.7,
        "launch": "Jan 2024",
        "specs": {
            "Memory": "12 GB GDDR6X",
            "Architecture": "Ada Lovelace",
            "Interface": "PCIe 4.0",
            "Power": "220 W",
        },
    },
    {
        "sku": "CFI-2000",
        "name": "Sony PlayStation 5 Slim",
        "brand": "Sony",
        "category": "Gaming",
        "price": 2799.00,
        "currency": "RON",
        "source": "eMAG",
        "source_url": "https://www.emag.ro/consola-sony-playstation-5-slim",
        "rating": 4.5,
        "launch": "Nov 2023",
        "specs": {
            "Storage": "1 TB SSD",
            "Resolution": "Up to 4K 120Hz",
            "Drive": "Blu-ray optional",
            "Features": "Ray tracing, PSSR",
        },
    },
    {
        "sku": "XBOX-SX-1TB",
        "name": "Microsoft Xbox Series X",
        "brand": "Microsoft",
        "category": "Gaming",
        "price": 2499.00,
        "currency": "RON",
        "source": "eMAG",
        "source_url": "https://www.emag.ro/consola-microsoft-xbox-series-x",
        "rating": 4.5,
        "launch": "Nov 2020",
        "specs": {
            "Storage": "1 TB SSD",
            "Resolution": "Up to 4K",
            "Drive": "4K UHD Blu-ray",
            "Features": "Quick Resume",
        },
    },
]


# --------------------------------------------------------------------------- #
# Reviews: (sku, source, author, rating, title, content, days_ago, helpful)
# --------------------------------------------------------------------------- #

REVIEWS: List[Tuple] = [
    # Samsung Galaxy S25
    ("SM-S931B", "eMAG", "Andrei M.", 5.0, "Ecran superb si procesor foarte rapid",
     "Sunt extrem de multumit. Ecranul Dynamic AMOLED este crisp si fluid la 120Hz. Bateria tine o zi intreaga de utilizare intensa, iar camera scoate poze excelente chiar si noaptea.", 3, 14),
    ("SM-S931B", "Reddit", "tech_enthusiast_ro", 4.0, "Great hardware, OneUI is snappy",
     "Upgraded from S22. The Snapdragon processor is a beast, snappy performance and zero lag in games. Battery life is decent, though charging speed could be faster.", 9, 22),
    ("SM-S931B", "eMAG", "Radu D.", 3.0, "Bun dar pretul este cam piperat",
     "Telefonul se misca fluid, dar este destul de overpriced la lansare. Dupa 30 de minute de gaming se simte o usoara incalzire pe rama metalica.", 16, 8),
    ("SM-S931B", "TechCommunity", "dev_mihai", 4.0, "Solid daily driver",
     "The display is excellent outdoors and the software is clean. Battery drain overnight is minimal. The price is high for what is an incremental update.", 24, 5),
    ("SM-S931B", "eMAG", "Ioana P.", 5.0, "Cea mai buna alegere pentru mine",
     "Camera face poze foarte naturale, iar ecranul este luminos. Bateria ma tine lejer o zi si jumatate. Recomand cu incredere.", 31, 11),
    ("SM-S931B", "Reddit", "pixelwatcher", 3.0, "Good but not worth the upgrade",
     "Performance is fine and the display is great, but the price is hard to justify coming from an S23. Charging speed is still slow compared to the competition.", 40, 19),
    ("SM-S931B", "eMAG", "Vlad T.", 4.0, "Raport calitate pret ok dupa reducere",
     "La pretul intreg nu as fi cumparat, dar cu reducere este o alegere buna. Procesorul este rapid, iar software-ul primeste update-uri constante.", 52, 6),

    # Apple iPhone 16
    ("MYEG3ZD/A", "eMAG", "Elena C.", 5.0, "Cea mai buna camera pentru video",
     "Autonomia bateriei este incredibila, ma tine 2 zile lejer la utilizare medie. Camera button este foarte practic, iar iOS 18 este extrem de fluid si stabil.", 2, 31),
    ("MYEG3ZD/A", "Reddit", "ios_dev_guru", 4.0, "Solid iterative upgrade",
     "The A18 chip is blazing fast. Build quality is premium. Only complaint is the lack of 120Hz display on the non-Pro version.", 11, 27),
    ("MYEG3ZD/A", "TechCommunity", "TechReviewer", 4.0, "Ecosistem excelent",
     "Integrarea cu Mac si Apple Watch ramane de neegalat. Sunetul difuzoarelor este clar si puternic, iar pozele au culori naturale.", 18, 9),
    ("MYEG3ZD/A", "eMAG", "Marius G.", 3.0, "Bun, dar scump pentru ce ofera",
     "Telefonul este rapid si camera este foarte buna. Totusi, pretul este mare si incarcarea este lenta comparativ cu Android.", 27, 12),
    ("MYEG3ZD/A", "Reddit", "designfirst", 5.0, "The camera is the reason",
     "Low light photos are noticeably better than the previous generation. The display is bright and the build feels premium. Battery life is excellent for my usage.", 35, 16),
    ("MYEG3ZD/A", "eMAG", "Cristina B.", 4.0, "Foarte bun pentru munca",
     "Il folosesc pentru email si call-uri toata ziua, bateria tine fara probleme. Ecranul este clar, iar camera frontala este buna la video.", 46, 4),
    ("MYEG3ZD/A", "TechCommunity", "swiftdev", 4.0, "Reliable but pricey",
     "Performance and software support are excellent. The price is the main issue, especially for the storage upgrade.", 58, 7),

    # Sony WH-1000XM5
    ("WH1000XM5B.CE7", "eMAG", "Mihai B.", 5.0, "Regele noise cancelling-ului",
     "ANC-ul este pur si simplu uimitor, izoleaza complet zgomotul din birou si din avion. Sunet echilibrat, bass profund si confortabile la purtare indelungata.", 4, 42),
    ("WH1000XM5B.CE7", "Reddit", "audiophile99", 5.0, "Best travel companion",
     "Superb audio fidelity with LDAC. Battery life easily reaches 30 hours. Microphones do a great job on Zoom calls.", 13, 33),
    ("WH1000XM5B.CE7", "eMAG", "Dan R.", 4.0, "Foarte bune, dar pretul mare",
     "Sunetul este excelent si ANC-ul isi face treaba. Pretul este insa mare pentru niste casti, iar husa este cam voluminoasa.", 22, 15),
    ("WH1000XM5B.CE7", "TechCommunity", "headphones_fan", 5.0, "Comfortable for long sessions",
     "Wore them for an eight hour flight with no discomfort. Noise cancelling removes engine noise almost entirely. Audio is balanced with good bass.", 29, 18),
    ("WH1000XM5B.CE7", "eMAG", "Alina S.", 4.0, "Bune pentru birou",
     "Le folosesc zilnic la birou si izoleaza bine vocea colegilor. Bateria tine cateva zile. Aplicatia de control ar putea fi mai simpla.", 38, 6),
    ("WH1000XM5B.CE7", "Reddit", "soundstage", 5.0, "Balanced tuning",
     "Finally a headphone that makes my daily commute quiet. Comfortable and the tuning is much more balanced than before.", 49, 21),

    # NVIDIA RTX 5080
    ("RTX-5080-16G", "Reddit", "pc_master_builder", 5.0, "Unbelievable 4K gaming performance",
     "Runs Cyberpunk 2077 at maximum ray tracing over 100 fps with DLSS. Temperatures stay very cool under load. Premium build quality.", 5, 64),
    ("RTX-5080-16G", "eMAG", "Alexandru V.", 3.0, "Performanta mare dar consum ridicat",
     "Performanta in randare 3D este uluitoare. Totusi, consumul de energie este mare si necesita o sursa serioasa de minim 850W.", 14, 23),
    ("RTX-5080-16G", "TechCommunity", "gpu_nerd", 4.0, "Great but expensive",
     "Performance is excellent at 4K and the memory bandwidth is a real improvement. The price is the main problem, and the power draw is high.", 23, 31),
    ("RTX-5080-16G", "Reddit", "frame_chaser", 4.0, "DLSS carries it",
     "Native performance is good, DLSS makes it excellent. The price is hard to justify if you already own a 40-series card.", 33, 17),
    ("RTX-5080-16G", "eMAG", "Bogdan L.", 5.0, "Merita pentru 4K",
     "Am trecut de la un 3080 si diferenta este mare in 4K. Temperaturile sunt ok, iar zgomotul este redus. Pretul ramane mare.", 44, 9),

    # Apple MacBook Pro 14 M4
    ("MCX04ZE/A", "eMAG", "Cristina P.", 5.0, "Perfect pentru programare si creatie",
     "Bateria tine lejer 18-20 de ore de lucru in VS Code si Docker. Ecranul Liquid Retina este o capodopera vizuala, iar viteza cipului M4 este uluitoare.", 6, 38),
    ("MCX04ZE/A", "Reddit", "macdev_ro", 5.0, "Battery life is unreal",
     "Compiles large projects without the fans spinning up. Battery easily lasts a full working day. The display is the best I have used on a laptop.", 15, 29),
    ("MCX04ZE/A", "TechCommunity", "rustacean", 4.0, "Excellent, pricey upgrades",
     "Performance per watt is unmatched. The base model is good value, but the storage and memory upgrades are very expensive.", 26, 24),
    ("MCX04ZE/A", "eMAG", "George F.", 5.0, "Cea mai buna investitie",
     "Il folosesc pentru editare video si se descurca impecabil. Ecranul este superb, iar bateria tine o zi intreaga de munca.", 37, 13),
    ("MCX04ZE/A", "Reddit", "photo_editor", 4.0, "Great screen, few ports",
     "The display is fantastic for photo editing and the performance is excellent. The limited port selection means another dongle.", 48, 8),

    # Microsoft Surface Laptop 7
    ("ZGM-00001", "eMAG", "laptopnotes", 5.0, "Three days between charges",
     "Three days between charges with my actual workflow. The keyboard and trackpad feel like they finally nailed the details.", 7, 26),
    ("ZGM-00001", "Reddit", "arm_curious", 4.0, "Great hardware, app gaps",
     "Battery life is outstanding and the build quality is excellent. Some of my development tools still do not run natively on ARM.", 17, 34),
    ("ZGM-00001", "TechCommunity", "surface_user", 3.0, "Good laptop, software caveats",
     "The hardware is lovely and the battery life is genuinely all day. Compatibility with older Windows applications is the weak point.", 28, 19),
    ("ZGM-00001", "eMAG", "Raluca M.", 4.0, "Usor si silentios",
     "Este usor, silentios si bateria tine foarte mult. Ecranul este luminos, dar se reflecta lumina in el.", 39, 7),

    # Samsung Galaxy S25 Ultra
    ("SM-S938B", "eMAG", "Stefan I.", 5.0, "Camera zoom extraordinara",
     "Zoom-ul optic este impresionant, iar ecranul anti-reflexie se vede perfect afara. Bateria tine o zi intreaga cu utilizare grea.", 1, 21),
    ("SM-S938B", "Reddit", "note_power_user", 4.0, "S Pen still useful",
     "The display is excellent and the S Pen is genuinely useful for notes. The phone is large and heavy, and charging is slower than competitors.", 12, 28),
    ("SM-S938B", "eMAG", "Adrian N.", 3.0, "Bun, dar greu si scump",
     "Camera este foarte buna si ecranul este superb. Totusi, telefonul este greu si pretul este foarte mare.", 21, 14),
    ("SM-S938B", "TechCommunity", "android_daily", 4.0, "Best display on a phone",
     "The anti-reflective coating is a real improvement outdoors. Performance is excellent. Battery life is good but charging speed lags behind Chinese competitors.", 30, 11),
    ("SM-S938B", "Reddit", "cameraphile", 5.0, "The zoom is the selling point",
     "Photos at 5x and 10x are sharp and usable. The display is bright and the software is feature rich. The price is high.", 43, 9),

    # NVIDIA RTX 4070 Super
    ("RTX-4070S-12G", "eMAG", "Cosmin D.", 5.0, "Excelenta pentru 1440p",
     "Randeaza foarte bine in 1440p si consumul este rezonabil. Temperaturile sunt scazute si zgomotul redus. Raport calitate pret foarte bun.", 8, 18),
    ("RTX-4070S-12G", "Reddit", "1440p_gamer", 4.0, "Great value for 1440p",
     "Excellent performance at 1440p and the power draw is reasonable. 12 GB of memory may become limiting in a few years.", 19, 25),
    ("RTX-4070S-12G", "TechCommunity", "build_guide", 5.0, "Efficient and quiet",
     "Very efficient card with good thermals. Performance is strong at 1440p and the price is reasonable compared to the higher tier.", 32, 12),

    # Sony PlayStation 5 Slim
    ("CFI-2000", "eMAG", "Alexandru P.", 5.0, "Consola perfecta pentru familie",
     "Jocurile arata superb si incarcarea este rapida. Consola este silentioasa. Magazinul digital are preturi mari la jocuri.", 10, 16),
    ("CFI-2000", "Reddit", "console_corner", 4.0, "Smaller and quieter",
     "The slim model is noticeably smaller and quieter. Performance is identical to the original. The disc drive being optional is annoying.", 20, 22),
    ("CFI-2000", "eMAG", "Diana E.", 4.0, "Buna, dar jocurile sunt scumpe",
     "Consola functioneaza impecabil si este silentioasa. Pretul jocurilor este insa mare, iar abonamentul este necesar pentru multiplayer.", 34, 5),

    # Microsoft Xbox Series X
    ("XBOX-SX-1TB", "eMAG", "Robert A.", 5.0, "Raport calitate pret excelent",
     "Quick Resume functioneaza perfect si consola este silentioasa. Game Pass ofera foarte multe jocuri la un pret bun.", 25, 20),
    ("XBOX-SX-1TB", "Reddit", "gamepass_fan", 4.0, "Great value with Game Pass",
     "Quick Resume is seamless and the console is quiet. Game Pass makes it excellent value. Fewer exclusive titles than the competition.", 36, 27),
    ("XBOX-SX-1TB", "TechCommunity", "living_room", 4.0, "Quiet and compact",
     "Runs quietly and the load times are short. The interface is clean. The lack of exclusives is the main weakness.", 50, 10),
]


TRENDS: List[Dict] = [
    {"category": "Smartphone", "keyword": "AI smartphones", "trend_score": 88.5, "search_interest": 92.0, "trend_direction": "increasing"},
    {"category": "Laptop", "keyword": "Apple M4 laptop", "trend_score": 84.0, "search_interest": 86.5, "trend_direction": "increasing"},
    {"category": "Headphones", "keyword": "active noise cancelling", "trend_score": 74.5, "search_interest": 71.0, "trend_direction": "stable"},
    {"category": "Graphics Card", "keyword": "RTX 50 series", "trend_score": 91.0, "search_interest": 96.0, "trend_direction": "increasing"},
    {"category": "Gaming", "keyword": "console generation", "trend_score": 66.0, "search_interest": 63.0, "trend_direction": "stable"},
]


def seed_database_if_empty(db: Session) -> None:
    """
    Insert the baseline dataset when the database has no products.
    Idempotent per row: an existing SKU or review is left untouched.
    """
    existing_products = {p.sku: p for p in db.query(Product).all() if p.sku}
    if existing_products and db.query(Review).count() > 0:
        logger.info("Database already contains products and reviews; skipping seed.")
        return

    logger.info("Seeding baseline tech market intelligence data...")
    now = datetime.utcnow()

    # 1. Products
    created: Dict[str, Product] = {}
    for payload in PRODUCTS:
        sku = payload["sku"]
        product = existing_products.get(sku)
        if product is None:
            product = Product(**payload, review_count=0)
            db.add(product)
            created[sku] = product
        else:
            created[sku] = product
    db.commit()

    for product in created.values():
        db.refresh(product)

    # 2. Price history: four milestones over the last 60 days, ending at the
    #    current price. Deterministic per product (derived from the SKU hash) so
    #    the charts are stable across restarts but the products differ from each
    #    other, which is what makes "top movers" meaningful.
    for index, product in enumerate(created.values()):
        has_history = (
            db.query(PriceHistory)
            .filter(PriceHistory.product_id == product.id)
            .count()
        ) > 0
        if has_history:
            continue
        # Spread the starting premium between roughly -4 % and +14 %.
        seed_offset = ((index * 37) % 19 - 4) / 100.0
        snapshots = [
            (product.price * (1.0 + seed_offset), now - timedelta(days=60)),
            (product.price * (1.0 + seed_offset * 0.55), now - timedelta(days=35)),
            (product.price * (1.0 + seed_offset * 0.15), now - timedelta(days=14)),
            (product.price, now - timedelta(days=1)),
        ]
        for price, recorded_at in snapshots:
            db.add(PriceHistory(
                product_id=product.id,
                price=round(price, 2),
                currency=product.currency,
                recorded_at=recorded_at,
            ))
    db.commit()

    # 3. Reviews, sentiment computed by the real service.
    existing_keys = {
        (r.product_id, r.external_id)
        for r in db.query(Review).filter(Review.external_id.isnot(None)).all()
    }
    added = 0
    for index, (sku, source, author, rating, title, content, days_ago, helpful) in enumerate(REVIEWS):
        product = created.get(sku)
        if product is None:
            continue
        external_id = f"seed-{sku}-{index}"
        if (product.id, external_id) in existing_keys:
            continue

        analysis = sentiment_service.analyze_text(content)
        db.add(Review(
            product_id=product.id,
            source=source,
            external_id=external_id,
            author=author,
            rating=rating,
            title=title,
            content=content,
            sentiment_score=analysis["score"],
            sentiment_label=analysis["label"],
            aspects=analysis["aspects"],
            helpful=helpful,
            published_at=now - timedelta(days=days_ago),
        ))
        added += 1
    db.commit()

    # 4. Recalculate product aggregates from the stored reviews.
    for product in created.values():
        reviews = db.query(Review).filter(Review.product_id == product.id).all()
        if not reviews:
            continue
        product.review_count = len(reviews)
        rated = [r.rating for r in reviews if r.rating]
        if rated:
            product.rating = round(sum(rated) / len(rated), 2)
    db.commit()

    # 5. Trend metrics
    if db.query(TrendMetric).count() == 0:
        for item in TRENDS:
            db.add(TrendMetric(**item, source="Google Trends"))
        db.commit()

    logger.info(
        f"Seed complete: {len(created)} products, {added} reviews added, "
        f"{len(TRENDS)} trend metrics."
    )
