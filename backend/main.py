import os
# Importa funzioni sicure per confrontare credenziali/token.
import secrets
from datetime import date
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session


# Tenta import relativo quando il modulo gira come package.
try:
    # Importa modelli e utility DB dal modulo locale package.
    from .database import Gara, News, SessionLocal, init_db
except ImportError:
    # Fallback per esecuzione diretta del file senza package context.
    from database import Gara, News, SessionLocal, init_db



app = FastAPI(title="Ciclismo API", version="1.0.0")

# Security scheme HTTP Basic per rotte protette con username/password.
basic_security = HTTPBasic()

# Individua la root del progetto
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
IMAGES_PREFIX = "/frontend/images/"

# Monta la cartella frontend sotto la rotta statica /frontend.
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


# Normalizza vari formati di URL/percorso immagine in un formato coerente.
def normalize_image_url(value: Optional[str]) -> Optional[str]:
    cleaned = (value or "").strip().replace("\\", "/")
    if not cleaned:
        return None
    # Accetta URL esterni/data URI o URL statiche gia complete.
    if cleaned.startswith(("http://", "https://", "data:", "/frontend/")):
        return cleaned
    # Supporta path relativi comuni tipo ./images/gare/file.jpg
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    if cleaned.startswith("frontend/"):
        return f"/{cleaned}"
    if cleaned.startswith("images/"):
        return f"/frontend/{cleaned}"
    if cleaned.startswith("/"):
        return cleaned
    return f"{IMAGES_PREFIX}{cleaned}"


# Legge credenziali admin da variabili d'ambiente locali.
def load_admin_credentials() -> list[tuple[str, str]]:
    username = os.getenv("ADMIN_USERNAME", "").strip()
    password = os.getenv("ADMIN_PASSWORD", "")

    if not username or not password:
        raise RuntimeError(
            "Credenziali admin mancanti: imposta ADMIN_USERNAME e ADMIN_PASSWORD nel sistema locale."
        )

    return [(username, password)]


# Schema base usato per creare news.
class NewsBase(BaseModel):
    titolo: str = Field(min_length=3, max_length=255)
    sottotitolo: Optional[str] = Field(default=None, max_length=255)
    contenuto: str = Field(min_length=10)
    categoria: str = Field(default="Generale", max_length=80)
    immagine_url: str = Field(min_length=10, max_length=500)
    fonte_url: Optional[str] = Field(default=None, max_length=500)
    data_pubblicazione: date = Field(default_factory=date.today)


# Schema create news identico al base.
class NewsCreate(NewsBase):
    # Nessun campo extra.
    pass


# Schema update news con tutti i campi opzionali.
class NewsUpdate(BaseModel):
    titolo: Optional[str] = Field(default=None, min_length=3, max_length=255)
    sottotitolo: Optional[str] = Field(default=None, max_length=255)
    contenuto: Optional[str] = Field(default=None, min_length=10)
    categoria: Optional[str] = Field(default=None, max_length=80)
    immagine_url: Optional[str] = Field(default=None, min_length=10, max_length=500)
    fonte_url: Optional[str] = Field(default=None, max_length=500)
    data_pubblicazione: Optional[date] = None


# Schema base usato per creare gare.
class GaraBase(BaseModel):
    nome: str = Field(min_length=3, max_length=255)
    descrizione: Optional[str] = None
    data_gara: date
    luogo: str = Field(min_length=2, max_length=255)
    categoria: str = Field(default="Strada", max_length=80)
    immagine_url: Optional[str] = Field(default=None, max_length=500)
    distanza_km: Optional[int] = Field(default=None, ge=1, le=5000)
    dislivello_m: Optional[int] = Field(default=None, ge=0, le=70000)
    orario_partenza: Optional[str] = Field(default=None, max_length=10)
    is_principale: bool = False


# Schema create gara identico al base.
class GaraCreate(GaraBase):
    pass


# Schema update gara con campi opzionali.
class GaraUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=3, max_length=255)
    descrizione: Optional[str] = None
    data_gara: Optional[date] = None
    luogo: Optional[str] = Field(default=None, min_length=2, max_length=255)
    categoria: Optional[str] = Field(default=None, max_length=80)
    immagine_url: Optional[str] = Field(default=None, max_length=500)
    distanza_km: Optional[int] = Field(default=None, ge=1, le=5000)
    dislivello_m: Optional[int] = Field(default=None, ge=0, le=70000)
    orario_partenza: Optional[str] = Field(default=None, max_length=10)
    is_principale: Optional[bool] = None


# Payload richiesto per login admin.
class AdminLoginRequest(BaseModel):
    username: str
    password: str


# Dependency FastAPI che apre una sessione DB e la chiude automaticamente.
def get_db():
    db = SessionLocal()
    try:
        # Restituisce la sessione alla route chiamante.
        yield db
    finally:
        db.close()


# Verifica credenziali admin usando confronto in tempo costante.
def validate_admin_credentials(username: str, password: str) -> str:
    try:
        # Ricarica il file a ogni login per applicare subito eventuali modifiche.
        admin_credentials = load_admin_credentials()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configurazione credenziali admin non valida",
        )

    for admin_user, admin_pass in admin_credentials:
        is_user_ok = secrets.compare_digest(username, admin_user)
        is_pass_ok = secrets.compare_digest(password, admin_pass)
        if is_user_ok and is_pass_ok:
            return username

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenziali non valide",
    )


# Dependency che valida credenziali HTTP Basic ricevute nell'header Authorization.
def verify_admin_basic(credentials: HTTPBasicCredentials = Depends(basic_security)) -> str:
    # Se mancano username o password, rifiuta richiesta.
    if not credentials.username or credentials.password is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login richiesto")

    # Valida coppia user/pass con confronto sicuro.
    return validate_admin_credentials(credentials.username, credentials.password)


# Hook startup: inizializza schema e seed (compatibile).
@app.on_event("startup")
def on_startup() -> None:
    # Crea/aggiorna tabelle DB.
    init_db()


# Route root che serve home page.
@app.get("/")
def page_index():
    # Restituisce file statico index.
    return FileResponse(FRONTEND_DIR / "index.html")


# Route dettaglio che serve detail page.
@app.get("/detail")
def page_detail():
    # Restituisce file statico detail.
    return FileResponse(FRONTEND_DIR / "detail.html")


# Route admin che serve pagina admin.
@app.get("/admin")
def page_admin():
    # Restituisce file statico admin.
    return FileResponse(FRONTEND_DIR / "admin.html")


# Endpoint health-check minimale.
@app.get("/api/health")
def health_check():
    # Risposta di stato servizio.
    return {"ok": True, "service": "ciclismo-api"}


# Endpoint login admin.
@app.post("/api/admin/login")
def admin_login(payload: AdminLoginRequest):
    # Valida username/password ricevuti.
    username = validate_admin_credentials(payload.username, payload.password)

    # Restituisce login ok; le rotte protette usano Basic Auth ad ogni richiesta.
    return {
        "ok": True,
        "username": username,
        "auth_type": "basic",
    }


# Endpoint aggregato per homepage e client API-first.
@app.get("/api/home")
def get_home_feed(news_limit: int = Query(default=12, ge=1, le=100), future_only: bool = Query(default=True), db: Session = Depends(get_db)):
    news_total = db.query(News).count()
    news_items = db.query(News).order_by(News.data_pubblicazione.desc()).limit(news_limit).all()

    gare_query = db.query(Gara)
    if future_only:
        gare_query = gare_query.filter(Gara.data_gara >= date.today())

    gare_items = gare_query.order_by(Gara.data_gara.asc()).all()
    return {
        "ok": True,
        "news_total": news_total,
        "news_items": news_items,
        "gare_total": len(gare_items),
        "gare_items": gare_items,
    }


# Endpoint lista news con filtri e paginazione.
@app.get("/api/news")
def get_news(categoria: Optional[str] = Query(default=None), q: Optional[str] = Query(default=None), limit: Optional[int] = Query(default=None, ge=1), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    # Base query su tabella News.
    query = db.query(News)

    # Se richiesta categoria, applica filtro case-insensitive.
    if categoria:
        query = query.filter(News.categoria.ilike(f"%{categoria}%"))
    # Se richiesta ricerca titolo, applica filtro testuale.
    if q:
        query = query.filter(News.titolo.ilike(f"%{q}%"))
    # Calcola totale dopo filtri.
    total = query.count()
    # Ordina per data decrescente e applica offset.
    q2 = query.order_by(News.data_pubblicazione.desc()).offset(offset)

    # Applica limite solo se presente, poi materializza lista.
    items = (q2.limit(limit) if limit is not None else q2).all()
    return {"total": total, "items": items}


# Endpoint dettaglio singola news.
@app.get("/api/news/{news_id}")
def get_news_detail(news_id: int, db: Session = Depends(get_db)):
    news = db.query(News).filter(News.id == news_id).first()

    if news is None:
        raise HTTPException(status_code=404, detail="Notizia non trovata")

    return news


# Endpoint creazione news, protetto da token admin.
@app.post("/api/news", status_code=201)
def add_news(payload: NewsCreate, _: str = Depends(verify_admin_basic), db: Session = Depends(get_db)):
    # Converte payload in dict Python.
    data = payload.model_dump()

    # Normalizza URL immagine prima del salvataggio.
    data["immagine_url"] = normalize_image_url(data.get("immagine_url"))

    # Crea istanza ORM News.
    news = News(**data)
    db.add(news)
    db.commit()
    db.refresh(news)
    return news


# Endpoint modifica news, protetto da token admin.
@app.put("/api/news/{news_id}")
def update_news(news_id: int, payload: NewsUpdate, _: str = Depends(verify_admin_basic), db: Session = Depends(get_db)):
    # Cerca la news target.
    news = db.query(News).filter(News.id == news_id).first()

    # Se non trovata, 404.
    if news is None:
        raise HTTPException(status_code=404, detail="Notizia non trovata")

    # Estrae solo campi realmente presenti nel payload.
    updates = payload.model_dump(exclude_unset=True)

    # Se immagine inclusa, la normalizza.
    if "immagine_url" in updates:
        updates["immagine_url"] = normalize_image_url(updates.get("immagine_url"))

    # Applica ogni campo aggiornato al modello ORM.
    for key, value in updates.items():
        setattr(news, key, value)

    db.commit()
    db.refresh(news)
    return news


# Endpoint eliminazione news, protetto da token admin.
@app.delete("/api/news/{news_id}")
def delete_news(news_id: int, _: str = Depends(verify_admin_basic), db: Session = Depends(get_db)):
    # Cerca record target.
    news = db.query(News).filter(News.id == news_id).first()

    if news is None:
        raise HTTPException(status_code=404, detail="Notizia non trovata")

    # Marca record per eliminazione.
    db.delete(news)

    # Conferma eliminazione.
    db.commit()

    # Risposta sintetica con id eliminato.
    return {"ok": True, "deleted_id": news_id}


# Endpoint lista gare con filtro categoria e future_only.
@app.get("/api/gare")
def get_gare(categoria: Optional[str] = Query(default=None), future_only: bool = Query(default=True), db: Session = Depends(get_db)):
    # Base query tabella Gara.
    query = db.query(Gara)

    # Se categoria presente, filtra per categoria.
    if categoria:
        query = query.filter(Gara.categoria.ilike(f"%{categoria}%"))

    # Se richiesto future_only, filtra date >= oggi.
    if future_only:
        query = query.filter(Gara.data_gara >= date.today())

    # Ordina per data crescente e materializza risultati.
    items = query.order_by(Gara.data_gara.asc()).all()

    return {"total": len(items), "items": items}


# Endpoint dettaglio singola gara.
@app.get("/api/gare/{gara_id}")
def get_gara_detail(gara_id: int, db: Session = Depends(get_db)):
    # Cerca gara per id.
    gara = db.query(Gara).filter(Gara.id == gara_id).first()

    if gara is None:
        raise HTTPException(status_code=404, detail="Gara non trovata")

    return gara


# Endpoint creazione gara, protetto da token admin.
@app.post("/api/gare", status_code=201)
def add_gara(payload: GaraCreate, _: str = Depends(verify_admin_basic), db: Session = Depends(get_db)):
    # Converte payload in dict.
    data = payload.model_dump()

    # Normalizza URL immagine prima del salvataggio.
    data["immagine_url"] = normalize_image_url(data.get("immagine_url"))

    # Crea istanza ORM Gara.
    gara = Gara(**data)

    db.add(gara)
    db.commit()
    db.refresh(gara)
    return gara



@app.put("/api/gare/{gara_id}")
def update_gara(gara_id: int, payload: GaraUpdate, _: str = Depends(verify_admin_basic), db: Session = Depends(get_db)):
    # Cerca gara target.
    gara = db.query(Gara).filter(Gara.id == gara_id).first()

    if gara is None:
        raise HTTPException(status_code=404, detail="Gara non trovata")

    # Prende solo campi inviati realmente.
    updates = payload.model_dump(exclude_unset=True)

    # Se presente immagine, normalizza percorso.
    if "immagine_url" in updates:
        updates["immagine_url"] = normalize_image_url(updates.get("immagine_url"))

    # Applica update su ogni campo.
    for key, value in updates.items():
        setattr(gara, key, value)

    db.commit()
    db.refresh(gara)
    return gara


# Endpoint eliminazione gara, protetto da token admin.
@app.delete("/api/gare/{gara_id}")
def delete_gara(gara_id: int, _: str = Depends(verify_admin_basic), db: Session = Depends(get_db)):
    gara = db.query(Gara).filter(Gara.id == gara_id).first()

    if gara is None:
        raise HTTPException(status_code=404, detail="Gara non trovata")
    
    db.delete(gara)
    db.commit()
    return {"ok": True, "deleted_id": gara_id}