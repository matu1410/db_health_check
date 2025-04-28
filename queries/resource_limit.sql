SELECT resource_name,
       current_utilization,
       limit_value,
       ROUND((current_utilization / limit_value) * 100, 2) AS pct_utilization
FROM v$resource_limit
WHERE resource_name IN ('processes', 'sessions')