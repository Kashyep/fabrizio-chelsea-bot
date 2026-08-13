# Security policy

## Secrets

Never commit `.env`, X credentials, copied workflow logs containing credentials, or the SQLite state
database. The supplied ignore rules exclude them. Use GitHub Actions secrets or a host secret manager
in production. Do not put secrets in Actions variables, cache paths, Docker images, or Compose files.

If any credential is exposed:

1. disable the bot (`BOT_ENABLED=false` or stop the container);
2. regenerate the X API key/secret and user access token/secret in the Developer Console;
3. update the deployment secrets;
4. inspect the bot account and X developer usage for unexpected activity;
5. remove the leaked value from Git history if it was committed.

Changing an X App from Read to Read and write requires regenerating the user access token and secret.
Use a dedicated X account for the bot and enable strong account security.

## Reporting a vulnerability

Open a private GitHub security advisory for this repository. Do not include working credentials or
private account data in a public issue.
