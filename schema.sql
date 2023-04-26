CREATE TABLE domains(
	id SERIAL PRIMARY KEY,
	url VARCHAR(2048) NOT NULL UNIQUE,
	domain TEXT NOT NULL,
	depth INTEGER NOT NULL DEFAULT 5,
	weight FLOAT NOT NULL DEFAULT 1,
	current_rank FLOAT NOT NULL DEFAULT 1,

	last_updated TIMESTAMP
);

CREATE TABLE search(
	url VARCHAR(2048) NOT NULL UNIQUE,
	domain INTEGER NOT NULL,

	title VARCHAR(128) NOT NULL,
	body TEXT NOT NULL,
	last_updated TIMESTAMP,

	search_index TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))) STORED,

	FOREIGN KEY(domain) REFERENCES domains(id) ON DELETE CASCADE
);

CREATE TABLE links(
	src_domain INTEGER NOT NULL,
	src VARCHAR(2048) NOT NULL,
	dst_domain VARCHAR(2048) NOT NULL,
	dst VARCHAR(2048) NOT NULL,

	UNIQUE(src, dst),
	FOREIGN KEY(src_domain) REFERENCES domains(id) ON DELETE CASCADE,
	FOREIGN KEY(src) REFERENCES search(url) ON DELETE CASCADE
);

CREATE INDEX search_idx ON search USING GIN (search_index);
