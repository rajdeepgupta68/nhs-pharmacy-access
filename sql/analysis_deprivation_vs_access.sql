-- Analysis: Deprivation vs Pharmacy Access
-- Question: Do more deprived areas have fewer pharmacies?

-- 1. Deprivation bands summary
SELECT
    CASE
        WHEN imd_avg_score > 30 THEN 'High Deprivation'
        WHEN imd_avg_score > 20 THEN 'Medium Deprivation'
        ELSE 'Low Deprivation'
    END AS deprivation_band,
    COUNT(*) AS local_authority_count,
    ROUND(AVG(pharmacies_per_100k), 2) AS avg_pharmacies_per_100k,
    ROUND(AVG(imd_avg_score), 2) AS avg_deprivation_score,
    ROUND(AVG(total_population), 0) AS avg_population
FROM pharmacy_deprivation
WHERE pharmacies_per_100k > 0
GROUP BY deprivation_band
ORDER BY avg_deprivation_score DESC;

-- 2. Top 10 most deprived areas and their pharmacy access
SELECT
    lad_name,
    ROUND(imd_avg_score, 2) AS deprivation_score,
    ROUND(pharmacies_per_100k, 2) AS pharmacies_per_100k,
    pharmacy_count,
    total_population
FROM pharmacy_deprivation
WHERE pharmacies_per_100k > 0
ORDER BY imd_avg_score DESC
LIMIT 10;

-- 3. Bottom 10 least deprived areas
SELECT
    lad_name,
    ROUND(imd_avg_score, 2) AS deprivation_score,
    ROUND(pharmacies_per_100k, 2) AS pharmacies_per_100k,
    pharmacy_count,
    total_population
FROM pharmacy_deprivation
WHERE pharmacies_per_100k > 0
ORDER BY imd_avg_score ASC
LIMIT 10;

-- 4. Correlation check
SELECT
    ROUND(CORR(imd_avg_score, pharmacies_per_100k), 4) AS correlation_deprivation_vs_pharmacy_density
FROM pharmacy_deprivation
WHERE pharmacies_per_100k > 0;