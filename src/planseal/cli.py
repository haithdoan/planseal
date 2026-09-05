"""PlanSeal command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .approval import issue_certificate, verify_certificate
from .binding import verify_local_binding
from .crypto import generate_keypair
from .errors import PlanSealError
from .execution import apply_saved_plan
from .inspection import inspect_plan
from .io import read_json, write_json
from .models import Certificate, Evidence


def _actions(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def _load_evidence(path: Path) -> Evidence:
    return Evidence.from_dict(read_json(path, "evidence_read_failed"))


def _load_certificate(path: Path) -> Certificate:
    return Certificate.from_dict(read_json(path, "certificate_read_failed"))


def _repo_relative(repo: Path, value: Path | None, default: str) -> Path:
    candidate = value or Path(default)
    return candidate if candidate.is_absolute() else repo / candidate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="planseal")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    inspect_command = commands.add_parser("inspect", help="create sanitized saved-plan evidence")
    inspect_command.add_argument("plan", type=Path)
    inspect_command.add_argument("--repo", type=Path, default=Path.cwd())
    inspect_command.add_argument("--lockfile", type=Path)
    inspect_command.add_argument(
        "--tool", choices=("auto", "opentofu", "terraform"), default="auto"
    )
    inspect_command.add_argument("--output", type=Path)

    keygen_command = commands.add_parser("keygen", help="create an Ed25519 owner key pair")
    keygen_command.add_argument("--private-key", type=Path, required=True)
    keygen_command.add_argument("--public-key", type=Path, required=True)

    approve_command = commands.add_parser("approve", help="sign exact plan evidence")
    approve_command.add_argument("evidence", type=Path)
    approve_command.add_argument("--private-key", type=Path, required=True)
    approve_command.add_argument("--allow", required=True, help="comma-separated action names")
    approve_command.add_argument(
        "--ttl", type=int, default=300, help="certificate lifetime in seconds"
    )
    approve_command.add_argument("--output", type=Path, required=True)
    approve_command.add_argument("--confirm", help="required evidence digest")

    verify_command = commands.add_parser("verify", help="verify certificate and local binding")
    _add_binding_arguments(verify_command)

    apply_command = commands.add_parser("apply", help="preview or execute the approved saved plan")
    _add_binding_arguments(apply_command)
    apply_command.add_argument("--ledger", type=Path, default=Path(".planseal/executions.db"))
    apply_command.add_argument("--execute", action="store_true")
    return parser


def _add_binding_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--certificate", type=Path, required=True)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--lockfile", type=Path)


def _emit(value: object) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def run(arguments: list[str] | None = None) -> int:
    args = build_parser().parse_args(arguments)
    if args.command == "inspect":
        evidence = inspect_plan(
            args.plan,
            repo=args.repo,
            lockfile=_repo_relative(args.repo, args.lockfile, ".terraform.lock.hcl"),
            tool=args.tool,
        )
        if args.output:
            write_json(args.output, evidence.as_dict())
        _emit({"evidence": evidence.as_dict(), "evidence_digest": evidence.digest})
        return 0
    if args.command == "keygen":
        signer_key_id = generate_keypair(args.private_key, args.public_key)
        _emit({"schema_version": 1, "signer_key_id": signer_key_id})
        return 0
    if args.command == "approve":
        evidence = _load_evidence(args.evidence)
        if args.confirm != evidence.digest:
            raise PlanSealError("approval_confirmation_mismatch")
        certificate = issue_certificate(
            evidence,
            private_key_path=args.private_key,
            approved_actions=_actions(args.allow),
            ttl_seconds=args.ttl,
        )
        write_json(args.output, certificate.as_dict())
        _emit({"schema_version": 1, "certificate_digest": certificate.digest})
        return 0
    evidence = _load_evidence(args.evidence)
    certificate = _load_certificate(args.certificate)
    lockfile = _repo_relative(args.repo, args.lockfile, ".terraform.lock.hcl")
    if args.command == "verify":
        verify_certificate(evidence, certificate, public_key_path=args.public_key)
        verify_local_binding(evidence, plan=args.plan, repo=args.repo, lockfile=lockfile)
        _emit(
            {
                "schema_version": 1,
                "verified": True,
                "evidence_digest": evidence.digest,
                "certificate_digest": certificate.digest,
            }
        )
        return 0
    if args.command == "apply":
        result = apply_saved_plan(
            evidence,
            certificate,
            public_key=args.public_key,
            plan=args.plan,
            repo=args.repo,
            lockfile=lockfile,
            ledger_path=_repo_relative(args.repo, args.ledger, ".planseal/executions.db"),
            execute=args.execute,
        )
        _emit(result.as_dict())
        return 0 if result.exit_code in {None, 0} else result.exit_code
    raise PlanSealError("command_invalid")


def main() -> None:
    try:
        raise SystemExit(run())
    except PlanSealError as exc:
        print(json.dumps({"error": exc.code}, separators=(",", ":")), file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
