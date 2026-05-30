-- Analysis: Pharmacy Density across England
-- Question: Where are pharmacies concentrated?

-- 1. Top 10 highest pharmacy density areas
SELECT
    lad_name,
    ROUND(pharmacies_per_100k, 2) AS pharmacies_per_100k,
    pharmacy_count,
    total_population,
    ROUND(imd_avg_score, 2) AS deprivation_score
FROM pharmacy_deprivation
WHERE pharmacies_per_100k > 0
ORDER BY pharmacies_per_100k DESC
LIMIT 10;

-- 2. Bottom 10 lowest pharmacy density areas
SELECT
    lad_name,
    ROUND(pharmacies_per_100k, 2) AS pharmacies_per_100k,
    pharmacy_count,
    total_population,
    ROUND(imd_avg_score, 2) AS deprivation_score
FROM pharmacy_deprivation
WHERE pharmacies_per_100k > 0
ORDER BY pharmacies_per_100k ASC
LIMIT 10;

-- 3. Pharmacy density by population size band
SELECT
    CASE
        WHEN total_population > 500000 THEN 'Large (500k+)'
        WHEN total_population > 200000 THEN 'Medium (200k-500k)'
        WHEN total_population > 100000 THEN 'Small (100k-200k)'
        ELSE 'Very Small (<100k)'
    END AS population_band,
    COUNT(*) AS local_authority_count,
    ROUND(AVG(pharmacies_per_100k), 2) AS avg_pharmacies_per_100k,
    SUM(pharmacy_count) AS total_pharmacies
FROM pharmacy_deprivation
WHERE pharmacies_per_100k > 0
GROUP BY population_band
ORDER BY avg_pharmacies_per_100k DESC;

-- 4. Areas with high deprivation but low pharmacy access
-- These are the areas of genuine concern
SELECT
    lad_name,
    ROUND(imd_avg_score, 2) AS deprivation_score,
    ROUND(pharmacies_per_100k, 2) AS pharmacies_per_100k,
    total_population
FROM pharmacy_deprivation
WHERE imd_avg_score > 25
AND pharmacies_per_100k < 15
AND pharmacies_per_100k > 0
ORDER BY imd_avg_score DESC;