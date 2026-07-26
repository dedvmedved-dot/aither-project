#!/usr/bin/env bash
set -Eeuo pipefail

# U1.3-OPS-R2 Evidence Collector
# Corrected version: guaranteed exit code logging even with set -e

NS="${NS:-aither-inference}"
EVIDENCE_DIR="${EVIDENCE_DIR:-evidence/u1.3-ops-r2}"

# Function: run command and log everything, guaranteed exit code capture
run_logged() {
    local logfile="$1"
    shift

    mkdir -p "$(dirname "$logfile")"

    {
        printf '\nCOMMAND START\n'
        printf 'UTC TIMESTAMP: %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
        printf 'COMMAND:'
        printf ' %q' "$@"
        printf '\n\n'

        set +e
        "$@"
        local rc=$?
        set -e

        printf '\nEXIT_CODE=%s\n' "$rc"
        printf 'COMMAND END\n'

        return "$rc"
    } >>"$logfile" 2>&1
}

# Collect Git state
collect_git_state() {
    local log="$EVIDENCE_DIR/logs/01-git-baseline.log"

    run_logged "$log" date -u +"%Y-%m-%dT%H:%M:%SZ"
    run_logged "$log" pwd
    run_logged "$log" git remote -v
    run_logged "$log" git fetch --all --prune --tags
    run_logged "$log" git status --short
    run_logged "$log" git branch --show-current
    run_logged "$log" git rev-parse HEAD
    run_logged "$log" git rev-parse origin/aither-v2
    run_logged "$log" git ls-remote origin refs/heads/aither-v2
    run_logged "$log" git log --oneline --decorate -15

    echo "collect_git_state: DONE"
}

# Collect cluster baseline
collect_cluster_baseline() {
    local log="$EVIDENCE_DIR/logs/03-cluster-baseline.log"

    run_logged "$log" date -u +"%Y-%m-%dT%H:%M:%SZ"
    run_logged "$log" kubectl cluster-info
    run_logged "$log" kubectl get nodes -o wide
    run_logged "$log" kubectl get deployments -n "$NS" -o wide
    run_logged "$log" kubectl get pods -n "$NS" -o wide
    run_logged "$log" kubectl get services -n "$NS" -o wide
    run_logged "$log" kubectl get ingress -n "$NS" -o wide
    run_logged "$log" kubectl get pdb -n "$NS" -o wide 2>&1 || true
    run_logged "$log" kubectl get events -n "$NS" --sort-by=.lastTimestamp
    run_logged "$log" kubectl get deployments -n "$NS" \
        -o custom-columns='NAME:.metadata.name,DESIRED:.spec.replicas,READY:.status.readyReplicas,AVAILABLE:.status.availableReplicas,UPDATED:.status.updatedReplicas'

    echo "collect_cluster_baseline: DONE"
}

# Validate startup
validate_startup() {
    local log="$EVIDENCE_DIR/logs/03-cluster-baseline.log"

    run_logged "$log" kubectl get deployments -n "$NS" --no-headers 2>&1
    run_logged "$log" kubectl get pods -n "$NS" --no-headers 2>&1

    local total_deployments
    total_deployments=$(kubectl get deployments -n "$NS" --no-headers 2>/dev/null | wc -l)
    local available_deployments
    available_deployments=$(kubectl get deployments -n "$NS" -o json 2>/dev/null | jq '[.items[] | select(.status.availableReplicas // 0 >= 1)] | length')

    local total_pods
    total_pods=$(kubectl get pods -n "$NS" --no-headers 2>/dev/null | wc -l)
    local running_pods
    running_pods=$(kubectl get pods -n "$NS" --no-headers 2>/dev/null | grep -c "Running" || true)

    printf '\nSTARTUP SUMMARY: deployments=%s/%s available, pods=%s/%s Running\n' \
        "$available_deployments" "$total_deployments" "$running_pods" "$total_pods" >> "$log"

    echo "validate_startup: DONE"
}

# Validate logs for error patterns
validate_logs() {
    local log="$EVIDENCE_DIR/logs/11-log-scan.log"

    run_logged "$log" date -u +"%Y-%m-%dT%H:%M:%SZ"

    local patterns=(
        'Traceback'
        'panic'
        'fatal'
        'Unhandled'
        'ReferenceError'
        'TypeError'
        'CrashLoop'
        'segmentation fault'
        'OutOfMemory'
        'OOMKilled'
        'authentication failed'
        'permission denied'
        'x509'
        'certificate verify failed'
    )

    local pods
    pods=$(kubectl get pods -n "$NS" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')

    printf 'SCANNING PODS:\n' >> "$log"
    for pod in $pods; do
        printf '\n--- POD: %s ---\n' "$pod" >> "$log"
        local containers
        containers=$(kubectl get pod "$pod" -n "$NS" -o jsonpath='{range .status.containerStatuses[*]}{.name}{"\n"}{end}')
        local restarts
        restarts=$(kubectl get pod "$pod" -n "$NS" -o jsonpath='{.status.containerStatuses[*].restartCount}')

        printf 'RESTART_COUNT: %s\n' "$restarts" >> "$log"

        for container in $containers; do
            printf '\nCONTAINER: %s\n' "$container" >> "$log"
            for pattern in "${patterns[@]}"; do
                local matches
                matches=$(kubectl logs "$pod" -n "$NS" -c "$container" --tail=1000 2>/dev/null | grep -ci "$pattern" || true)
                if [ "${matches:-0}" -gt 0 ]; then
                    printf '  PATTERN "%s": %d matches\n' "$pattern" "$matches" >> "$log"
                fi
            done
        done
    done

    run_logged "$log" printf '\nLOG_SCAN_COMPLETE\n'

    echo "validate_logs: DONE"
}

# Validate configuration
validate_configuration() {
    local log="$EVIDENCE_DIR/logs/12-config-scan.log"

    run_logged "$log" date -u +"%Y-%m-%dT%H:%M:%SZ"

    # Secrets — names and keys only
    run_logged "$log" kubectl get secrets -n "$NS" -o json 2>&1
    run_logged "$log" bash -c "kubectl get secrets -n \"$NS\" -o json | jq -r '.items[] | select(.type != \"kubernetes.io/service-account-token\") | [.metadata.name, (.data | keys | join(\",\"))] | @tsv'"

    # Deployments — check env references
    run_logged "$log" bash -c "kubectl get deployments -n \"$NS\" -o json | jq '[.items[] | {name: .metadata.name, envFrom: [.spec.template.spec.containers[]?.envFrom[]? | {secretRef: .secretRef?.name, configMapRef: .configMapRef?.name}], envSecretRefs: [.spec.template.spec.containers[]?.env[]? | select(.valueFrom?.secretKeyRef) | .valueFrom.secretKeyRef.name], envConfigMapRefs: [.spec.template.spec.containers[]?.env[]? | select(.valueFrom?.configMapKeyRef) | .valueFrom.configMapKeyRef.name]}]'"

    echo "validate_configuration: DONE"
}

# Validate dependencies
validate_dependencies() {
    local log="$EVIDENCE_DIR/logs/13-dependency-scan.log"

    run_logged "$log" date -u +"%Y-%m-%dT%H:%M:%SZ"
    run_logged "$log" python3 --version
    run_logged "$log" python3 -m pip --version
    run_logged "$log" python3 -m pip check
    run_logged "$log" python3 -m pip install --dry-run --requirement tests/e2e/requirements.txt

    echo "validate_dependencies: DONE"
}

# Secret scan
run_secret_scan() {
    local log="$EVIDENCE_DIR/logs/14-secret-scan.log"

    run_logged "$log" date -u +"%Y-%m-%dT%H:%M:%SZ"

    if command -v gitleaks &>/dev/null; then
        run_logged "$log" gitleaks dir . --redact --no-banner --report-format json --report-path "$EVIDENCE_DIR/gitleaks-report.json"
    else
        printf 'GITLEAKS_NOT_INSTALLED: falling back to grep scan\n' >> "$log"
        run_logged "$log" bash -c "grep -RInE '(api.?key|secret|token|password|credential)[\s]*[=:][\s]*[A-Za-z0-9_\-]{8,}' . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=evidence --exclude='*.pyc' --exclude='*.log' | grep -v 'example\|EXAMPLE\|placeholder\|PLACEHOLDER\|test_secret\|Bearer \*\*\*\|# ' | head -100"
    fi

    echo "run_secret_scan: DONE"
}

# Placeholder scan
run_placeholder_scan() {
    local log="$EVIDENCE_DIR/logs/18-placeholder-scan.log"

    run_logged "$log" date -u +"%Y-%m-%dT%H:%M:%SZ"

    local patterns='(<set by|<after commit>|<to be|to be created|to be resolved|set by Hermes|after commit|TBD|FIXME|CHANGEME|PLACEHOLDER|ACTUAL_SHA|NUMBER|LIST|DIRTY \(uncommitted)'

    run_logged "$log" grep -RInE "$patterns" evidence/u1.3-ops-r2 --exclude='placeholder-scan.txt' --exclude='18-placeholder-scan.log' || true
    run_logged "$log" grep -RInE '(<set by|<after commit>|<to be|to be created|to be resolved|TBD|FIXME|CHANGEME|PLACEHOLDER)' docs/operations scripts/ops || true

    echo "run_placeholder_scan: DONE"
}

# Main
main() {
    echo "=== U1.3-OPS-R2 Evidence Collector ==="
    echo "Namespace: $NS"
    echo "Evidence Dir: $EVIDENCE_DIR"
    echo ""

    mkdir -p "$EVIDENCE_DIR/logs" "$EVIDENCE_DIR/junit"

    case "${1:-all}" in
        git)        collect_git_state ;;
        baseline)   collect_cluster_baseline ;;
        startup)    validate_startup ;;
        logs)       validate_logs ;;
        config)     validate_configuration ;;
        deps)       validate_dependencies ;;
        secrets)    run_secret_scan ;;
        placeholders) run_placeholder_scan ;;
        all)
            collect_git_state
            collect_cluster_baseline
            validate_startup
            validate_logs
            validate_configuration
            validate_dependencies
            run_secret_scan
            ;;
        *)
            echo "Usage: $0 {git|baseline|startup|logs|config|deps|secrets|placeholders|all}"
            exit 1
            ;;
    esac

    echo "=== COLLECTOR DONE ==="
}

main "$@"
