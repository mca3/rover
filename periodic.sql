-- This file should be run every so often as domain ranks are not updated
-- automatically due to it being costly to do so on every insert or update.

WITH rank AS (
	SELECT
		dst_domain,
		COUNT(DISTINCT src_domain) AS rank
	FROM links
	GROUP BY dst_domain
)
UPDATE domains
SET current_rank = rank.rank
FROM rank
WHERE rank.dst_domain = domains.domain;
