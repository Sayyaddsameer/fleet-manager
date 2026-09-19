#!/bin/bash

# Collect hostname
HOSTNAME_VAL=$(hostname)

# Collect uptime in seconds from /proc/uptime (first field, truncated to integer)
UPTIME_RAW=$(cat /proc/uptime | awk '{print $1}')
UPTIME_SECONDS=$(printf "%.0f" "$UPTIME_RAW")

# Collect CPU usage percentage
# Read two snapshots of /proc/stat one second apart and compute the delta
read_cpu() {
    awk '/^cpu / {print $2+$3+$4+$5+$6+$7+$8, $5}' /proc/stat
}

CPU1=$(read_cpu)
sleep 1
CPU2=$(read_cpu)

TOTAL1=$(echo "$CPU1" | awk '{print $1}')
IDLE1=$(echo "$CPU1" | awk '{print $2}')
TOTAL2=$(echo "$CPU2" | awk '{print $1}')
IDLE2=$(echo "$CPU2" | awk '{print $2}')

TOTAL_DELTA=$((TOTAL2 - TOTAL1))
IDLE_DELTA=$((IDLE2 - IDLE1))

if [ "$TOTAL_DELTA" -gt 0 ]; then
    CPU_USAGE=$(awk "BEGIN {printf \"%.1f\", (1 - $IDLE_DELTA / $TOTAL_DELTA) * 100}")
else
    CPU_USAGE=0.0
fi

# Collect free memory in MB
MEMORY_FREE_MB=$(free -m | awk '/^Mem:/ {print $7}')
# Fallback if available column is missing (older systems)
if [ -z "$MEMORY_FREE_MB" ]; then
    MEMORY_FREE_MB=$(free -m | awk '/^Mem:/ {print $4}')
fi

# Collect free disk space on root partition in GB
DISK_FREE_ROOT_GB=$(df -BG / | awk 'NR==2 {gsub("G","",$4); print $4}')

# Output a single line of JSON
printf '{"os":"linux","hostname":"%s","uptime_seconds":%d,"cpu_usage_percent":%s,"memory_free_mb":%d,"disk_free_root_gb":%d}\n' \
    "$HOSTNAME_VAL" "$UPTIME_SECONDS" "$CPU_USAGE" "$MEMORY_FREE_MB" "$DISK_FREE_ROOT_GB"
