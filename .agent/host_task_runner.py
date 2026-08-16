#!/usr/bin/env python3
"""Fail-closed host supervisor for governed Codex tasks."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

TASK_PATH = Path('.agent/CURRENT_TASK.json')
TASK_MD_PATH = Path('.agent/CURRENT_TASK.md')
ARCHITECT_PATHS = frozenset({str(TASK_PATH), str(TASK_MD_PATH)})
STATE_NAME = 'host-task-runner-state.json'
LOCK_NAME = 'host-task-runner.lock'
FIXED_PROMPT = (
    'Read AGENTS.md, .agent/CURRENT_TASK.json and .agent/CURRENT_TASK.md. '
    'Execute the current task exactly as authorized. Do not expand scope. '
    'Return the required final report and STOP.'
)
REQUIRED_FIELDS: dict[str, type] = {
    'schema_version': int,
    'task_id': str,
    'mode': str,
    'status': str,
    'branch': str,
    'executor': str,
    'baseline_sha': str,
    'allowed_paths': list,
    'capabilities': dict,
    'host_capabilities': dict,
    'max_commits': int,
    'require_clean_start': bool,
    'require_clean_finish': bool,
    'architect_acceptance_required': bool,
}
REQUIRED_CAPABILITIES = {
    'source_write', 'agent_exec', 'network_git', 'kubernetes', 'deployment',
    'database_write', 'runtime_write', 'secret_access', 'package_install',
}
REQUIRED_HOST_CAPABILITIES = {'sync', 'commit', 'push'}


class RunnerError(RuntimeError):
    pass


CommandRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]


def execute_command(argv: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(argv), cwd=cwd, check=True, capture_output=True, text=True)


def run_capture(argv: Sequence[str], cwd: Path, run: CommandRunner = execute_command) -> str:
    return run(argv, cwd).stdout.strip()


def resolve_repo_root(start: Path, run: CommandRunner = execute_command) -> Path:
    return Path(run_capture(['git', 'rev-parse', '--show-toplevel'], start, run)).resolve()


def resolve_git_path(repo: Path, name: str, run: CommandRunner = execute_command) -> Path:
    raw = run_capture(['git', 'rev-parse', '--git-path', name], repo, run)
    path = Path(raw)
    return (path if path.is_absolute() else repo / path).resolve()


def resolve_default_lock_path(repo: Path, run: CommandRunner = execute_command) -> Path:
    return resolve_git_path(repo, LOCK_NAME, run)


def resolve_state_path(repo: Path, run: CommandRunner = execute_command) -> Path:
    return resolve_git_path(repo, STATE_NAME, run)


def validate_task(task: Any) -> dict[str, Any]:
    if not isinstance(task, dict):
        raise RunnerError('task JSON must contain an object')
    for name, expected in REQUIRED_FIELDS.items():
        if name not in task or type(task[name]) is not expected:
            raise RunnerError(f'missing or invalid field: {name}')
    if task['schema_version'] != 1:
        raise RunnerError('unsupported schema_version')
    if task['status'] != 'ACTIVE':
        raise RunnerError('task status is not ACTIVE')
    if task['executor'] not in ('codex', 'hermes'):
        raise RunnerError("executor must be exactly 'codex' or 'hermes'")
    if not task['task_id'] or not task['branch'] or not task['baseline_sha']:
        raise RunnerError('task_id, branch and baseline_sha must be non-empty')
    paths = task['allowed_paths']
    if any(not isinstance(value, str) or not value for value in paths):
        raise RunnerError('allowed_paths must contain non-empty strings')
    if len(paths) != len(set(paths)):
        raise RunnerError('allowed_paths contains duplicates')
    capabilities = task['capabilities']
    for name in REQUIRED_CAPABILITIES:
        if name not in capabilities or type(capabilities[name]) is not bool:
            raise RunnerError(f'missing or invalid capability: {name}')
    host = task['host_capabilities']
    for name in REQUIRED_HOST_CAPABILITIES:
        if name not in host or type(host[name]) is not bool:
            raise RunnerError(f'missing or invalid host capability: {name}')
    validation = task.get('validation_commands', [])
    if not isinstance(validation, list):
        raise RunnerError('validation_commands must be a list')
    for command in validation:
        if (not isinstance(command, list) or not command or
                any(not isinstance(arg, str) or not arg for arg in command)):
            raise RunnerError('each validation command must be a non-empty argv list')
    message = task.get('commit_message')
    if message is not None and (not isinstance(message, str) or not message.strip()):
        raise RunnerError('commit_message must be a non-empty string when present')
    return task


def load_task(path: Path) -> dict[str, Any]:
    try:
        return validate_task(json.loads(path.read_text(encoding='utf-8')))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunnerError(f'cannot load task: {exc}') from exc


def task_fingerprint(repo: Path) -> str:
    digest = hashlib.sha256()
    for rel in (TASK_PATH, TASK_MD_PATH):
        try:
            data = (repo / rel).read_bytes()
        except OSError as exc:
            raise RunnerError(f'cannot fingerprint task control file {rel}: {exc}') from exc
        digest.update(str(rel).encode())
        digest.update(b'\0')
        digest.update(data)
        digest.update(b'\0')
    return digest.hexdigest()


def require_branch(repo: Path, expected: str, run: CommandRunner = execute_command) -> str:
    actual = run_capture(['git', 'branch', '--show-current'], repo, run)
    if actual != expected:
        raise RunnerError(f'branch mismatch: expected {expected}, got {actual}')
    return actual


def status_porcelain(repo: Path, run: CommandRunner = execute_command) -> str:
    return run(['git', 'status', '--porcelain=v1', '-z', '--untracked-files=all'], repo).stdout


def require_clean_worktree(repo: Path, run: CommandRunner = execute_command) -> None:
    if status_porcelain(repo, run):
        raise RunnerError('worktree is not clean')


def verify_baseline_ancestor(repo: Path, baseline: str, head: str,
                             run: CommandRunner = execute_command) -> None:
    try:
        run(['git', 'rev-parse', '--verify', f'{baseline}^{{commit}}'], repo)
        run(['git', 'merge-base', '--is-ancestor', baseline, head], repo)
    except subprocess.CalledProcessError as exc:
        raise RunnerError('baseline is missing or is not an ancestor of launch HEAD') from exc


def committed_handoff_paths(repo: Path, baseline: str, head: str,
                            allowed_paths: Iterable[str],
                            run: CommandRunner = execute_command) -> list[str]:
    output = run(['git', 'diff', '--name-only', '-z', f'{baseline}..{head}'], repo).stdout
    paths = sorted(filter(None, output.split('\0')))
    allowed = set(allowed_paths)
    unexpected = sorted(set(paths) - ARCHITECT_PATHS - allowed)
    if unexpected:
        raise RunnerError(f'unexpected committed handoff paths: {unexpected}')
    return paths


HERMES_OBSERVER = 'hermes_observer.py'


def build_codex_argv(prompt: str = FIXED_PROMPT) -> list[str]:
    return [os.environ.get('CODEX_BIN', 'codex'), '--ask-for-approval', 'never',
            'exec', '--sandbox', 'workspace-write', prompt]


def build_hermes_argv() -> list[str]:
    """Hermes dispatch: local argv-safe H2 socket-bridge client, never a direct CLI."""
    observer_bin = os.environ.get('HERMES_OBSERVER_BIN', '').strip()
    if observer_bin:
        return [observer_bin]
    return [sys.executable, str(Path(__file__).resolve().parent / HERMES_OBSERVER)]


def build_executor_argv(task: dict[str, Any]) -> list[str]:
    executor = task.get('executor')
    if executor == 'codex':
        return build_codex_argv()
    if executor == 'hermes':
        return build_hermes_argv()
    raise RunnerError(f'invalid executor: {executor!r}')


def parse_porcelain_z(output: str) -> list[str]:
    entries = output.split('\0')
    paths: list[str] = []
    index = 0
    while index < len(entries) and entries[index]:
        entry = entries[index]
        if len(entry) < 4 or entry[2] != ' ':
            raise RunnerError('invalid Git porcelain output')
        status, path = entry[:2], entry[3:]
        paths.append(path)
        if 'R' in status or 'C' in status:
            index += 1
            if index >= len(entries) or not entries[index]:
                raise RunnerError('invalid rename/copy porcelain output')
            paths.append(entries[index])
        index += 1
    return sorted(set(paths))


def changed_worktree_paths(repo: Path, run: CommandRunner = execute_command) -> list[str]:
    return parse_porcelain_z(status_porcelain(repo, run))


def validate_changed_paths(changed: Iterable[str], task: dict[str, Any]) -> list[str]:
    paths = sorted(set(changed))
    unexpected = sorted(set(paths) - set(task['allowed_paths']))
    if unexpected:
        raise RunnerError(f'changed paths outside task allowlist: {unexpected}')
    tampered = sorted(set(paths) & ARCHITECT_PATHS)
    if tampered:
        raise RunnerError(f'Architect-managed task files modified by executor: {tampered}')
    if paths and not task['capabilities']['source_write']:
        raise RunnerError('source_write=false but executor changed files')
    return paths


def implementation_paths(changed: Iterable[str], task: dict[str, Any]) -> list[str]:
    return validate_changed_paths(changed, task)


def require_agent_capability(task: dict[str, Any], name: str) -> None:
    if not task['capabilities'].get(name, False):
        raise RunnerError(f'agent capability prohibits action: {name}')


def require_host_capability(task: dict[str, Any], name: str) -> None:
    if not task['host_capabilities'].get(name, False):
        raise RunnerError(f'host capability prohibits action: {name}')


def read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunnerError(f'cannot read runner state: {exc}') from exc
    if not isinstance(data, dict):
        raise RunnerError('runner state must be a JSON object')
    return data


def write_state(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(data, sort_keys=True) + '\n', encoding='utf-8')
    os.replace(tmp, path)


def make_summary(task_id: str, start_head: str, changed_paths: Iterable[str],
                 implementation: Iterable[str], result: str, message: str = '',
                 commit_sha: str = '', executor: str = '') -> dict[str, Any]:
    return {
        'changed_paths': sorted(set(changed_paths)),
        'commit_sha': commit_sha,
        'implementation_paths': sorted(set(implementation)),
        'message': message,
        'result': result,
        'start_head': start_head,
        'task_id': task_id,
        'executor': executor,
    }


class InterProcessLock(AbstractContextManager['InterProcessLock']):
    def __init__(self, path: Path):
        self.path = path
        self._fd: int | None = None

    def __enter__(self) -> 'InterProcessLock':
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(self._fd)
            self._fd = None
            raise RunnerError(f'runner lock is already held: {self.path}') from exc
        os.ftruncate(self._fd, 0)
        os.write(self._fd, f'{os.getpid()}\n'.encode('ascii'))
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._fd is not None:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None


def fetch_remote(repo: Path, branch: str, run: CommandRunner = execute_command) -> str:
    run(['git', 'fetch', '--prune', 'origin', branch], repo)
    return run_capture(['git', 'rev-parse', f'origin/{branch}'], repo, run)


def fast_forward_to_remote(repo: Path, branch: str,
                           run: CommandRunner = execute_command) -> str:
    require_clean_worktree(repo, run)
    local = run_capture(['git', 'rev-parse', 'HEAD'], repo, run)
    remote = fetch_remote(repo, branch, run)
    if local != remote:
        try:
            run(['git', 'merge-base', '--is-ancestor', local, remote], repo)
        except subprocess.CalledProcessError as exc:
            raise RunnerError('local branch is not a fast-forward ancestor of remote') from exc
        run(['git', 'merge', '--ff-only', f'origin/{branch}'], repo)
    return run_capture(['git', 'rev-parse', 'HEAD'], repo, run)


def run_validations(repo: Path, task: dict[str, Any],
                    run: CommandRunner = execute_command) -> None:
    run(['python3', '.agent/validate_task_scope.py'], repo)
    run(['git', 'diff', '--check'], repo)
    for argv in task.get('validation_commands', []):
        run(argv, repo)


def restore_after_failed_executor(repo: Path, start_head: str,
                                  run: CommandRunner = execute_command) -> None:
    run(['git', 'reset', '--hard', start_head], repo)
    run(['git', 'clean', '-fd'], repo)


def stage_commit_push(repo: Path, task: dict[str, Any], start_head: str,
                      paths: list[str], run: CommandRunner = execute_command) -> str:
    if not paths:
        return ''
    require_host_capability(task, 'commit')
    require_host_capability(task, 'push')
    if task['max_commits'] < 1:
        raise RunnerError('max_commits prohibits host commit')
    remote = fetch_remote(repo, task['branch'], run)
    if remote != start_head:
        raise RunnerError(f'remote moved during execution: expected {start_head}, got {remote}')
    run(['git', 'add', '--', *paths], repo)
    staged = run(['git', 'diff', '--cached', '--name-only', '-z'], repo).stdout
    staged_paths = sorted(filter(None, staged.split('\0')))
    if staged_paths != sorted(paths):
        raise RunnerError(f'staged paths mismatch: {staged_paths}')
    message = task.get('commit_message', f"agent: {task['task_id']}")
    run(['git', 'commit', '-m', message], repo)
    commit_sha = run_capture(['git', 'rev-parse', 'HEAD'], repo, run)
    try:
        run(['git', 'push', 'origin', f"HEAD:{task['branch']}"], repo)
    except subprocess.CalledProcessError:
        run(['git', 'reset', '--hard', start_head], repo)
        raise
    return commit_sha


def execute_task(repo: Path, task: dict[str, Any], start_head: str,
                 run: CommandRunner = execute_command) -> dict[str, Any]:
    require_agent_capability(task, 'agent_exec')
    try:
        run(build_executor_argv(task), repo)
        changed = changed_worktree_paths(repo, run)
        implementation = implementation_paths(changed, task)
        run_validations(repo, task, run)
        final_changed = changed_worktree_paths(repo, run)
        final_implementation = implementation_paths(final_changed, task)
        if final_implementation != implementation:
            implementation = final_implementation
            changed = final_changed
        commit_sha = stage_commit_push(repo, task, start_head, implementation, run)
        require_clean_worktree(repo, run)
        return make_summary(task['task_id'], start_head, changed, implementation,
                            'PASS', commit_sha=commit_sha, executor=task['executor'])
    except (RunnerError, subprocess.CalledProcessError) as exc:
        try:
            restore_after_failed_executor(repo, start_head, run)
        except Exception as restore_exc:
            raise RunnerError(f'task failed: {exc}; restore also failed: {restore_exc}') from restore_exc
        raise RunnerError(str(exc)) from exc


def run_once(repo: Path, run: CommandRunner = execute_command,
             execute_agent: bool = True) -> dict[str, Any]:
    repo = resolve_repo_root(repo, run)
    lock_path = resolve_default_lock_path(repo, run)
    state_path = resolve_state_path(repo, run)
    with InterProcessLock(lock_path):
        require_clean_worktree(repo, run)
        branch = run_capture(['git', 'branch', '--show-current'], repo, run)
        if branch != 'aither-v2':
            raise RunnerError(f'runner only operates on aither-v2, got {branch}')
        start_head = fast_forward_to_remote(repo, branch, run)
        task = load_task(repo / TASK_PATH)
        require_branch(repo, task['branch'], run)
        require_host_capability(task, 'sync')
        executor = task['executor']
        fingerprint = task_fingerprint(repo)
        state = read_state(state_path)
        verify_baseline_ancestor(repo, task['baseline_sha'], start_head, run)
        committed_handoff_paths(repo, task['baseline_sha'], start_head,
                                task['allowed_paths'], run)
        if state.get('last_success_fingerprint') == fingerprint:
            return make_summary(task['task_id'], start_head, [], [], 'IDLE',
                                'task already completed successfully',
                                state.get('last_commit_sha', ''), executor=executor)
        if state.get('last_attempt_fingerprint') == fingerprint and \
                state.get('last_attempt_result') in ('BLOCKED', 'FAIL'):
            return make_summary(task['task_id'], start_head, [], [], 'SUPPRESSED',
                                'executor retry suppressed pending Architect task change',
                                executor=executor)
        if not execute_agent:
            return make_summary(task['task_id'], start_head, [], [], 'PASS', 'dry-run',
                                executor=executor)
        try:
            result = execute_task(repo, task, start_head, run)
        except (RunnerError, subprocess.CalledProcessError) as exc:
            write_state(state_path, {
                'last_commit_sha': state.get('last_commit_sha', ''),
                'last_success_fingerprint': state.get('last_success_fingerprint', ''),
                'last_task_id': task['task_id'],
                'last_executor': executor,
                'last_attempt_fingerprint': fingerprint,
                'last_attempt_result': 'BLOCKED',
            })
            return make_summary(task['task_id'], start_head, [], [], 'BLOCKED',
                                str(exc), executor=executor)
        write_state(state_path, {
            'last_commit_sha': result['commit_sha'],
            'last_success_fingerprint': fingerprint,
            'last_task_id': task['task_id'],
            'last_executor': executor,
            'last_attempt_fingerprint': fingerprint,
            'last_attempt_result': 'PASS',
        })
        return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--run-once', action='store_true')
    args = parser.parse_args(argv)
    try:
        summary = run_once(args.repo, execute_agent=args.run_once)
    except (RunnerError, subprocess.CalledProcessError) as exc:
        summary = make_summary('', '', [], [], 'BLOCKED', str(exc))
    print(json.dumps(summary, sort_keys=True, separators=(',', ':')))
    return 0 if summary['result'] in {'PASS', 'IDLE', 'SUPPRESSED'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
