import time
import uuid
import platform
from sqlalchemy.orm import Session
from hub.db.schema import SystemVersion, EvacInfo, KBArticle, Category, Hub, User


def _generate_device_id() -> str:
    """Derive a stable device ID from the machine's hostname + node (MAC-based)."""
    node_hex = format(uuid.getnode(), '012x')
    host = platform.node() or "hub"
    return f"{host}-{node_hex}"


def seed_data(db: Session):
    # 1. Ensure SystemVersion exists (replaces KBMeta)
    sv = db.query(SystemVersion).filter(SystemVersion.id == 1).first()
    if not sv:
        sv = SystemVersion(id=1, kb_version=1, last_published=int(time.time()))
        db.add(sv)
        print("Seeded SystemVersion.")

    # 2. Seed default message categories
    if db.query(Category).count() == 0:
        defaults = [
            ("Resource Request", "Request supplies, equipment, or personnel from another hub"),
            ("Medical Alert", "Medical emergency or health-related communication"),
            ("Status Update", "General status report from a hub"),
            ("Evacuation Notice", "Evacuation orders or relocation instructions"),
            ("General Communication", "General inter-hub messages"),
        ]
        for name, desc in defaults:
            db.add(Category(category_name=name, description=desc))
        print("Seeded message categories.")

    # 3. Ensure this hub exists in the hub table
    this_hub = db.query(Hub).first()
    if not this_hub:
        device_id = _generate_device_id()
        db.add(Hub(
            device_id=device_id,
            hub_name="This Hub",
            location="Local",
            created_at=int(time.time()),
        ))
        print(f"Seeded default hub entry (device_id={device_id}).")
    elif not this_hub.device_id:
        this_hub.device_id = _generate_device_id()
        print(f"Back-filled device_id={this_hub.device_id} on existing hub.")

    # 4. Ensure EvacInfo row exists (replaces StructuredConfig defaults)
    evac = db.query(EvacInfo).filter(EvacInfo.id == 1).first()
    if not evac:
        evac = EvacInfo(
            id=1,
            food_schedule="Morning: 08:00, Lunch: 12:00, Dinner: 18:00",
            food_distribution_location="Cafeteria near the basketball court",
            sleeping_zones="Zone A, Zone B",
            medical_station="Room 101",
            registration_steps="Step 1: Go to desk. Step 2: Show ID.",
            announcements="",
            emergency_mode="false",
            last_updated="",
            info_metadata="{}",
        )
        db.add(evac)
        print("Seeded EvacInfo.")

    # 3. Seed a welcome KB article if the table is empty
    if db.query(KBArticle).count() == 0:
        now = int(time.time())
        article = KBArticle(
            question="Welcome",
            answer="Welcome to the Evacuation Center. Please register at the front desk.",
            category="general",
            tags="welcome,start",
            enabled=1,
            source="seed",
            created_at=now,
            last_updated=now,
        )
        db.add(article)
        print("Seeded welcome article.")

    db.commit()

    # Sync evac_info fields → KB articles for semantic search
    from hub.db.evac_sync import sync_evac_to_kb
    sync_evac_to_kb(db)

    # Seed default admin users (only if table is empty)
    if db.query(User).count() == 0:
        try:
            from passlib.context import CryptContext
            _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
            _hash = _pwd_ctx.hash
        except ImportError:
            import hashlib
            def _hash(pw):
                return "plain:" + hashlib.sha256(pw.encode()).hexdigest()

        default_users = [
            {"username": "admin",    "password": "admin123"},
            {"username": "admin2", "password": "admin123"},
            {"username": "admin3",    "password": "admin123"},
        ]
        now_ts = int(time.time())
        for u in default_users:
            db.add(User(
                username=u["username"],
                password=_hash(u["password"]),
                is_first_login=True,
                created_at=now_ts,
            ))
        db.commit()
        print("Seeded 3 default users (admin, admin2, admin3).")

    # Enrich tags for core KB articles with multilingual synonyms
    _enrich_multilingual_tags(db)


def _enrich_multilingual_tags(db: Session):
    """Add multilingual tags to core KB articles to improve non-English recall."""
    from hub.db.schema import KBArticle
    from hub.retrieval.embedder import load_embedder, serialize_embedding, get_embeddable_text
    from hub.retrieval.search import invalidate_corpus_cache
    import time as _time

    tag_map = {
        "where can i wash my clothes?": [
            "laundry", "wash", "clothes",
            "lavanderia", "area de lavado", "lavar la ropa",
            "waschraum", "wasche", "waschebereich",
            "blanchisserie", "zone de lavage", "laver les vetements",
            "洗濯", "洗濯場所", "洗濯エリア",
        ],
        "what is the food schedule?": [
            "food", "meals", "schedule",
            "food distribution", "food distribution schedule", "food distribution time",
            "meal distribution", "meal distribution schedule",
            "comida", "horario de comidas",
            "essen", "essenszeit",
            "repas", "horaire des repas",
            "食事", "食事時間",
        ],
        "where are the sleeping zones?": [
            "sleeping", "beds", "cots",
            "zona de dormir", "camas",
            "schlafbereich", "betten",
            "zone de sommeil", "lits",
            "寝る場所", "寝室", "ベッド",
        ],
        "where is the medical station?": [
            "medical", "clinic", "doctor", "nurse",
            "medico", "clinica",
            "arzt", "klinik",
            "medical", "clinique",
            "医療", "診療所",
        ],
        "how do i register?": [
            "registration", "sign up", "check in",
            "registro", "inscribirme",
            "registrierung", "anmeldung",
            "inscription", "enregistrer",
            "登録", "受付",
        ],
    }

    updated = []
    for art in db.query(KBArticle).all():
        q = (art.question or "").strip().lower()
        if q in tag_map:
            existing = set(t.strip() for t in (art.tags or "").split(",") if t.strip())
            new_tags = [t for t in tag_map[q] if t and t not in existing]
            if new_tags:
                art.tags = ",".join(list(existing) + new_tags)
                art.last_updated = int(_time.time())
                art.embedding = None
                updated.append(art)

    if not updated:
        return

    # Re-embed updated articles
    embedder = None
    try:
        embedder = load_embedder()
    except Exception:
        embedder = None
    for art in updated:
        try:
            if embedder:
                text = get_embeddable_text(art)
                vec = embedder.embed_text(text)
                art.embedding = serialize_embedding(vec)
            else:
                art.embedding = None
        except Exception:
            # Leave embedding None; startup will attempt to fill missing
            art.embedding = None

    db.commit()
    invalidate_corpus_cache()
