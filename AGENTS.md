# Agent Notes

- Prefer Nix-provided tools over system-wide packages when validating or running project tooling.
- Validate GitHub Actions workflow changes with `nix run nixpkgs#actionlint -- .github/workflows/<workflow>.yml`.
