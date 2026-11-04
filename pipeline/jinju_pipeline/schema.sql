-- places.db schema (contract with the backend). schema_version = 1
CREATE TABLE places (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    title_norm TEXT,
    summary TEXT,
    overview TEXT,
    addr TEXT,
    lat REAL,
    lng REAL,
    geo_status TEXT,
    phone TEXT,
    homepage TEXT,
    hours TEXT,
    closed_days TEXT,
    fee TEXT,
    parking TEXT,
    menu TEXT,
    start_date TEXT,
    end_date TEXT,
    date_undecided INTEGER NOT NULL DEFAULT 0,
    date_year INTEGER,
    hero_image TEXT,
    is_collection INTEGER NOT NULL DEFAULT 0,
    jinju8_rank INTEGER,
    tags TEXT NOT NULL DEFAULT '[]',            -- JSON array
    venue_place_ids TEXT NOT NULL DEFAULT '[]', -- JSON array (festival rows)
    updated_at TEXT
);
CREATE INDEX idx_places_category ON places(category);
CREATE INDEX idx_places_lat_lng ON places(lat, lng);

CREATE TABLE place_images (
    place_id TEXT NOT NULL,
    url TEXT NOT NULL,
    source TEXT,
    license TEXT,
    sort INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_place_images_place ON place_images(place_id, sort);

CREATE TABLE place_sources (
    place_id TEXT NOT NULL,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_url TEXT,
    fetched_at TEXT,
    raw_json TEXT
);
CREATE INDEX idx_place_sources_place ON place_sources(place_id);

CREATE TABLE place_aliases (
    old_id TEXT PRIMARY KEY,
    new_id TEXT NOT NULL
);

CREATE TABLE badges (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    description TEXT,
    required INTEGER NOT NULL DEFAULT 0,
    rule_json TEXT NOT NULL  -- {"eligible_place_ids": [...], "festival_windows": [...]}
);

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE id_order (
    place_id TEXT PRIMARY KEY,
    issued_seq INTEGER NOT NULL
);
