---
name: github-stacks
description: Create, inspect, or extend native GitHub pull request stacks when PRs depend on one another. Use for converting existing dependent PRs into a stack or managing an explicitly requested stack; ordinary independent PRs do not need this workflow.
---

# Native GitHub stacks

Use GitHub's native stack relationship to represent dependent PRs. Targeting
another PR's branch alone does not register a native stack.

## Establish the chain

Identify the repository, trunk branch, PR numbers, and dependency order from
the user's request and current GitHub state. Inspect each PR's state, head/base
repository and branch, and existing stack membership. Do not infer ancestry
from branch names or treat a cached remote ref as current state.

Order layers from bottom to top: the bottom PR targets trunk; each subsequent
PR targets the preceding PR's head branch. All branches must be in the same
repository. If the requested dependency chain is ambiguous or would require
changing unrelated PRs, resolve that before mutation.

## Choose the tool

Discover relevant GitHub connector capabilities first. Prefer them when they
support the needed stack operation. If they do not, say so briefly and use
authenticated `gh api` or an available official `gh stack` extension. Do not
install an extension just to register existing PRs when the API suffices.

For API details consult the official [Stacks REST API](https://docs.github.com/en/rest/pulls/stacks).
The examples below use API version `2026-03-10`; check current documentation
when the installed server or API rejects a documented operation.

## Register or extend

Use the actual repository and integer PR numbers; these are illustrative.
Query membership before writing:

```bash
gh api -H 'X-GitHub-Api-Version: 2026-03-10' \
  'repos/OWNER/REPO/stacks?pull_request=102'
```

If the PRs already have the intended membership and order, report success
without recreating the stack. Otherwise, create a stack from bottom to top:

```bash
gh api --method POST -H 'X-GitHub-Api-Version: 2026-03-10' \
  repos/OWNER/REPO/stacks \
  -F 'pull_requests[]=101' -F 'pull_requests[]=102'
```

To extend a stack, append only new PRs above its current top:

```bash
gh api --method POST -H 'X-GitHub-Api-Version: 2026-03-10' \
  repos/OWNER/REPO/stacks/STACK_NUMBER/add -F 'pull_requests[]=103'
```

Before creating new dependent PRs, choose their base branches using the same
chain, then register or extend the native stack. Keep PR descriptions focused
on each layer and reference its prerequisite; avoid promising manual retargeting
when native stack handling applies.

## Verify and report

Read the resulting stack, checking its trunk, ordered PR membership, and each
PR's head/base relationship against the requested chain. Report the stack
number and linked PRs in dependency order. Distinguish successful registration
from merge readiness: check CI and review status when asked about readiness.
A registered stack can still need an ancestry update before merging.

If an API mutation times out or returns an uncertain result, re-read membership
before retrying. For a conflict or validation error, inspect current PR/stack
state and address the specific cause; stop if it requires a broader action
than authorized. Do not repeatedly replay a failing mutation.

## Keep actions within scope

A request to create or link a stack authorizes those metadata changes, not
merging, deleting branches, or rewriting published history. Honor any existing
authorization for those actions without asking again. For requested rebases,
reordering, or merges, consult the relevant official workflow and inspect the
affected layers before acting:

- [Manage stacks](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/managing-stacked-pull-requests)
- [Merge stacks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-stacked-pull-requests)

Do not run a cascading rebase merely to register a stack. Preserve local work,
and report blockers without expanding the operation into unrelated cleanup.
