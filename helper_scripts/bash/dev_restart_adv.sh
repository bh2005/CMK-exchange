#!/bin/bash
# =============================================================================
# Checkmk Advanced Development Restart Script
# =============================================================================
# Comprehensive restart script for Checkmk plugin development with:
# - Selective service restarts
# - Python cache cleaning
# - Syntax validation
# - Log monitoring
# - Auto-discovery option
# =============================================================================

set -euo pipefail

# ----- Configuration ----------------------------------------------------------
QUICK_SERVICES=("automation-helper" "ui-job-scheduler" "apache")
SITE_NAME=$(omd config show CORE 2>/dev/null | head -1 || echo "unknown")

# Flags
FULL_MODE=false
CLEAN_CACHE=false
VALIDATE=false
TAIL_LOG=false
DISCOVER_HOST=""
VERBOSE=false

# ----- Parse arguments --------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --full|-f)
      FULL_MODE=true
      shift
      ;;
    --clean|-c)
      CLEAN_CACHE=true
      shift
      ;;
    --validate|-v)
      VALIDATE=true
      shift
      ;;
    --log|-l)
      TAIL_LOG=true
      shift
      ;;
    --discover)
      DISCOVER_HOST="$2"
      shift 2
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    --help|-h)
      cat <<EOF
Usage: $0 [OPTIONS]

Restart Checkmk development environment with various options.

Options:
  --full, -f           Full OMD restart (all services)
  --clean, -c          Clean Python cache before restart
  --validate, -v       Validate Python syntax before restart
  --log, -l            Tail web.log after restart
  --discover <HOST>    Run service discovery on HOST after restart
  --verbose            Show detailed output
  --help, -h           Show this help

Examples:
  $0                           # Quick restart
  $0 --clean                   # Clean + restart
  $0 --full --clean            # Full restart with cache clean
  $0 -c -v                     # Clean + validate + restart
  $0 --clean --discover myhost # Clean + restart + discovery
  $0 --log                     # Restart + monitor logs

Development Workflow:
  1. Make code changes
  2. Run: $0 --clean --validate
  3. Test in GUI or with: cmk -I <hostname>
  4. Check logs with: tail -f ~/var/log/web.log
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# ----- Helper functions -------------------------------------------------------
log_step() {
  echo "==> $1"
}

log_success() {
  echo "    ✓ $1"
}

log_warn() {
  echo "    ⚠ Warning: $1" >&2
}

log_error() {
  echo "    ✗ Error: $1" >&2
}

# ----- Validate Python syntax (optional) --------------------------------------
if [[ "$VALIDATE" == true ]]; then
  log_step "Validating Python syntax..."
  
  ERROR_COUNT=0
  
  # Check all Python files in cmk_addons
  while IFS= read -r -d '' pyfile; do
    if ! python3 -m py_compile "$pyfile" 2>/dev/null; then
      log_error "Syntax error in: $pyfile"
      ERROR_COUNT=$((ERROR_COUNT + 1))
    elif [[ "$VERBOSE" == true ]]; then
      log_success "OK: $pyfile"
    fi
  done < <(find ~/local/lib/python3/cmk_addons -name "*.py" -print0 2>/dev/null)
  
  if [[ $ERROR_COUNT -gt 0 ]]; then
    log_error "Found $ERROR_COUNT syntax error(s). Fix them before restarting!"
    exit 1
  fi
  
  log_success "All Python files validated"
fi

# ----- Clean Python cache (optional) ------------------------------------------
if [[ "$CLEAN_CACHE" == true ]]; then
  log_step "Cleaning Python cache..."
  
  CACHE_DIRS=0
  CACHE_FILES=0
  
  # Count and remove __pycache__ directories
  while IFS= read -r dir; do
    CACHE_DIRS=$((CACHE_DIRS + 1))
  done < <(find ~/local/lib/python3/cmk_addons -type d -name "__pycache__" 2>/dev/null)
  
  find ~/local/lib/python3/cmk_addons -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
  
  # Count and remove .pyc files
  while IFS= read -r file; do
    CACHE_FILES=$((CACHE_FILES + 1))
  done < <(find ~/local/lib/python3/cmk_addons -name "*.pyc" 2>/dev/null)
  
  find ~/local/lib/python3/cmk_addons -name "*.pyc" -delete 2>/dev/null || true
  
  if [[ "$VERBOSE" == true ]]; then
    log_success "Removed $CACHE_DIRS cache directories and $CACHE_FILES .pyc files"
  else
    log_success "Cache cleaned"
  fi
fi

# ----- Restart services -------------------------------------------------------
if [[ "$FULL_MODE" == true ]]; then
  log_step "Full OMD restart..."
  
  if [[ "$VERBOSE" == true ]]; then
    omd stop
    sleep 1
    omd start
  else
    omd stop >/dev/null 2>&1
    sleep 1
    omd start >/dev/null 2>&1
  fi
  
  log_success "All services restarted"
else
  log_step "Quick restart (GUI services only)..."
  
  for service in "${QUICK_SERVICES[@]}"; do
    if [[ "$VERBOSE" == true ]]; then
      echo "    Restarting $service..."
    fi
    
    if omd restart "$service" >/dev/null 2>&1; then
      if [[ "$VERBOSE" == true ]]; then
        log_success "$service restarted"
      fi
    else
      log_warn "Could not restart $service (may not be running)"
    fi
  done
  
  log_success "GUI services restarted"
fi

# ----- Reload Checkmk configuration -------------------------------------------
log_step "Reloading Checkmk configuration..."

if [[ "$VERBOSE" == true ]]; then
  cmk -R
else
  cmk -R >/dev/null 2>&1
fi

log_success "Configuration reloaded"

# ----- Run service discovery (optional) ---------------------------------------
if [[ -n "$DISCOVER_HOST" ]]; then
  log_step "Running service discovery on $DISCOVER_HOST..."
  
  if cmk -I "$DISCOVER_HOST" 2>&1 | grep -q "SUCCESS"; then
    log_success "Discovery completed for $DISCOVER_HOST"
  else
    log_warn "Discovery may have failed for $DISCOVER_HOST"
  fi
fi

# ----- Status summary ---------------------------------------------------------
echo ""
echo "========================================="
echo "Development Environment Ready!"
echo "========================================="

[[ "$VALIDATE" == true ]] && echo "✓ Python syntax validated"
[[ "$CLEAN_CACHE" == true ]] && echo "✓ Python cache cleaned"
[[ "$FULL_MODE" == true ]] && echo "✓ All OMD services restarted" || echo "✓ GUI services restarted"
echo "✓ Configuration reloaded"
[[ -n "$DISCOVER_HOST" ]] && echo "✓ Discovery run on $DISCOVER_HOST"

echo ""
echo "Tips:"
echo "  • Check service status: omd status"
echo "  • View web logs: tail -f ~/var/log/web.log"
echo "  • Test check: cmk -vvn <HOSTNAME>"
echo "  • List plugins: cmk --list-checks | grep <name>"

# ----- Tail logs (optional) ---------------------------------------------------
if [[ "$TAIL_LOG" == true ]]; then
  echo ""
  echo "==> Monitoring ~/var/log/web.log (Ctrl+C to stop)..."
  echo ""
  tail -f ~/var/log/web.log
fi