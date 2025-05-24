#!/bin/bash
# OTLP HTTP Interceptor with proper request handling

PORT="${1:-14318}"
FORWARD_HOST="${2:-pi.lan}"
FORWARD_PORT="${3:-4318}"
LOG_FILE="otlp-interceptor-$(date +%Y%m%d-%H%M%S).log"

echo "Starting OTLP HTTP interceptor on port $PORT"
echo "Forwarding to: $FORWARD_HOST:$FORWARD_PORT"
echo "Logging to: $LOG_FILE"
echo ""
echo "Configure Claude Code with:"
echo "  export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:$PORT"
echo "  export OTEL_METRICS_EXPORTER=otlp"
echo ""
echo "Press Ctrl+C to stop"
echo "----------------------------------------"

# Use socat for better HTTP handling
if command -v socat >/dev/null 2>&1; then
    echo "Using socat for HTTP interception..."
    socat -v TCP-LISTEN:$PORT,reuseaddr,fork TCP:$FORWARD_HOST:$FORWARD_PORT 2>&1 | tee "$LOG_FILE"
else
    echo "socat not found, falling back to netcat..."
    echo "Note: This may not handle HTTP properly. Install socat for better results."
    
    # Basic netcat approach - works but may miss some data
    while true; do
        nc -l $PORT | tee -a "$LOG_FILE" | nc $FORWARD_HOST $FORWARD_PORT
    done
fi