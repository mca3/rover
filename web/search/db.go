package main

import (
	"context"

	"github.com/jackc/pgx/v5/pgxpool"
)

type result struct {
	Url string
	Title string
	Snip string
	Rank float64
}

const pageAmount = 20

var pg *pgxpool.Pool

func initDatabase(pgurl string) error {
	var err error

	pg, err = pgxpool.New(context.TODO(), pgurl)
	return err
}

func closeDatabase() {
	pg.Close()
}

func searchDatabase(ctx context.Context, query string, page int) ([]result, error) {
	rows, err := pg.Query(ctx, `
		SELECT
			url,
			title,
			ts_headline(body, query),
			ts_rank_cd(search_index, query) AS rank
		FROM
			search,
			websearch_to_tsquery($1) query
		WHERE query @@ search_index
		ORDER BY rank DESC
		OFFSET $2
	`, query, page*pageAmount)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	ret := make([]result, 0)

	for rows.Next() {
		r := result{}
		if err := rows.Scan(&r.Url, &r.Title, &r.Snip, &r.Rank); err != nil {
			return nil, err
		}
		ret = append(ret, r)

		if page >= 0 && len(ret) == pageAmount {
			break
		}
	}

	return ret, nil
}
