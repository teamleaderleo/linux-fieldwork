# Fork and contribution-path lookup — 2026-08-01

## Result

The canonical contribution destination remains the Muffin Gitea/Forgejo repository `josch/mmdebstrap`, branch `main`. The repository exposes a pull-request workflow, and visible accepted pull requests originate from contributor forks on the same host.

The canonical repository page displayed `You've already forked mmdebstrap` during this lookup. Search could not resolve the authenticated fork namespace or URL. Treat this as evidence of a possible existing fork, not as a verified controlled-fork identity.

## Safe action

1. Do not create a GitHub fork or use a distribution mirror such as `deepin-community/mmdebstrap`.
2. In the logged-in Muffin Gitea account, open the repository/profile fork list and locate the existing fork URL.
3. If an existing fork is found, record its exact URL in the unit `README.md` and use a candidate branch such as `linux-fieldwork/unit-02-caching-proxy-complete-repair`.
4. If no fork exists, create exactly one fork of `josch/mmdebstrap` on the same host after the candidate patch and tests are ready.
5. Do not open a pull request, issue, comment, or review without explicit unit-specific authorization.

## Current packet interpretation

`Controlled fork: NEEDS FORK` remains accurate until the exact existing fork URL is identified. The likely presence of a fork reduces the chance that a new fork is needed, but it does not satisfy the packet identity gate.

## Sources checked

- canonical repository landing page and current `main` head;
- repository pull-request examples showing contributor-fork-to-`josch:main` flow;
- public repository and issue indexes;
- GitHub-connected account repositories, which do not provide the canonical-host fork identity.
