SELECT name, total_mb, free_mb,
       ROUND((1 - free_mb / total_mb) * 100, 2) pct_used
FROM v$asm_diskgroup