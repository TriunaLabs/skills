# GitHub Pages deployment

The intended repository is `TriunaLabs/skills`. Enable Pages with GitHub Actions as the source, then push `main` or run the Pages workflow. It validates packages, runs tests, builds `dist/`, uploads the Pages artifact, and deploys using the `github-pages` environment. Pull requests only run checks and never deploy. No secrets are needed for the static site.

The project URL is `https://triunalabs.github.io/skills/`. All asset, catalog, and skill links are relative, so the artifact also works at a domain root. Confirm the workflow deployment URL and fetch that URL before claiming publication succeeded.

For a future `skills.triunalabs.com`, first verify domain ownership and DNS in GitHub Pages settings, configure the requested DNS record, then add the exact CNAME to `site/CNAME` and verify HTTPS. No CNAME is included now. See [GitHub's custom-domain documentation](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site).
