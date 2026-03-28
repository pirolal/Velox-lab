# Importa il tipo `date` per usare date nei modelli e nei valori di default.
from datetime import date

# Importa `Path` per costruire il percorso del file SQLite in modo robusto.
from pathlib import Path

# Importa i tipi e le utility SQLAlchemy usati per definire tabelle e connessione.
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
    text,
)

# Importa la base dichiarativa per i modelli e il factory delle sessioni.
from sqlalchemy.orm import declarative_base, sessionmaker

# Costruisce il percorso assoluto al file `ciclismo.db` nella radice del progetto.
DB_PATH = Path(__file__).resolve().parent.parent / "ciclismo.db"

# Crea la URL SQLAlchemy in formato SQLite usando il percorso convertito in stringa POSIX.
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

# Crea l'engine SQLAlchemy; `check_same_thread=False` serve per SQLite in contesti web.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Prepara un factory di sessioni database da usare nel backend.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Crea la classe base da cui erediteranno tutti i modelli ORM.
Base = declarative_base()

# --- MODELLI ---

# Definisce il modello ORM per la tabella delle notizie.
class News(Base):

    __tablename__ = "news"
    id = Column(Integer, primary_key=True, index=True)
    titolo = Column(String(255), nullable=False)
    sottotitolo = Column(String(255), nullable=True)
    contenuto = Column(Text, nullable=False)
    categoria = Column(String(80), nullable=False, default="Generale")
    immagine_url = Column(String(500), nullable=False)
    fonte_url = Column(String(500), nullable=True)
    data_pubblicazione = Column(Date, nullable=False, default=date.today)


# Definisce il modello ORM per la tabella delle gare.
class Gara(Base):

    __tablename__ = "gare"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    descrizione = Column(Text, nullable=True)
    data_gara = Column(Date, nullable=False)
    luogo = Column(String(255), nullable=False)
    categoria = Column(String(80), nullable=False, default="Strada")
    immagine_url = Column(String(500), nullable=True)
    distanza_km = Column(Integer, nullable=True)
    dislivello_m = Column(Integer, nullable=True)
    orario_partenza = Column(String(10), nullable=True)
    is_principale = Column(Boolean, nullable=False, default=False)



# --- FUNZIONI DI INIZIALIZZAZIONE E MIGRAZIONE ---

# Controlla se una colonna esiste gia in una tabella specifica.
def _column_exists(table_name: str, column_name: str) -> bool:
    # Crea un inspector collegato all'engine corrente.
    inspector = inspect(engine)

    # Estrae i nomi delle colonne presenti nella tabella richiesta.
    columns = [c["name"] for c in inspector.get_columns(table_name)]

    # Restituisce True se la colonna richiesta e presente, altrimenti False.
    return column_name in columns


# Aggiorna uno schema esistente aggiungendo eventuali colonne mancanti.
def migrate_existing_schema() -> None:
    # Apre una transazione sul database usando l'engine.
    with engine.begin() as conn:
        # Recupera i nomi di tutte le tabelle esistenti.
        table_names = inspect(engine).get_table_names()

        # Se la tabella `news` esiste gia, controlla che abbia tutte le colonne nuove.
        if "news" in table_names:
            # Se manca `sottotitolo`, la aggiunge.
            if not _column_exists("news", "sottotitolo"):
                conn.execute(text("ALTER TABLE news ADD COLUMN sottotitolo VARCHAR(255)"))

            # Se manca `categoria`, la aggiunge con default "Generale".
            if not _column_exists("news", "categoria"):
                conn.execute(text("ALTER TABLE news ADD COLUMN categoria VARCHAR(80) DEFAULT 'Generale'"))

            # Se manca `fonte_url`, la aggiunge.
            if not _column_exists("news", "fonte_url"):
                conn.execute(text("ALTER TABLE news ADD COLUMN fonte_url VARCHAR(500)"))

            # Se manca `data_pubblicazione`, la aggiunge.
            if not _column_exists("news", "data_pubblicazione"):
                conn.execute(text("ALTER TABLE news ADD COLUMN data_pubblicazione DATE"))

            # Riempie eventuali date mancanti nelle righe vecchie usando la data corrente.
            conn.execute(text("UPDATE news SET data_pubblicazione = CURRENT_DATE WHERE data_pubblicazione IS NULL"))

        # Se la tabella `gare` esiste gia, controlla che abbia tutte le colonne nuove.
        if "gare" in table_names:
            # Scorre l'elenco delle colonne da garantire nello schema storico.
            for col, dtype in [
                ("descrizione", "TEXT"),
                ("data_gara", "DATE"),
                ("categoria", "VARCHAR(80)"),
                ("immagine_url", "VARCHAR(500)"),
                ("distanza_km", "INTEGER"),
                ("dislivello_m", "INTEGER"),
                ("orario_partenza", "VARCHAR(10)"),
                ("is_principale", "BOOLEAN"),
            ]:
                # Se la colonna corrente manca, la aggiunge con ALTER TABLE.
                if not _column_exists("gare", col):
                    conn.execute(text(f"ALTER TABLE gare ADD COLUMN {col} {dtype}"))


# Crea le tabelle mancanti e poi applica le migrazioni compatibili agli schemi gia esistenti.
def init_db() -> None:
    # Crea le tabelle definite dai modelli se non esistono ancora.
    Base.metadata.create_all(bind=engine)

    # Applica eventuali aggiornamenti di schema su database gia creati in precedenza.
    migrate_existing_schema()

# Esegue questo blocco solo se il file viene lanciato direttamente da terminale.
if __name__ == "__main__":
    init_db()
    print("Schema DB creato/aggiornato con successo.")