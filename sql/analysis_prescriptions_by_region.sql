-- Analysis: Prescription Volumes by Region
-- Question: Which regions have highest prescription burden?

-- 1. Regional prescription summary
SELECT
    region_name,
    SUM(total_items) AS total_prescriptions,
    ROUND(SUM(total_nic), 2) AS total_cost_gbp,
    ROUND(SUM(total_nic) / SUM(total_items), 4) AS cost_per_item_gbp,
    COUNT(DISTINCT bnf_chapter) AS drug_categories
FROM prescriptions_by_region_bnf
GROUP BY region_name
ORDER BY total_prescriptions DESC;

-- 2. Top 5 drug categories nationally
SELECT
    bnf_chapter,
    SUM(total_items) AS total_prescriptions,
    ROUND(SUM(total_nic), 2) AS total_cost_gbp,
    ROUND(SUM(total_items) * 100.0 / SUM(SUM(total_items)) OVER (), 2) AS pct_of_total
FROM prescriptions_by_region_bnf
GROUP BY bnf_chapter
ORDER BY total_prescriptions DESC
LIMIT 5;

-- 3. Most expensive drug categories per item
SELECT
    bnf_chapter,
    SUM(total_items) AS total_prescriptions,
    ROUND(SUM(total_nic), 2) AS total_cost_gbp,
    ROUND(SUM(total_nic) / SUM(total_items), 4) AS cost_per_item_gbp
FROM prescriptions_by_region_bnf
GROUP BY bnf_chapter
ORDER BY cost_per_item_gbp DESC
LIMIT 10;

-- 4. London vs North East And Yorkshire comparison
SELECT
    region_name,
    SUM(total_items) AS total_prescriptions,
    ROUND(SUM(total_nic), 2) AS total_cost_gbp,
    ROUND(SUM(total_nic) / SUM(total_items), 4) AS cost_per_item_gbp
FROM prescriptions_by_region_bnf
WHERE region_name IN ('London', 'North East And Yorkshire')
GROUP BY region_name
ORDER BY total_prescriptions DESC;